import calendar
import os
from datetime import date, timedelta, datetime
from django.db.models import Sum, Q
from fpdf import FPDF
from izouapp.models import orders, DeliveryPerson, Pizza
from izouaproject import settings
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def prepare_datas_to_export():
    fetched_datas = orders.objects.all()
    datas_cleaned = []
    if len(fetched_datas):
        for data in fetched_datas:
            date_formatee_fr = data.create_at.strftime("%d %B %Y")
            time_formatee = data.deliveryHour.strftime(
                "%Hh%M") if data.deliveryHour else 'Heure sur place: ' + data.onSiteHour.strftime('%H:%M')
            pizza_names = ", ".join([pizza.__str__() for pizza in data.pizzas.all()])
            surplace = 'Oui' if data.surplace else 'Non'
            delivered = {'delivered': 'Livré', 'canceled': 'Annulé', 'on-site': 'Sur place', 'pending': 'En attente'}[
                data.status]
            methode_payment_order = 'Chez Izoua' if data.payment_method_order == 'izoua' else 'Chez le livreur'
            methode_payment_delivery = 'Chez Izoua' if data.payment_method_delivery == 'izoua' else 'Chez le livreur'
            data_row = [date_formatee_fr, surplace,
                        data.deliveryAdress if data.deliveryAdress else 'Commandée sur place', time_formatee,
                        data.deliveryPerson.name if data.deliveryPerson else 'Commandée sur place',
                        delivered, data.client.name, methode_payment_order if data.surplace else 'Chez Izoua', methode_payment_delivery if data.surplace else 'Chez Izoua', pizza_names,
                        data.deliveryPrice if data.surplace else 'Commandée sur place',
                        data.pizza_and_extratopping_price, data.total_price]

            datas_cleaned.append(data_row)

        return datas_cleaned

    return None


def get_periodicaly_total_orders() -> dict:
    today = date.today()

    # Calcul des périodes
    previous_period_start = today - timedelta(days=today.weekday() + 7)
    previous_period_end = previous_period_start + timedelta(days=6)

    period_before_start = previous_period_start - timedelta(days=7)
    period_before_end = period_before_start + timedelta(days=6)

    # Commandes de la periode dernière
    previous_period_orders = orders.objects.filter(
        create_at__gte=previous_period_start, create_at__lte=previous_period_end
    )
    previous_period_order_count = previous_period_orders.count()

    # Commandes de la periode d'avant
    period_before_orders = orders.objects.filter(
        create_at__gte=period_before_start, create_at__lte=period_before_end,
    )
    period_before_order_count = period_before_orders.count()

    return {'previous_period_order_count':previous_period_order_count,'period_before_order_count':period_before_order_count}


