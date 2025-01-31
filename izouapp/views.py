import json
import traceback
from bs4 import BeautifulSoup
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse
from django.utils.timezone import now
from django.shortcuts import render, redirect
from django.conf import settings
from accounts.auth_form import UserLoginForm
from accounts.models import Manager_or_Admin
from .datas_to_export import create_excel_with_data, writing_orderToHtml_in_data_json
from .mail_sender import send_period_digest
from .models import orders, Pizza, Client, DailyInventory, ExtraTopping, PizzaSizePrice, DeliveryPerson, PizzaName, \
    SendMailReminder
from datetime import timedelta, datetime, date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
import os
import locale
from django.db.models import Sum,Q


locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
file_path = os.path.join(parent_dir, 'staticfiles', 'izouapp', 'data.json') # pour lea production

static_path = os.path.join(parent_dir, 'staticfiles')

#file_path = os.path.join(script_dir, 'static', 'izouapp', 'data.json')


# Create your views here.
@login_required
def add_inventory(request):  # fonction qui cree et ajoute un nouvel inventaire dans la bd
    if request.method == "POST":
        try:
            date_ = datetime.strptime(request.POST.get('addDate'), "%Y-%m-%d").date()
            print(f"date is {date_} and his type :{type(date_)}")
            if date_ != date.fromisoformat(request.session.get('date_selected',now().date().isoformat())):
                return render(request, 'izouapp/error_template.html', context={'error':"La date de l'inventaire ne peut pas être différente de la date sélectionnée !"})
            grande = int(request.POST.get('addGrande'))

            if grande<0:
                return render(request, 'izouapp/error_template.html', context={'error':"Le nombre de grandes pizzas ne peut pas être inférieur à zéro !"})
            mini = int(request.POST.get('addMini'))
            if mini<0:
                return render(request, 'izouapp/error_template.html', context={'error':"Le nombre de petites pizzas ne peut pas être inférieur à zéro !"})

            DailyInventory.objects.create(small_pizzas_count=mini, large_pizzas_count=grande, date=date_)


        except ValueError:
            return render(request, 'izouapp/error_template.html', context={'error':"Entrez des données valides s'il vous plaît !!"})

        else:
            request.session['date_selected'] = date_.isoformat()
            request.session['from_add_inventory'] = True
            request.session['date_to_print'] = datetime.strptime(request.POST.get('addDate'), "%Y-%m-%d").date().isoformat()


    return redirect(reverse('home'))


class IzouaLoginView(LoginView):
    form_class = UserLoginForm


class IzouaLogoutView(LogoutView):
    next_page = '/login'