def get_periodicaly_orders_info(filter_conditions=None, period="week") -> dict|bool:
    today = date.today()

    print('period choisie: ', period)

    if period == "week":
        # Calcul des périodes
        previous_period_start = today - timedelta(days=today.weekday() + 7)
        previous_period_end = previous_period_start + timedelta(days=6)

        before_period_start = previous_period_start - timedelta(days=7)
        before_period_end = before_period_start + timedelta(days=6)

    else:
        month1 = 12 if today.month - 1 == 0 else today.month - 1 # le mois précedent 1,2,...,12
        month2 = month1 - 1 # le mois d'avant 1,2,...,12
        year = today.year-1 if today.month - 1 == 0 else today.year # l'année actuelle

        # Obtenir le premier jour du mois précédent
        previous_period_start = datetime(year, month1, 1)

        # Obtenir le dernier jour du mois précédent
        previous_period_end = datetime(year, month1,
                                           calendar.monthrange(year, month1)[1])

        # Obtenir le premier jour du mois d'avant
        before_period_start = datetime(year, month2, 1)

        # Obtenir le dernier jour du mois d'avant
        before_period_end = datetime(year, month2,
                                           calendar.monthrange(year, month2)[1])

    # Filtre optionnel
    filter_conditions = filter_conditions or {}

    # Commandes de la periode dernière
    previous_period_orders = orders.objects.filter(create_at__gte=previous_period_start, create_at__lte=previous_period_end, **filter_conditions)

    if len(previous_period_orders)==0:
        if not filter_conditions:
            period_orders_info = {
                'last_period_order_count': 0,
                'last_period_turnover': 0,
                'period_before_order_count': 0,
                'period_before_turnover': 0,
                'order_count_evolution_percentage': 0,
                'turnover_evolution_percentage': 0,
            }

        else:
            if filter_conditions == {'surplace': True}:
                period_orders_info = {
                    'last_period_order_count': 0,
                    'last_period_turnover': 0,
                    'period_before_order_count': 0,
                    'period_before_turnover': 0,
                    'order_count_evolution_percentage': 0,
                    'turnover_evolution_percentage': 0,
                    'last_period_on_site_out_of_total': (0 / get_periodicaly_total_orders()[
                        'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                     'previous_period_order_count'] != 0 else 0,
                    'period_before_on_site_out_of_total': (0 / get_periodicaly_total_orders()[
                        'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                     'previous_period_order_count'] != 0 else 0,
                }
            else:

                period_orders_info = {
                    'last_period_order_count': 0,
                    'last_period_turnover': 0,
                    'period_before_order_count': 0,
                    'period_before_turnover': 0,
                    'order_count_evolution_percentage': 0,
                    'turnover_evolution_percentage': 0,
                    'last_period_delivery_out_of_total': (0 / get_periodicaly_total_orders()[
                        'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                     'previous_period_order_count'] != 0 else 0,
                    'period_before_delivery_out_of_total': (0 / get_periodicaly_total_orders()[
                        'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                     'previous_period_order_count'] != 0 else 0,
                }
        return period_orders_info

    previous_period_order_count = previous_period_orders.count()
    previous_period_turnover = sum(order.total_price for order in previous_period_orders) or 0

    # Commandes de la periode d'avant
    period_before_orders = orders.objects.filter(
        create_at__gte=before_period_start, create_at__lte=before_period_end, **filter_conditions
    )
    period_before_order_count = period_before_orders.count()
    period_before_turnover = sum(order.total_price for order in period_before_orders) or 0

    # Calcul des évolutions en pourcentage
    order_count_evolution = 0
    turnover_evolution = 0

    if period_before_order_count > 0:
        order_count_evolution = ((
                                             previous_period_order_count - period_before_order_count) / period_before_order_count) * 100

    if period_before_turnover > 0:
        turnover_evolution = ((previous_period_turnover - period_before_turnover) / period_before_turnover) * 100

    # Retour des informations
    if not filter_conditions:

        period_orders_info = {
            'last_period_order_count': previous_period_order_count,
            'last_period_turnover': previous_period_turnover,
            'period_before_order_count': period_before_order_count,
            'period_before_turnover': period_before_turnover,
            'order_count_evolution_percentage': order_count_evolution,
            'turnover_evolution_percentage': turnover_evolution,
        }

    else:
        if filter_conditions == {'surplace': True}:
            period_orders_info = {
                'last_period_order_count': previous_period_order_count,
                'last_period_turnover': previous_period_turnover,
                'period_before_order_count': period_before_order_count,
                'period_before_turnover': period_before_turnover,
                'order_count_evolution_percentage': order_count_evolution,
                'turnover_evolution_percentage': turnover_evolution,
                'last_period_on_site_out_of_total': (previous_period_order_count / get_periodicaly_total_orders()[
                    'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                 'previous_period_order_count'] != 0 else 0,
                'period_before_on_site_out_of_total': (period_before_order_count / get_periodicaly_total_orders()[
                    'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                 'previous_period_order_count'] != 0 else 0,
            }
        else:

            period_orders_info = {
                'last_period_order_count': previous_period_order_count,
                'last_period_turnover': previous_period_turnover,
                'period_before_order_count': period_before_order_count,
                'period_before_turnover': period_before_turnover,
                'order_count_evolution_percentage': order_count_evolution,
                'turnover_evolution_percentage': turnover_evolution,
                'last_period_delivery_out_of_total': (previous_period_order_count / get_periodicaly_total_orders()[
                    'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                 'previous_period_order_count'] != 0 else 0,
                'period_before_delivery_out_of_total': (period_before_order_count / get_periodicaly_total_orders()[
                    'previous_period_order_count']) * 100 if get_periodicaly_total_orders()[
                                                                 'previous_period_order_count'] != 0 else 0,
            }

    return period_orders_info


def get_periodicaly_orders_by_type(period):
    # Commandes sur place
    on_site_info = get_periodicaly_orders_info(filter_conditions={'surplace': True}, period=period)

    # Commandes livrées
    delivery_info = get_periodicaly_orders_info(filter_conditions={'surplace': False}, period=period)

    return {
        'on_site_orders_info': on_site_info,
        'delivery_orders_info': delivery_info
    }


def get_periodicaly_delivery_infos():
    # Nombre total de livraisons effectuées
    total_delivery = {'last_period_order_count': get_periodicaly_orders_info(filter_conditions={'surplace': False})[
        'last_period_order_count'],  # la semaine passée
                      'period_before_order_count': get_periodicaly_orders_info(filter_conditions={'surplace': False})[
                          'period_before_order_count']}  # la semaine d'avant

    today = date.today()
    delivery_men_infos = []

    # Calcul des périodes
    previous_week_start = today - timedelta(days=today.weekday() + 7)
    previous_week_end = previous_week_start + timedelta(days=6)

    week_before_start = previous_week_start - timedelta(days=7)
    week_before_end = week_before_start + timedelta(days=6)

    delivery_men = DeliveryPerson.objects.all()

    if delivery_men:
        for deliMan in delivery_men:  # pour chaque livreur enregistré
            # Commandes de la semaine dernière
            previous_week_orders = orders.objects.filter(
                create_at__gte=previous_week_start, create_at__lte=previous_week_end,
                deliveryPerson_id=deliMan.id_deliveryman, status='delivered'
            )

            # Commandes de la semaine d'avant
            week_before_orders = orders.objects.filter(
                create_at__gte=week_before_start, create_at__lte=week_before_end,
                deliveryPerson_id=deliMan.id_deliveryman, status='delivered'
            )
            numb_delivery1 = len(previous_week_orders)
            total_pizzas1 = sum([order.pizza_and_extratopping_price for order in previous_week_orders if
                                 order.payment_method_order == 'delivered_man'])
            total_delivery1 = previous_week_orders.aggregate(
                total_delivery=Sum('deliveryPrice',
                                   filter=Q(deliveryPrice__isnull=False) & Q(payment_method_delivery='delivered_man'))
            )['total_delivery'] or 0

            numb_delivery2 = len(week_before_orders)
            total_pizzas2 = sum([order.pizza_and_extratopping_price for order in week_before_orders if
                                 order.payment_method_order == 'delivered_man'])
            total_delivery2 = week_before_orders.aggregate(total_delivery=Sum('deliveryPrice',
                                                                              filter=Q(deliveryPrice__isnull=False) & Q(
                                                                                  payment_method_delivery='delivered_man'))
                                                           )['total_delivery'] or 0

            delivDict = [deliMan.name, total_pizzas1, total_delivery1, 0.2 * total_delivery1, numb_delivery1,
                         total_pizzas2, total_delivery2, 0.2 * total_delivery2, numb_delivery2]
            delivery_men_infos.append(delivDict)

    return delivery_men_infos


def get_most_and_least_sold_pizza_names(period) -> dict:
    today = date.today()

    if period == "week":
        # Calcul des périodes
        previous_period_start = today - timedelta(days=today.weekday() + 7)
        previous_period_end = previous_period_start + timedelta(days=6)

        before_period_start = previous_period_start - timedelta(days=7)
        before_period_end = before_period_start + timedelta(days=6)

    else:
        month1 = 12 if today.month - 1 == 0 else today.month - 1  # le mois précedent 1,2,...,12
        month2 = month1 - 1  # le mois d'avant 1,2,...,12
        year = today.year - 1 if today.month - 1 == 0 else today.year  # l'année actuelle

        # Obtenir le premier jour du mois précédent
        previous_period_start = datetime(year, month1, 1)

        # Obtenir le dernier jour du mois précédent
        previous_period_end = datetime(year, month1,
                                       calendar.monthrange(year, month1)[1])

        # Obtenir le premier jour du mois d'avant
        before_period_start = datetime(year, month2, 1)

        # Obtenir le dernier jour du mois d'avant
        before_period_end = datetime(year, month2,calendar.monthrange(year, month2)[1])

    # Ventes de pizzas de la periode dernière
    previous_period_pizzas = Pizza.objects.filter(
        create_at__gte=previous_period_start, create_at__lte=previous_period_end
    )

    if len(previous_period_pizzas)==0:
        previous_period_list = None
    else:
        previous_period_sales = {}
        for pizza in previous_period_pizzas:
            pizza_name = pizza.get_name  # Utilisation de la propriété
            previous_period_sales[pizza_name] = previous_period_sales.get(pizza_name, 0) + 1

        previous_period_list = {name: count for name, count in previous_period_sales.items()}

    # Ventes de pizzas de la periode d'avant
    period_before_pizzas = Pizza.objects.filter(
        create_at__gte=before_period_start, create_at__lte=before_period_end
    )

    if len(period_before_pizzas) == 0:
        period_before_list = None
    else:
        period_before_sales = {}
        for pizza in period_before_pizzas:
            pizza_name = pizza.get_name  # Utilisation de la propriété
            period_before_sales[pizza_name] = period_before_sales.get(pizza_name, 0) + 1

        period_before_list = {name: count for name, count in period_before_sales.items()}

    # Retourner les résultats
    return {
        'previous_period': previous_period_list,
        'before_period': period_before_list
    }


def create_pdf_with_data(): # note: je dois ajouter un tableau en dessous qui resumme aussi les infos des livreurs
    second_table_data = get_periodicaly_delivery_infos()
    file_name = 'file.pdf'
    data = prepare_datas_to_export()
    if data:
        # Construire le chemin absolu du fichier PDF dans MEDIA_ROOT
        parent_path = os.path.join(settings.MEDIA_ROOT, 'reports')
        file_path = os.path.join(settings.MEDIA_ROOT, 'reports',file_name)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=10)
        pdf.add_page()
        pdf.set_font("Arial", size=10)

        # Titre du document pour le premier tableau
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(0, 10, "Recapitulatif des commandes", ln=True, align='C')
        pdf.ln(10)  # Ajouter un espacement vertical

        # Entêtes du tableau
        headers = [
            "Date", "Sur place", "Adresse Livraison", "Heure livraison", "Livreur",
            "Statut", "Clients", "Mode de paiement commandes", "Mode de paiement livraison", "Infos Pizzas",
            "Prix Livraison", "Prix Pizzas + Suppléments", "Total"
        ]
        pdf.set_font("Arial", size=10, style='B')
        col_widths = [25, 20, 50, 25, 30, 25, 30, 35, 35, 40, 30, 45, 30]  # Largeurs des colonnes adaptées
        for col_num, header in enumerate(headers):
            pdf.cell(col_widths[col_num], 10, header, border=1, align='C')
        pdf.ln()  # Passer à la ligne suivante

        pdf.set_font("Arial", size=10, style='B')
        col_widths = [25, 20, 50, 25, 30, 25, 30, 35, 35, 40, 30, 45, 30]  # Largeurs des colonnes adaptées
        for col_num, header in enumerate(headers):
            pdf.cell(col_widths[col_num], 10, header, border=1, align='C')
        pdf.ln()  # Passer à la ligne suivante

        # Ajouter une nouvelle page pour le second tableau
        pdf.add_page()

        # Entêtes du second tableau
        second_headers = [
            "Livreurs", "Total vendu sem. passée", "Total livré sem. passée", "Pourcentage sem. passée",
            "Nombre livraisons sem. passée", "Total vendu sem. d'avant", "Total livré sem. d'avant",
            "Pourcentage sem. d'avant", "Nombre livraisons sem. d'avant"
        ]

        # Titre du document pour le second tableau
        pdf.set_font("Arial", size=14, style='B')
        pdf.cell(0, 10, "Statistiques des livreurs", ln=True, align='C')
        pdf.ln(10)  # Ajouter un espacement vertical

        col_widths_second = [30, 40, 40, 40, 45, 40, 40, 40, 45]  # Largeurs des colonnes adaptées
        pdf.set_font("Arial", size=10, style='B')
        for col_num, header in enumerate(second_headers):
            pdf.cell(col_widths_second[col_num], 10, header, border=1, align='C')
        pdf.ln()  # Passer à la ligne suivante

        pdf.set_font("Arial", size=10)
        for row_data in second_table_data:
            for col_num, value in enumerate(row_data):
                pdf.cell(col_widths_second[col_num], 10, str(value), border=1, align='C')
            pdf.ln()  # Passer à la ligne suivante

        # Sauvegarder le fichier PDF
        pdf.output(file_path)

        return  parent_path, file_path


def create_pdf_with_images(image_paths:list, titles:list, output_file:str):
    """
    Crée un fichier PDF contenant 6 images disposées en 3 lignes avec des titres.

    :param image_paths: Liste de 6 chemins vers les images à insérer.
    :param titles: Liste de 3 titres correspondant à chaque ligne d'images.
    :param output_file: Nom du fichier PDF de sortie.
    """
    if len(image_paths) != 6:
        raise ValueError("Vous devez fournir exactement 6 chemins d'images.")
    if len(titles) != 3:
        raise ValueError("Vous devez fournir exactement 3 titres.")

    file_path = os.path.join(settings.MEDIA_ROOT, 'reports', output_file)

    with PdfPages(file_path) as pdf:
        fig, axes = plt.subplots(3, 2, figsize=(8.5, 11))  # Taille standard pour un PDF A4
        fig.subplots_adjust(hspace=0.5)  # Espacement vertical

        for row in range(3):
            # Ajouter un titre au-dessus de chaque ligne
            fig.text(0.5, 0.94 - row * 0.3, titles[row], ha='center', fontsize=14, fontweight='bold')

            for col in range(2):
                idx = row * 2 + col
                ax = axes[row, col]
                ax.axis('off')  # Désactiver les axes

                # Charger et afficher l'image
                img = plt.imread(image_paths[idx])
                ax.imshow(img)

        pdf.savefig(fig)
        plt.close(fig)

    return file_path