def edit_order_status(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')

        order_status = request.POST.get('order_status')

        order_to_edit = orders.objects.filter(order_id=order_id)

        if len(order_to_edit):
            obj_first = order_to_edit.first()
        else:
            return render(request, 'izouapp/error_template.html', context={'error':"Cette commande a été supprimée depuis l'interface admin"})

        if len(DailyInventory.objects.filter(date=get_date(request))):
            current_inventory = DailyInventory.objects.filter(date=get_date(request)).first()
            soldTotalStart = {'Petite':current_inventory.sold_small_pizzas_count,
                              'Grande':current_inventory.sold_large_pizzas_count}
        else:
            return render(request, 'izouapp/error_template.html', context={'error':"L'inventaire pour le jour choisi n'existe pas ou a été supprimé."})

        soldSizes = obj_first.get_nb_sold_pizzas_by_sizes

        first_status = obj_first.status

        plus_or_minus = 1
        if order_status in ['delivered','pending'] and first_status == 'canceled':
            plus_or_minus = 1

        elif order_status == 'canceled' and first_status in ['delivered','pending']:
            plus_or_minus = -1

        """current_inventory.update(sold_small_pizzas_count=soldTotalStart['Petite'] + plus_or_minus * soldSizes['Petite'], # si la commande passe de annulée à livrée,  alors le nombre de pizzas vendues de l'inventaire actuel est incrémenté du nombre de pizzas vendues dans cette commande
                                 sold_large_pizzas_count=soldTotalStart['Grande'] + plus_or_minus * soldSizes['Grande'])"""

        current_inventory.sold_small_pizzas_count=soldTotalStart['Petite'] + plus_or_minus * soldSizes['Petite']
        current_inventory.sold_large_pizzas_count=soldTotalStart['Grande'] + plus_or_minus * soldSizes['Grande']

        try:
            current_inventory.save()
        except ValueError as e:
            return render(request, 'izouapp/error_template.html',
                          context={'error': str(e)})
        else:
            obj_first.status = order_status

            obj_first.save()

    request.session['from_order_status'] = True

    return redirect(reverse('home'))


@login_required
def to_admin(request):
    return redirect('/admin/')


@login_required
def filter_orders_by_status(request):  # quand l'utilisateur change de filtre

    if request.method == 'POST':
        datas_to_json(request)
        request.session['filter_by_status'] = True
        request.session['selected_option'] = request.POST.get('selected_option')

    return redirect(reverse('home'))

@login_required
def filter_orders_by_date(request):  # quand l'utilisateur change de date à partir du calendrier date_from_form

    if request.method == 'POST':
        request.session['date_selected'] = request.POST.get('datePicker')
        datas_to_json(request)
        request.session['filter_by_date'] = True
        request.session['date_to_print'] = datetime.strptime(request.POST.get('datePicker'),"%Y-%m-%d").date().isoformat()

    return redirect(reverse('home'))


def split_html_and_get_pizzas(request,html, pizzas_count_sold, firstOrderStatus, finalOrderStatus, edit=False):
    # html: un gros bloc de code html contenant toute les pizzas,
    # pizzas_count_sold: dictionnaire contenant le nombre de petites/grandes pizzas vendues

    order_liste = html.split(
        '///')  # liste de code html où chaque code est un ensemble d'inputs contenant les infos sur une pizzas achetée: nom, taille, suppléments, prix

    pizza_liste = []

    for code_html in order_liste:  # code_html: code html d'une pizza
        soup = BeautifulSoup(code_html, 'html.parser')
        inputs = soup.find_all("input")  # liste d'inputs nom, taille, suppléments, prix pour une pizza choisie

        pizza_dict = dict()
        status = ''

        if len(inputs) > 0:
            for input_tag in inputs:  # input_tag ici represente un input qui contient soit nom soit taille soit suppléments soit prix
                if input_tag.get("id") == 'name':  # si input_tag est un input contenant la valeur nom
                    if " - " in input_tag.get("value"):
                        pizza_dict['name'] = input_tag.get("value").split(" - ")  # name = ['moitie 1', 'moitie 2']
                        status = 'speciale'
                    else:
                        pizza_dict['name'] = input_tag.get("value")
                        status = 'normale'
                if input_tag.get("id") == 'size':  # si input_tag est un input contenant la valeur taille
                    pizza_dict['size'] = input_tag.get("value")
                    if not edit:  # si on n'est pas en mode edition, on est donc en train d'ajouter une nouvelle pizza, donc le solde de pizza vendue de cette taille doit etre incrémenté
                        pizzas_count_sold[input_tag.get("value")] += 1

                if input_tag.get("id") == 'extratoppings':  # si input_tag est un input contenant la valeur suppléments
                    if len(input_tag.get("value").split(', ')) > 1:
                        pizza_dict['extratoppings'] = input_tag.get("value").split(', ')
                    else:
                        pizza_dict['extratoppings'] = []
                if input_tag.get("id") == 'price':  # si input_tag est un input contenant la valeur prix
                    pizza_dict['price'] = int(input_tag.get("value"))

            if status == 'speciale':
                extratoppings = tuple(ExtraTopping.objects.filter(name=i)[0] for i in pizza_dict['extratoppings'])
                pizza = Pizza.objects.create(
                    moitie_1=pizza_dict['name'][0],
                    moitie_2=pizza_dict['name'][1],
                    status='Spéciale',
                    name='Pizza Spéciale',
                    size=pizza_dict['size'])
                if len(extratoppings) > 0:
                    pizza.extratoppings.add(*extratoppings)
                pizza_liste.append(pizza)
            else:
                if len(pizza_dict['extratoppings']) > 0:
                    extratoppings = tuple(ExtraTopping.objects.filter(name=i)[0] for i in pizza_dict['extratoppings'])
                pizza = Pizza.objects.create(
                    moitie_1='Néant',
                    moitie_2='Néant',
                    status='Normale',
                    name=pizza_dict['name'],
                    size=pizza_dict['size'])
                if len(pizza_dict['extratoppings']) > 0:
                    pizza.extratoppings.add(*extratoppings)
                pizza_liste.append(pizza)

    if len(pizza_liste) == 0:
        return render(request, 'izouapp/error_template.html', context={'error':"Vous n'avez choisie aucune pizza"})
    if not edit:  # si on n'est pas en mode edition
        return pizza_liste, pizzas_count_sold

    return pizza_liste


def get_pizzas_names_from_html_input(html):
    order_liste = html.split('///')
    pizza_liste_names = []

    for code_html in order_liste:
        soup = BeautifulSoup(code_html, 'html.parser')
        inputs = soup.find_all("input")

        if len(inputs) > 0:
            for input_tag in inputs:
                if input_tag.get("id") == 'name':
                    pizza_liste_names.append(input_tag.get('value'))

    return ", ".join(pizza_liste_names)


@login_required
def edit_order_if_granted(request):#******************************************************************* doit rediriger vers la vue home
    if request.method == 'POST':
        order_to_edit = int(request.POST.get('grantedEdit'))

        with open(file_path, 'r') as file:
            content = json.load(file)
            for dict_ in content['pending_to_edit']:
                if dict_['order_id'] == order_to_edit:
                    data = dict_['data']
                    break
            edit_order_directly(request,
                                client_to_edit=data[1],  # int
                                order_to_edit=data[0],  # int
                                id_deliveryman=data[2],  # int
                                deliveryman_name=data[3],  # str
                                order_type=data[4],  # str
                                html_list_order=data[7],  # str
                                client_name=data[5],  # str
                                client_number=data[8],  # str
                                client_adress=data[9],  # str
                                delivery_time=data[10],  # str
                                payment_method_order_from_order_to_deliver=data[11],
                                payment_method_delivery_from_order_to_deliver=data[12],# str
                                order_status=data[6],  # str
                                price_delivery=data[13],
                                pizzas_count_av=data[14]  # int
                                )

        request.session['from_edit_order_if_granted']=True

    return redirect(reverse('home'))


def edit_order_directly(request, client_to_edit, order_to_edit, id_deliveryman, deliveryman_name, order_type,
                        html_list_order, client_name, client_number, client_adress, delivery_time,
                        payment_method_order_from_order_to_deliver,payment_method_delivery_from_order_to_deliver, order_status, price_delivery, pizzas_count_av):
    client = Client.objects.filter(id_client=client_to_edit)
    order = orders.objects.filter(order_id=order_to_edit)

    if order.first():
        obj_first = order.first()
    else:
        return render(request, 'izouapp/error_template.html', context={'error':"Cette commande n'existe pas ou a été supprimée."})

    initial_status = obj_first.status

    if len(DailyInventory.objects.filter(date=get_date(request))):
        current_inventory = DailyInventory.objects.filter(date=get_date(request)).first()
    else:
        return render(request, 'izouapp/error_template.html', context={'error':"L'inventaire pour le jour choisi n'existe pas ou a été supprimé"})

    user = request.user

    if user.is_admin:

        for pizza in obj_first.pizzas.all():
            pizza.delete()  # supprime toutes les pizzas liées à cette commande

        if order_type == 'to-deliver':

            if DeliveryPerson.objects.filter(id_deliveryman=id_deliveryman).first() and DeliveryPerson.objects.filter(
                    name=deliveryman_name).first():

                if DeliveryPerson.objects.filter(
                        id_deliveryman=id_deliveryman).first() != DeliveryPerson.objects.filter(
                        name=deliveryman_name).first():  # si l'id du livreur et le nom du livreur livreur ne correspondent pas#

                    deliv_man = DeliveryPerson.objects.filter(name=deliveryman_name).first()

                else:
                    deliv_man = DeliveryPerson.objects.filter(id_deliveryman=id_deliveryman).first()

            else:
                return render(request, 'izouapp/error_template.html', context={'error':'Un des livreurs a été supprimé de la base de données.'})

            pizzas:list[Pizza] = split_html_and_get_pizzas(request,html_list_order, pizzas_count_sold=None, edit=True,
                                               finalOrderStatus=order_status, firstOrderStatus=initial_status)

            current_inventory.sold_small_pizzas_count = current_inventory.small_pizzas_count - pizzas_count_av['Petite']
            current_inventory.sold_large_pizzas_count = current_inventory.large_pizzas_count - pizzas_count_av['Grande']

            try:
                current_inventory.save()
            except ValueError as e:
                for pizza in pizzas:
                    pizza.delete()
                return render(request, 'izouapp/error_template.html', context={'error': str(e)})
            else:
                client.update(name=client_name, phone_number=client_number, adress=client_adress)

                obj_first.status = order_status
                obj_first.deliveryHour = delivery_time
                obj_first.deliveryAdress = client_adress
                obj_first.payment_method_order = payment_method_order_from_order_to_deliver
                obj_first.payment_method_delivery = payment_method_delivery_from_order_to_deliver
                obj_first.update_at = now()
                obj_first.surplace = False
                obj_first.deliveryPerson = deliv_man
                obj_first.client = client.first()
                obj_first.deliveryPrice = price_delivery
                obj_first.pizzas.add(*tuple(pizzas))
                obj_first.html_code = html_list_order
                obj_first.save()
                order.update(edit_requested=False)

        else:

            pizzas:list[Pizza] = split_html_and_get_pizzas(request,html_list_order, pizzas_count_sold=None, edit=True,
                                               finalOrderStatus=order_status, firstOrderStatus=initial_status)

            current_inventory.sold_small_pizzas_count = current_inventory.small_pizzas_count - pizzas_count_av['Petite']
            current_inventory.sold_large_pizzas_count = current_inventory.large_pizzas_count - pizzas_count_av['Grande']

            try:
                current_inventory.save()
            except ValueError as e:
                for pizza in pizzas:
                    pizza.delete()
                return render(request, 'izouapp/error_template.html', context={'error': str(e)})
            else:
                client.update(name=client_name)
                obj_first.update_at = now()
                obj_first.surplace = True
                obj_first.status = order_status if order_status else 'on-site'
                obj_first.client = client.first()
                obj_first.pizzas.add(*tuple(pizzas))
                obj_first.html_code = html_list_order
                obj_first.save()
                order.update(edit_requested=False)

   #writing_orderToHtml_in_data_json(all_orders=list(order), file_path=file_path)



@login_required
def edit_order(request):  # modifie simplement le dictionnaire data.json et la clé pending_to_edit
    if request.method == 'POST':

        order_to_edit = int(request.POST.get('order-id'))
        client_to_edit = int(request.POST.get('client-id'))

        order_type = request.POST.get('order-type')

        client_name = request.POST.get('client_name')

        order_status = request.POST.get('editOrderStatus')

        if order_type == 'to-deliver':

            html_list_order = request.POST.get('edit-hidden-textarea-from-order-on-delivery1')
            client_number = request.POST.get('client_number')
            client_adress = request.POST.get('client_adress')
            id_deliveryman = int(request.POST.get('deliver-id'))

            deliveryman_name = request.POST.get('delivery_man')
            delivery_time = request.POST.get('delivery_time')

            pizzas_count_av = {'Petite': int(request.POST.get('edit-SmallPizzasAvailableOnDelivery')),
                               # les pizzas encore disponibles
                               'Grande': int(request.POST.get(
                                   'edit-LargePizzasAvailableOnDelivery'))}  # les pizzas encore disponibles

            if DeliveryPerson.objects.filter(id_deliveryman=id_deliveryman).first() and DeliveryPerson.objects.filter(
                    name=deliveryman_name).first():

                if DeliveryPerson.objects.filter(
                        id_deliveryman=id_deliveryman).first() != DeliveryPerson.objects.filter(
                    name=deliveryman_name).first():  # si l'id du livreur et le nom du livreur livreur ne correspondent pas#

                    deliv_man = DeliveryPerson.objects.filter(name=deliveryman_name).first()

                else:
                    deliv_man = DeliveryPerson.objects.filter(id_deliveryman=id_deliveryman).first()

            else:
                return render(request, 'izouapp/error_template.html', context={'error':'Un des livreurs a été supprimé de la base de données'})

            payment_method_order_from_order_to_deliver = request.POST.get('payment_method_order_from_order_to_deliver')
            payment_method_delivery_from_order_to_deliver = request.POST.get('payment_method_delivery_from_order_to_deliver')
            price_delivery = int(request.POST.get('price_delivery'))
        else:
            html_list_order = request.POST.get('edit-hidden-textarea-from-order-on-site1')

            pizzas_count_av = {'Petite': int(request.POST.get('edit-SmallPizzasAvailableOnSite')),
                               # les pizzas encore disponibles
                               'Grande': int(request.POST.get(
                                   'edit-LargePizzasAvailableOnSite'))}  # les pizzas encore disponibles

            deliveryman_name = 'Commandé sur place'
            client_number = ''
            client_adress = ''
            delivery_time = ''
            payment_method_order_from_order_to_deliver = ''
            payment_method_delivery_from_order_to_deliver = ''
            id_deliveryman = None
            price_delivery = ''

        client = Client.objects.filter(id_client=client_to_edit)
        order = orders.objects.filter(order_id=order_to_edit)

        if order.first():
            obj_first = order.first()
        else:
            return render(request, 'izouapp/error_template.html', context={'error':"Cette commande n'existe pas ou a été supprimée"})

        initial_status = obj_first.status

        if len(DailyInventory.objects.filter(date=get_date(request))):
            current_inventory = DailyInventory.objects.filter(date=get_date(request)).first()
        else:
            return render(request, 'izouapp/error_template.html', context={'error':"L'inventaire pour le jour choisi n'existe pas ou a été supprimé"})

        user = request.user

        if user.is_admin:

            obj_first.pizzas.all().delete()  # supprime toutes les pizzas liées à cette commande

            if order_type == 'to-deliver':

                pizzas = split_html_and_get_pizzas(request,html_list_order, pizzas_count_sold=None, edit=True,
                                                   firstOrderStatus=initial_status, finalOrderStatus=order_status)

                current_inventory.sold_small_pizzas_count = current_inventory.small_pizzas_count - pizzas_count_av['Petite']
                current_inventory.sold_large_pizzas_count = current_inventory.large_pizzas_count - pizzas_count_av['Grande']

                try:
                    current_inventory.save()
                except ValueError as e:
                    for pizza in pizzas:
                        pizza.delete()
                    return render(request, 'izouapp/error_template.html', context={'error': str(e)})
                else:
                    client.update(name=client_name, phone_number=client_number, adress=client_adress)
                    obj_first.status = order_status
                    obj_first.deliveryHour = delivery_time
                    obj_first.deliveryAdress = client_adress
                    obj_first.payment_method_order = payment_method_order_from_order_to_deliver  # ***************
                    obj_first.payment_method_delivery = payment_method_delivery_from_order_to_deliver  # ***************
                    obj_first.update_at = now()
                    obj_first.surplace = False
                    obj_first.deliveryPerson = deliv_man
                    obj_first.client = client.first()
                    obj_first.deliveryPrice = price_delivery
                    obj_first.html_code = html_list_order
                    obj_first.pizzas.add(*tuple(pizzas))
                    obj_first.save()
                    order.update(edit_requested=False)

            else:
                pizzas = split_html_and_get_pizzas(request,html_list_order, pizzas_count_sold=None, edit=True,
                                                   firstOrderStatus=initial_status, finalOrderStatus=order_status)

                current_inventory.sold_small_pizzas_count = current_inventory.small_pizzas_count - pizzas_count_av['Petite']
                current_inventory.sold_large_pizzas_count = current_inventory.large_pizzas_count - pizzas_count_av['Grande']

                try:
                    current_inventory.save()
                except ValueError as e:
                    for pizza in pizzas:
                        pizza.delete()
                    return render(request, 'izouapp/error_template.html', context={'error': str(e)})
                else:
                    client.update(name=client_name)
                    obj_first.update_at = now()
                    obj_first.surplace = True
                    obj_first.client = client.first()
                    obj_first.html_code = html_list_order
                    obj_first.pizzas.add(*tuple(pizzas))
                    obj_first.save()
                    order.update(edit_requested=False)

        else:

            pizza_names = get_pizzas_names_from_html_input(html_list_order)

            if order_type == 'to-deliver':
                pizzas_count_av = {'Petite': int(request.POST.get('edit-SmallPizzasAvailableOnDelivery')),
                                   'Grande': int(request.POST.get('edit-LargePizzasAvailableOnDelivery'))}

            else:
                pizzas_count_av = {'Petite': int(request.POST.get('edit-SmallPizzasAvailableOnSite')),
                                   'Grande': int(request.POST.get('edit-LargePizzasAvailableOnSite'))}

            with open(file_path, 'r') as file:
                content = json.load(file)
                len_row = len(content['pending_to_edit'])
                content['pending_to_edit'].append(
                    {'order_id': order_to_edit, 'idRow': f'pending-{len_row}', 'trFirst': f"""
                                                   <td class="text-center">{len_row + 1}</td>
                                                   <td class="text-center">{client[0].__str__()}</td>
                                                   <td class="text-center">{pizza_names}</td>
                                                   <td class="text-center">{'<span class="badge bg-success">Livrée</span>' if order_status == 'delivered' else '<span class="badge bg-danger">Annulée</span>' if order_status == 'canceled' else '<span class="badge bg-secondary">Sur place</span>'}</td>
                                                   <td class="text-center">{obj_first.total_price}</td>
                                                   <td class="text-center">{obj_first.create_at}</td>
                                                   <td class="text-center">{obj_first.deliveryPerson.name if obj_first.deliveryPerson else 'Commandé sur place'}</td>"""
                        , 'formInnerHTML': f"""
                                                   <input type="hidden" name="grantedEdit" value="{order_to_edit}" class="form-control">
                                                   <input type='submit' value='Valider' class='confirmPending form-control' disabled style="background-color: green; padding: 10px; border-radius: 5px; display: inline-block;">""",
                     'data': [order_to_edit,  # int
                              client_to_edit,  # int
                              id_deliveryman,  # int
                              deliveryman_name,  # str
                              order_type,  # str
                              client_name,  # str
                              order_status,  # str
                              html_list_order,  # str
                              client_number,  # str
                              client_adress,  # str
                              delivery_time,  # str
                              payment_method_order_from_order_to_deliver,  # str
                              payment_method_delivery_from_order_to_deliver,
                              price_delivery,
                              pizzas_count_av  # dict
                              ]})  # int

            with open(file_path, 'w') as file:
                json.dump(content, file)

            order.update(edit_requested=True)

        writing_orderToHtml_in_data_json(all_orders=list(order), file_path=file_path) # recupération de toutes les commandes choisies et stockage dans data.json

    return redirect(reverse('home'))


def send_email(request):

    today = datetime.now()
    reminder = SendMailReminder.objects.all()

    if len(reminder)==0:
        reminder_first = SendMailReminder.objects.create(weekly_digest_sent=False,monthly_digest_sent=False)
    else:
        reminder_first = reminder.first()


    if today.weekday() == 0 and not reminder_first.weekly_digest_sent:  # un Lundi
        superusers = Manager_or_Admin.objects.filter(is_superuser=True)
        user = None
        try:
            for user in superusers:
                if user.email:
                    send_period_digest(period="week", to_email=user.email, subject="Votre digest hebdomadaire.")
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email à {user.email} : {e}")
            traceback.print_exc()
        finally:
            reminder_first.weekly_digest_sent = True
            reminder_first.save()

    elif today.day == 1 and not reminder_first.monthly_digest_sent:  # Premier jour du mois
        print("Envoie d'un mail pour la periode: month")
        superusers = Manager_or_Admin.objects.filter(is_superuser=True)
        user = None
        try:
            for user in superusers:
                if user.email:
                    send_period_digest(period="month", to_email=user.email, subject="Votre digest mensuel.")
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email à {user.email} : {e}")
            traceback.print_exc()
        finally:
            reminder_first.monthly_digest_sent = True
            reminder_first.save()

    else:
        reminder_first.weekly_digest_sent = False
        reminder_first.monthly_digest_sent = False
        reminder_first.save()

    return render(request, 'izouapp/error_template.html', context={'error':'Email envoye avec succes'})


@login_required
def home(request):  # quand l'utilisateur atterit sur la page pour la premiere fois

    if not request.session.get('time_start',None):
        request.session['time_start']=datetime.now().isoformat()

    send_email(request)
    get_datas_to_chart_directly(request)
    if request.session.get('from_add_inventory',None):
        request.session['from_add_inventory'] = False
        return fetching_datas(request, filter_=date.fromisoformat(request.session.get('date_selected', None)),
                              date_to_print=request.session.get('date_to_print', now().date().isoformat()))

    elif request.session.get('filter_by_status',None):
        # Nom du fichier
        nom_fichier = "log.txt"

        # Contenu à écrire dans le fichier
        contenu = f"""le type de commande sélectionné est: {request.session['selected_option']}"""

        # Ouverture du fichier en mode écriture
        with open(os.path.join(static_path,'izouapp','txts',nom_fichier), "w", encoding="utf-8") as fichier:
            fichier.write(contenu)

        request.session['filter_by_status'] = False
        return fetching_datas(request, filter_=request.session['selected_option'],
                              date_to_print=request.session.get('date_selected', now().date().isoformat()))

    elif request.session.get('filter_by_date',None):
        request.session['filter_by_date'] = False
        return fetching_datas(request, filter_=date.fromisoformat(request.session.get('date_selected')),
                              date_to_print=datetime.strptime(request.session.get('date_to_print', now().date().isoformat()),
                                                              "%Y-%m-%d").date().isoformat())

    elif request.session.get('from_order_status', None):
        request.session['from_order_status'] = False
        return fetching_datas(request, filter_=request.session.get('date_selected', now().date()),
                              date_to_print=datetime.strptime(request.session.get('date_selected', now().date().isoformat()),
                                                              "%Y-%m-%d").date().isoformat())

    elif request.session.get('from_edit_order_if_granted', None):
        request.session['from_edit_order_if_granted']= False
        return fetching_datas(request, filter_=request.session.get('date_selected',now().date()),
                              date_to_print=request.session.get('date_selected',now().date().isoformat()))

    else:
        time_start =  datetime.fromisoformat(request.session.get('time_start'))
        time_end = datetime.now()

        difference = time_end-time_start
        if difference.total_seconds()>=300: # si l'utilisateur est connecté depuis plus de 5 minutes
            request.session['date_selected'] = now().date().isoformat()

        return fetching_datas(request, filter_=date.fromisoformat(request.session.get('date_selected', None)), date_to_print=request.session.get('date_selected', now().date().isoformat()))


def fetching_datas(request, filter_, date_to_print):
    time_now = datetime.now().strftime("%H:%M:%S")

    context = dict()
    request.session['date_selected'] = date_to_print  # un objet de type str et non date

    fetched_datas_clients = []
    fetched_datas_inventory = []

    list_order = []
    list_inventory = []
    list_client = []
    list_pending_orders = []

    if isinstance(filter_, date):  # dans le cas où le filtre est un objet de type date
        fetched_datas_orders = orders.objects.filter(
            create_at=filter_)

    elif isinstance(filter_,str):  # dans le cas où le filtre est un objet de type str: all, canceled, on-site, pending, delivered
        context['preselected_filter'] = {'all': 'Tout', 'canceled': 'Annulés', 'delivered': 'Livrés',
                                         'on-site': 'Sur place', 'pending': 'En attente'}.get(
            filter_)  # retourne le contenu html du filtre selectionné

        if filter_ in ['canceled', 'delivered', 'on-site', 'pending']:
            fetched_datas_orders = orders.objects.filter(create_at=date.fromisoformat(request.session['date_selected']),
                                                         status=filter_)

        else:
            fetched_datas_orders = orders.objects.filter(create_at=date.fromisoformat(request.session['date_selected']))

    else:
        context['preselected_filter'] = None
        fetched_datas_orders = orders.objects.filter(create_at=date.fromisoformat(
            request.session['date_selected']))  # récupère toutes les commandes créées à la date fournie en paramètre

    writing_orderToHtml_in_data_json(all_orders=list(fetched_datas_orders), file_path=file_path) # recupération de toutes les commandes choisies et stockage dans data.json

    for i in range(7):
        daily_inventory = DailyInventory.objects.filter(
            date=date.fromisoformat(request.session['date_selected']) - timedelta(i))
        if daily_inventory:
            fetched_datas_inventory.append(
                daily_inventory[0])  # récupère l'historique de l'inventaire des 7 derniers jours

    if fetched_datas_orders:  # si la liste des commandes du jour choisi n'est pas vide
        with open(file_path, 'r') as file:
            content = json.load(file)
            html_list_order = []
            for data in fetched_datas_orders:  # pour chaque commande de ce jour
                client = Client.objects.filter(
                    id_client=data.client.id_client).first()  # le client auquel cette commande est associée
                if not data.edit_requested:  # si la commande n'est pas en cours de modification
                    if client:  # si le client existe
                        fetched_datas_clients.append(client)  # liste des clients ayant commandé ce jour
                        pizza_names = ", ".join(
                            [" - ".join([pizza.moitie_1, pizza.moitie_2]) if pizza.status == 'Spéciale' else pizza.name
                             for pizza in data.pizzas.all()])

                        order = {'a': data.order_id, 'b': client.name, 'c': pizza_names, 'd': data.status,
                                 'e': data.total_price,
                                 'f': data.deliveryHour,
                                 'g': data.deliveryPerson if data.surplace == False else 'Commandé sur place',
                                 'h': data.surplace, 'i': data.client.id_client,
                                 'j': data.deliveryPerson.id_deliveryman if data.surplace == False else None,
                                 'k': sum([1 for i in data.pizzas.all() if i.size == 'Petite']),
                                 'l': sum([1 for i in data.pizzas.all() if i.size == 'Grande']), 'm': client.adress,
                                 'n': client.phone_number, 'o':data.onSiteHour}  # dictionnaire des commandes

                    else:  # si le client n'existe pas
                        # fetched_datas_clients.append(client)
                        pizza_names = ", ".join(
                            [" - ".join([pizza.moitie_1, pizza.moitie_2]) if pizza.status == 'Spéciale' else pizza.name
                             for pizza in data.pizzas.all()])

                        order = {'a': data.order_id, 'b': '', 'c': pizza_names, 'd': data.status,
                                 'e': data.total_price,
                                 'f': data.create_at,
                                 'g': data.deliveryPerson if data.surplace == False else 'Commandé sur place',
                                 'h': data.surplace, 'i': -1,
                                 'j': data.deliveryPerson.id_deliveryman if data.surplace == False else None}
                    list_order.append(order)

                for pizza in data.pizzas.all():  # pour chaque pizza commandé dans la commande actuelle
                    if pizza.status == 'Spéciale':

                        # code html qui sera affiché pour la pizza actuelle
                        html_pizza = f"""<div class="row my-1"><input type="text" class='col-md-2 mx-1' id="name" value="{pizza.moitie_1 + ' - ' + pizza.moitie_2}" disabled><input type="text" class='col-md-2 mx-1' id="size" value="{pizza.size}" disabled><input type="text" class='col-md-2 mx-1' id="extratoppings" value="{", ".join(
                            [extratopping.name for extratopping in pizza.extratoppings.all()]) if len(pizza.extratoppings.all()) > 0 else ''}" disabled><input type="text" class='col-md-2 mx-1' id="price" value="{pizza.price}" disabled><button class="btn btn-danger col-md-4" style="width: 20%; margin: 8px" onclick="deleteItemFromInvoice(taille='{pizza.size}',event, """ + f"""'{'edit-summary-box-from-order-on-site' if data.surplace else 'edit-summary-box-from-order-on-delivery'}')" type="button">Supprimer</button></div>"""

                        html_list_order.append(
                            html_pizza)  # liste de code html des pizzas, donc constituant le code html de la commande

                    else:

                        html_pizza = f"""<div class="row my-1"><input type="text" class='col-md-2 mx-1' id="name" value="{pizza.name}" disabled><input type="text" class='col-md-2 mx-1' id="size" value="{pizza.size}" disabled><input type="text" class='col-md-2 mx-1' id="extratoppings" value="{", ".join(
                            [extratopping.name for extratopping in pizza.extratoppings.all()]) if len(pizza.extratoppings.all()) > 0 else ''}" disabled><input type="text" class='col-md-2 mx-1' id="price" value="{pizza.price}" disabled><button class="btn btn-danger col-md-4" style="width: 20%; margin: 8px" onclick="deleteItemFromInvoice(taille='{pizza.size}',event, """ + f"""'{'edit-summary-box-from-order-on-site' if data.surplace else 'edit-summary-box-from-order-on-delivery'}')" type="button">Supprimer</button></div>"""

                        html_list_order.append(html_pizza)
                    # à la fin html_list_order contient une liste de code html pour les pizzas speciales et normales mais pour la commande en cours

                if 'orderToHtml' in content.keys():
                    for dict_ in content['orderToHtml']:  # à la recherche du dictionnaire correcpondant à la commande actuelle dans le fichier data.json
                        if dict_['order_id'] == data.order_id:  # si trouvé
                            if not data.surplace:
                                content['orderToHtml'][content['orderToHtml'].index(dict_)] = {
                                    'order_id': data.order_id,
                                    'client_infos': {'name': client.name, 'number': client.phone_number,
                                                     'deliveryAdress': data.deliveryAdress,
                                                     'paymentModeOrder': data.payment_method_order, # paymentMode
                                                     'paymentModeDelivery': data.payment_method_delivery,
                                                     'delivPrice': data.deliveryPrice,
                                                     'deliveryMan': data.deliveryPerson.name,
                                                     'deliveryHour': data.deliveryHour.strftime("%H:%M")},
                                    'orderHTML': "".join(html_list_order)}
                            else:
                                content['orderToHtml'][content['orderToHtml'].index(dict_)] = {
                                    'order_id': data.order_id, 'client_infos': {'name': client.name},
                                    'orderHTML': "".join(html_list_order)}
                            break

                html_list_order = []

            with open(file_path, 'w') as file:
                json.dump(content, file)

        for client in set(fetched_datas_clients):
            list_client.append({0: client.id_client, 1: client.name, 2: client.phone_number, 3: client.adress})

        context['orders'] = list_order
        context['clients'] = list_client
        context['len_orders'] = len(context['orders'])
        context['len_orders_delivered'] = len([i for i in context['orders'] if i['d'] == 'delivered'])
        context['len_orders_canceled'] = len([i for i in context['orders'] if i['d'] == 'canceled'])

    else:
        context['orders'] = []
        context['clients'] = []
        context['len_orders'] = 0
        context['len_orders_delivered'] = 0
        context['len_orders_canceled'] = 0

    for data in orders.objects.filter(create_at=date.fromisoformat(request.session['date_selected'])).order_by('deliveryHour'):
        client = Client.objects.filter(id_client=data.client.id_client).first()
        if data.status == 'pending':
            if client:
                pending_order = {'a': client.name, 'b': client.adress, 'c': client.phone_number,
                                 'd': [{'infos': pizza_.__str__()} for pizza_ in data.pizzas.all()],
                                 'e': data.deliveryHour, 'f': data.deliveryPerson,
                                 'g': data.pizza_and_extratopping_price, 'h': data.deliveryPrice, 'i': data.total_price}
                list_pending_orders.append(pending_order)
            else:
                pending_order = {'a': '', 'b': '', 'c': '',
                                 'd': [{'infos': pizza_.__str__()} for pizza_ in data.pizzas.all()],
                                 'e': data.deliveryHour, 'f': data.deliveryPerson,
                                 'g': data.pizza_and_extratopping_price, 'h': data.deliveryPrice, 'i': data.total_price}
                list_pending_orders.append(pending_order)

    context['pending_orders'] = list_pending_orders

    if fetched_datas_inventory:
        for data in fetched_datas_inventory:
            inventory = {1: data.date, 2: data.large_pizzas_count - data.sold_large_pizzas_count,
                         3: data.small_pizzas_count - data.sold_small_pizzas_count, 4: data.sold, 5: data.remaining}
            list_inventory.append(inventory)
        context['inventories'] = list_inventory
    else:
        context['inventories'] = []

    delivery_men = DeliveryPerson.objects.all()
    context['delivery_men_infos'] = []

    if delivery_men:
        for deliMan in delivery_men:
            orders_ = orders.objects.filter(
                deliveryPerson_id=deliMan.id_deliveryman,
                create_at=request.session['date_selected'],
                status='delivered'
            )
            numb_delivery = len(orders_)
            total_pizzas = sum([order.pizza_and_extratopping_price for order in orders_ if order.payment_method_order == 'delivered_man'])
            total_delivery_price_percent = sum([order.deliveryPrice for order in orders_])*0.2
            total_delivery = orders_.aggregate(
                total_delivery=Sum('deliveryPrice', filter=Q(deliveryPrice__isnull=False) & Q(payment_method_delivery='delivered_man'))
            )['total_delivery'] or 0

            delivDict = {'name': deliMan.name, 'TotalPizzasSold': total_pizzas, 'TotalDeliv': total_delivery,
                         'Percent': 0.2 * total_delivery_price_percent,'numb_delivery':numb_delivery}
            context['delivery_men_infos'].append(delivDict)

    preselected_datetime = datetime.strptime(
        f"{request.session.get('date_selected')} {time_now}", "%Y-%m-%d %H:%M:%S").isoformat()
    context['preselected_datetime'] = preselected_datetime  # la date qui sera affichée dans le calendrier
    context['user'] = request.user

    datas_to_json(request)
    return render(request, 'izouapp/manager_screen.html', context=context)


def get_delivery_men():
    delivery_men = DeliveryPerson.objects.all()
    if len(delivery_men) == 0:
        names = None
    else:
        names = [person.name for person in delivery_men]

    return  names

@login_required
def get_summary_of_one_delivery_man(request):
    context = dict()
    his_orders = []
    total_orders_in_cfa = 0
    total_delivery_in_cfa = 0
    total_20_percent_delivery_in_cfa = 0
    if request.method == 'POST':
        person = request.POST.get('selectDeliveryMan')
        try:
            date = datetime.strptime(request.POST.get('selectDate'),"%Y-%m-%d").date()
        except ValueError:
            return HttpResponseRedirect(request.path)

        if person != 'none':
            deliverPerson = DeliveryPerson.objects.filter(name=person)
            list_orders = orders.objects.filter(deliveryPerson=deliverPerson.first(), create_at=date, status='delivered')
            for order in list_orders:
                pizza_names = ", ".join(
                    [" - ".join([pizza.moitie_1, pizza.moitie_2]) if pizza.status == 'Spéciale' else pizza.name for pizza in order.pizzas.all()])
                his_orders.append({'a':person,'b':pizza_names, 'c':order.client,
                                   'd':order.pizza_and_extratopping_price if order.payment_method_order=='delivered_man' else 'Payé chez Izoua',
                                   'e': order.deliveryPrice if order.payment_method_delivery=='delivered_man' else 'Payé chez Izoua',
                                   'f': order.deliveryHour})
                total_orders_in_cfa += order.pizza_and_extratopping_price if order.payment_method_order=='delivered_man' else 0
                total_delivery_in_cfa += order.deliveryPrice if order.payment_method_delivery=='delivered_man' else 0
                total_20_percent_delivery_in_cfa += order.deliveryPrice
            context['his_orders'] = his_orders
            context['total_orders_in_cfa'] = total_orders_in_cfa
            context['total_delivery_in_cfa'] = total_delivery_in_cfa
            context['total_20_percent_delivery_in_cfa'] = 0.2*total_20_percent_delivery_in_cfa


    context['delivery_men'] = get_delivery_men()

    return render(request, 'izouapp/delivery_men_dashboard.html', context=context)

@login_required
def delivery_men_board(request):
    context = dict()
    context['delivery_men'] = get_delivery_men()

    return render(request, 'izouapp/delivery_men_dashboard.html', context=context)


@login_required
def add_order(request):
    if request.method == 'POST':
        with open(file_path, 'r') as file:
            content = json.load(file)

            current_inventory = DailyInventory.objects.filter(date=get_date(request)).first()  # inventaire de la date actuelle

            pizzas_count_sold = {'Petite': current_inventory.sold_small_pizzas_count,
                                 # le nombre de petites pizzas vendues
                                 'Grande': current_inventory.sold_large_pizzas_count}  # le nombre de grandes pizzas vendues

            if request.POST.get('addOrder') == 'order_to_deliver':  # si la commande est à livrer
                html_list_order = request.POST.get(
                    'hidden-textarea-from-order-on-delivery')  # bloc html de toutes les pizzas + le bouton supprimer à reintroduire dans le html

                infos_client = {'name': request.POST.get('client_name'),
                                'numero': request.POST.get('client_number'),
                                'adresse': request.POST.get('client_adress'),
                                'methode_payement_order': request.POST.get('payment_method_order_from_order_to_deliver'),
                                'methode_payement_delivery': request.POST.get('payment_method_delivery_from_order_to_deliver'),
                                'prix_livraison': request.POST.get('price_delivery'),
                                'livreur': request.POST.get('delivery_man'),
                                'heure_livraison': request.POST.get('delivery_time')}

                order_html = request.POST.get('hidden-textarea-from-order-on-delivery1')  # bloc html de toutes les pizzas

                try:
                    deliv_price = int(infos_client['prix_livraison']) # conversion du prix de livraison en entier
                except ValueError:
                    return render(request, 'izouapp/error_template.html', context={'error': "Le prix de la livraison doit être un entier."})

                pizzas, pizzas_count_sold = split_html_and_get_pizzas(request,html=order_html,
                                                                      pizzas_count_sold=pizzas_count_sold,
                                                                      firstOrderStatus='delivered',
                                                                      finalOrderStatus='delivered')  # noms des pizzas commandées + inventaire des pizzas vendues mis à jour

                current_inventory.sold_small_pizzas_count=pizzas_count_sold['Petite']
                current_inventory.sold_large_pizzas_count=pizzas_count_sold['Grande']

                try:
                    current_inventory.save()
                except ValueError as e:
                    for pizza in pizzas:
                        pizza.delete()
                    return render(request, 'izouapp/error_template.html', context={'error': str(e)})
                else:
                    client = Client.objects.create(  # création d'un nouveau client
                        name=infos_client['name'],
                        phone_number=infos_client['numero'],
                        adress=infos_client['adresse'])

                    order = orders.objects.create(  # création d'une nouvelle commande
                        create_at=date.fromisoformat(request.session['date_selected']),
                        deliveryHour=infos_client['heure_livraison'],
                        deliveryAdress=infos_client['adresse'],
                        payment_method_order=infos_client['methode_payement_order'],
                        payment_method_delivery=infos_client['methode_payement_delivery'],
                        deliveryPerson=DeliveryPerson.objects.filter(name=infos_client['livreur'])[0],
                        client=client,
                        deliveryPrice=deliv_price,
                        html_code=html_list_order
                    )

                    order.pizzas.add(*tuple(pizzas))  # ajout des pizzas dans la commande


                    """content['orderToHtml'].append({'order_id': order.order_id,
                                                   'client_infos': {'name': infos_client['name'],
                                                                    'number': infos_client['numero'],
                                                                    'deliveryAdress': infos_client['adresse'],
                                                                    'paymentModeOrder':infos_client['methode_payement_order'],
                                                                    'paymentModeDelivery': infos_client['methode_payement_delivery'],
                                                                    'delivPrice': infos_client['prix_livraison'],
                                                                    'deliveryMan': infos_client['livreur'],
                                                                    'deliveryHour': infos_client['heure_livraison']},
                                                   'orderHTML': html_list_order})"""

            else:  # si la commande est sur place

                html_list_order = request.POST.get('hidden-textarea-from-order-on-site')

                infos_client = {'name_onsite': request.POST.get('client_name')}
                order_html = request.POST.get('hidden-textarea-from-order-on-site1')

                pizzas, pizzas_count_sold = split_html_and_get_pizzas(request,html=order_html,
                                                                      pizzas_count_sold=pizzas_count_sold,
                                                                      firstOrderStatus='delivered',
                                                                      finalOrderStatus='delivered')

                current_inventory.sold_small_pizzas_count = pizzas_count_sold['Petite']
                current_inventory.sold_large_pizzas_count = pizzas_count_sold['Grande']

                try:
                    current_inventory.save()
                except ValueError as e:
                    for pizza in pizzas:
                        pizza.delete()
                    return render(request, 'izouapp/error_template.html', context={'error': str(e)})
                else:
                    client = Client.objects.create(
                        name=infos_client['name_onsite'])

                    order = orders.objects.create(
                        create_at=date.fromisoformat(request.session['date_selected']),
                        surplace=True,
                        status='on-site',
                        client=client,
                        html_code=html_list_order
                    )

                    order.pizzas.add(*tuple(pizzas))  # ajout des pizzas dans la commande

                    """content['orderToHtml'].append({'order_id': order.order_id, 'client_infos': {'name': client.name}, 'orderHTML': html_list_order})"""

        writing_orderToHtml_in_data_json(all_orders=[order], file_path=file_path) # ecriture de la commande dans le fichier json
        """with open(file_path, 'w') as file:
            json.dump(content, file)"""

    return redirect(reverse('home'))


def get_date(request):  # fonction qui retourne la date si elle est enregistrée dans la session sinon elle retourne la date actuelle
    if request.session.get('date_selected', None):
        return date.fromisoformat(request.session.get('date_selected'))
    request.session['date_selected'] = now().date().isoformat()
    return now().date().isoformat()


def datas_to_json(request):  # à revoir au cas où les requetes renvoient des tableaux vides, exportent les données nécéssaire dans un fichier.json

    pizza_names = PizzaName.objects.all()
    extratoppings = ExtraTopping.objects.all()
    inventory = DailyInventory.objects.filter(date=get_date(request))
    prices = PizzaSizePrice.objects.all()
    deliveryPersons = DeliveryPerson.objects.all()

    extratoppings_ = [{'name': topping.name, 'price': topping.price} for topping in extratoppings]
    deliveryPersons_ = [delivery_man.name for delivery_man in deliveryPersons]

    #date_ = datetime.strptime(request.session.get('date_selected'),'%Y-%m-%d')
    #date_to_check = date_.strftime('%d/%m/%Y')
    date_to_check = request.session.get('date_selected', now().date().isoformat())

    if len(pizza_names) == 0 or len(prices) == 0:
        pizza_ = []

    else:
        pizza_ = [{'name': n_pizza.name} for n_pizza in pizza_names]

    if len(inventory) != 0:
        if len(prices) != 0:
            inventory_ = [{'name': 'Petite',
                           'pizzas_count': inventory[0].small_pizzas_count - inventory[0].sold_small_pizzas_count,
                           'Price': prices[0].Petite},
                          {'name': 'Grande',
                           'pizzas_count': inventory[0].large_pizzas_count - inventory[0].sold_large_pizzas_count,
                           'Price': prices[0].Grande}, date_to_check]
        else:
            inventory_ = [{'name': 'Petite',
                           'pizzas_count': inventory[0].small_pizzas_count - inventory[0].sold_small_pizzas_count,
                           'Price': 0},
                          {'name': 'Grande',
                           'pizzas_count': inventory[0].large_pizzas_count - inventory[0].sold_large_pizzas_count,
                           'Price': 0}, date_to_check]

    elif len(prices) != 0:
        inventory_ = [{'name': 'Petite', 'pizzas_count': 0, 'Price': prices[0].Petite},
                      {'name': 'Grande', 'pizzas_count': 0, 'Price': prices[0].Grande}]

    else:
        inventory_ = [{'name': 'Petite', 'pizzas_count': 0, 'Price': 0},
                      {'name': 'Grande', 'pizzas_count': 0, 'Price': 0}]

    with open(file_path, 'r') as file:
        content = json.load(file)

    if pizza_ == [] or len(inventory) == 0 or len(prices) == 0:
        content = dict()

    else:
        content['pizza'] = pizza_
        content['extratoppings'] = extratoppings_
        content['inventory'] = inventory_
        content['deliveryPersons'] = deliveryPersons_
        content['date_selected'] = request.session.get('date_selected')

        if 'pending_to_edit' in content.keys():
            for dict_ in content['pending_to_edit']:
                order = orders.objects.filter(order_id=dict_['order_id'])
                if not order[0].edit_requested:
                    content['pending_to_edit'].remove(dict_)

        # content.get('ordersToChart', None)
        if not 'ordersToChart' in content.keys():
            content['ordersToChart'] = {}

        if not 'orderToHtml' in content.keys():
            content['orderToHtml'] = []  # une liste de dictionnaire

        if not 'pending_to_edit' in content.keys():
            content['pending_to_edit'] = []  # une liste de dictionnaire

    with open(file_path, 'w') as file:
        json.dump(content, file)


@login_required
def download_excel(request):
    if request.method == 'POST':
        try:
            first_period = request.POST.get('first_period')
            second_period = request.POST.get('second_period')
            create_excel_with_data(first_period=first_period,second_period=second_period,file_name='izoua.xlsx')

            # Chemin absolu du fichier Excel généré
            file_path = os.path.join(settings.MEDIA_ROOT, 'reports', 'izoua.xlsx')

            # Vérifier si le fichier existe
            if not os.path.exists(file_path):
                return render(request, 'izouapp/error_template.html', context={'error':'Fichier non trouvé'})

            # Ouvrir le fichier en mode binaire
            with open(file_path, 'rb') as file:
                response = HttpResponse(file, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="commandes.xlsx"'
                return response
        except Exception as e:
            return render(request, 'izouapp/error_template.html', context={'error':'Veuillez saisir des dates valides'})

    return redirect(reverse('home'))


def get_datas_to_chart_directly(request):
    days_ = int(request.GET.get('delayChart', 30))
    if days_<=0:
        delay = 30
    else:
        delay=days_
    datas = dict()
    days = []
    sold = []
    unsold = []

    start = request.session.get('date_selected', now().date().isoformat())

    for i in range(delay):
        daily_inventory = DailyInventory.objects.filter(date=date.fromisoformat(start) - timedelta(i)).first()
        if daily_inventory:
            date_to_format = date.fromisoformat(start) - timedelta(i)
            date_formatee_fr = date_to_format.strftime("%d/%m/%Y")
            days.append(date_formatee_fr)
            sold.append(daily_inventory.sold)
            unsold.append(daily_inventory.remaining)
        else:
            continue

    datas['days'] = list(reversed(days))
    datas['sold'] = list(reversed(sold))
    datas['unsold'] = list(reversed(unsold))

    with open(file_path, 'r') as file:
        content = json.load(file)

        content['ordersToChart'] = datas

    with open(file_path, 'w') as file:
        json.dump(content, file)

    datas_to_json(request)


@login_required
def get_datas_to_chart(request):
    get_datas_to_chart_directly(request)
    return fetching_datas(request, filter_=None, date_to_print=now().date().isoformat())






# <i class="bi bi-x-lg" onclick='deletePendingEdit(row='pending-{len_row}',order={order_to_edit})' style="background-color: green; padding: 10px; border-radius: 5px; display: inline-block;"></i>