import calendar
import os
import smtplib
from datetime import date, datetime, timedelta
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from environ import environ

from izouapp.generate_charts import generate_barplots, generate_polarArea
from izouapp.models import orders, Pizza
from izouaproject import settings
from izouaproject.settings import BASE_DIR
from django.templatetags.static import static


env = environ.Env()
environ.Env.read_env(env_file=str(BASE_DIR / 'izouapp' / '.env'))

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_img_path = os.path.join(script_dir,'static', 'izouapp', 'images','img_gen_from_charts')


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
        order_count_evolution = ((previous_period_order_count - period_before_order_count) / period_before_order_count) * 100

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
                'last_period_on_site_out_of_total': (previous_period_order_count / get_periodicaly_total_orders()['previous_period_order_count']) * 100 if get_periodicaly_total_orders()['previous_period_order_count'] !=0 else 0,
                'period_before_on_site_out_of_total': (period_before_order_count / get_periodicaly_total_orders()['previous_period_order_count']) * 100 if get_periodicaly_total_orders()['previous_period_order_count'] !=0 else 0,
            }
        else:

            period_orders_info = {
                'last_period_order_count': previous_period_order_count,
                'last_period_turnover': previous_period_turnover,
                'period_before_order_count': period_before_order_count,
                'period_before_turnover': period_before_turnover,
                'order_count_evolution_percentage': order_count_evolution,
                'turnover_evolution_percentage': turnover_evolution,
                'last_period_delivery_out_of_total': (previous_period_order_count / get_periodicaly_total_orders()['previous_period_order_count']) * 100 if get_periodicaly_total_orders()['previous_period_order_count'] !=0 else 0,
                'period_before_delivery_out_of_total': (period_before_order_count / get_periodicaly_total_orders()['previous_period_order_count']) * 100 if get_periodicaly_total_orders()['previous_period_order_count'] !=0 else 0,
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


def set_html_content(period):

    orders_ = get_periodicaly_orders_info(period=period)  # toutes les commandes des deux dernieres périodes

    orders_type = get_periodicaly_orders_by_type(period=period)  # toutes les commandes des deux dernieres periodes mais par type

    pizzas_count_sold = get_most_and_least_sold_pizza_names(period=period)

    last_period_str = {'week':'Semaine passée', 'month':'Mois passé'}.get(period)
    before_period_str = {'week':"Semaine d'avant", 'month':"Mois d'avant"}.get(period)

    img1_path = os.path.join(parent_img_path, generate_barplots('paired_period_orders.png',data={'Catégorie':['Nombre de commandes'],last_period_str: [orders_['last_period_order_count']],before_period_str: [orders_['period_before_order_count']],}, ylab="Commandes", legend="Périodes"))
    img2_path = os.path.join(parent_img_path, generate_barplots('paired_period_turnovers.png',data={'Catégorie':["Chiffres d'affaire"],last_period_str: [orders_['last_period_turnover']],before_period_str: [orders_['period_before_turnover']],}, ylab="Chiffres d'affaire", legend="Périodes"))
    img3_path = os.path.join(parent_img_path, generate_barplots('paired_period_orders_by_type.png', data={'Catégorie': [last_period_str, before_period_str], 'Sur place': [orders_type['on_site_orders_info']['last_period_order_count'], orders_type['on_site_orders_info']['period_before_order_count']], 'Livrées': [orders_type['delivery_orders_info']['last_period_order_count'], orders_type['delivery_orders_info']['period_before_order_count']]}, xlab='Périodes', ylab="Commandes", legend="Types de commandes"))
    img4_path = os.path.join(parent_img_path, generate_barplots('paired_period_turnovers_by_type.png', data={'Catégorie': [last_period_str, before_period_str], 'Sur place': [orders_type['on_site_orders_info']['last_period_turnover'], orders_type['on_site_orders_info']['period_before_turnover']], 'Livrées': [orders_type['delivery_orders_info']['last_period_turnover'], orders_type['delivery_orders_info']['period_before_turnover']], }, ylab="Chiffres d'affaires", xlab='Périodes', legend="Périodes"))

    try:
        img5_path = os.path.join(parent_img_path, generate_polarArea('previous_top_sold_pizzas.png', categories=list(pizzas_count_sold['previous_period'].keys()),  values=list(pizzas_count_sold['previous_period'].values())))
    except Exception as e:
        img5_path = None

    try:
        img6_path = os.path.join(parent_img_path, generate_polarArea('before_top_sold_pizzas.png', categories=list(pizzas_count_sold['before_period'].keys()), values=list(pizzas_count_sold['before_period'].values())))
    except Exception as e:
        img6_path = None

    img1_url = static(img1_path)
    img2_url = static(img2_path)
    img3_url = static(img3_path)
    img4_url = static(img4_path)
    img5_url = None if not img5_path else static(img5_path)
    img6_url = None if not img6_path else static(img6_path)

    img1 = f"""<img src="{img1_url}" height="80%">"""
    img2 = f"""<img src="{img2_url}" height="80%">"""
    img3 = f"""<img src="{img3_url}" height="80%">"""
    img4 = f"""<img src="{img4_url}" height="80%">"""
    img5 = "<h6 class='text-center'>Pas de données disponible</h3>" if not img5_url else f"""<img src="{img5_url}" height="80%">f"""
    img6 = "<h6 class='text-center'>Pas de données disponible</h3>" if not img6_url else f"""<img src="{img6_url}" height="80%">"""



    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons/font/bootstrap-icons.css" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.0/chart.min.js" integrity="sha512-R60W3LgKdvvfwbGbqKusRu/434Snuvr9/Flhtoq9cj1LQ9P4HFKParULqOCAisHk/J4zyaEWWjiWIMuP13vXEg==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
    
        <style>
            
        </style>
    </head>
    <body>
        <h2 class='text-center'>Faisons le point !!! ☺</h2>
        <p class='text-center'>Hello Izoua, voici votre digest hebdomadaire/mensuel:</p>
    
        <h3 class='text-center'>Commandes</h3> <!-- ******************************************************* -->
        <!--affricher deux barplots cote a cote ou chaque bar plot affiche respectivement le nombre de comandes et le chiffre d'affaire des deux periodes-->
        <div class="row justify-content-center">
            <div class="card col-md-6" style="width: 18rem;">
            <!-- dans ce canvas ci sera affiché la distribution du nombre de commandes des deux précédentes periodes -->
                """+f"""{img1 if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Comparaison des commandes pour """+f"""{dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"""+"""</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                <!-- dans ce canvas ci sera affiché la distribution des chiffres d'affaires des deux précédentes periodes -->
                """+f"""{img2 if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Comparaison des chiffres d'affaire pour """+f"""{dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"""+"""</h5>
                </div>
            </div>
        </div>
    
        <h3 class='text-center'>Distribution des Commandes</h3> <!-- ******************************************************* -->
    
        <div class="row justify-content-center">
            <div class="card col-md-6" style="width: 18rem;">
                """+f"""{img3 if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Comparaison des commandes par type pour """+f"""{dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"""+"""</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                """+f"""{img4 if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Comparaison des chiffres d'affaire pour """+f"""{dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"""+"""</h5>
                </div>
            </div>
            
        </div>
        <!--<div class="row justify-content-center">
            <div class="card col-md-6" style="width: 18rem;">
                """+f"""{"<img src='' height = '80%'>" if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Proportion des types commandes pour """+f"""{dict(week="la semaine précédente",month="le mois précédent").get(period)}"""+"""</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                """+f"""{"<img src='' height = '80%'>" if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Proportion des types commandes pour """+f"""{dict(week="la semaine d'avant",month="le mois d'avant").get(period)}"""+"""</h5>
                </div>
            </div>
        </div>-->
    
        <h3 class='text-center'>Pizzas les plus vendues</h3> <!-- ******************************************************* -->
        
        <div class="row justify-content-center">
            <div class="card col-md-6" style="width: 18rem;">
                """+f"""{img5 if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Proportion des pizzas les plus vendues durant """+f"""{dict(week='la semaine dernière', month='le mois dernier').get(period)}"""+"""</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                """+f"""{img6 if orders_ else "<h6 class='text-center'>Pas de données disponible</h3>"}"""+"""
                <div class="card-body">
                    <h5 class="card-title">Proportion des pizzas les plus vendues durant """+f"""{dict(week="la semaine d'avant",month="le mois d'avant").get(period)}"""+"""</h5>
                </div>
            </div>
        </div>
    
    </body>
    </html>
    """

    return html_content

def send_period_digest(period, to_email, subject):

    print("send_period_digest called")

    html_content = set_html_content(period)

    # Ajouter un lien vers le fichier PDF dans l'HTML
    download_link = '<p><a href="cid:pdf_attachment">Télécharger le rapport complet sous format PDF</a></p>'
    html_content += download_link

    # Configuration du serveur SMTP
    smtp_server = env("SMTP_SERVER")
    smtp_port = env("SMTP_PORT")
    sender_email = env("SENDER")
    sender_password = env("PWD")

    # Création du message
    message = MIMEMultipart("mixed")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = to_email

    # Ajout du contenu HTML
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)

    pdf_path = Path(settings.MEDIA_ROOT) / 'reports/file.pdf'

    if not pdf_path.exists():
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

    # Joindre le fichier PDF
    with open(pdf_path, "rb") as pdf_file:
        pdf_attachment = MIMEBase("application", "octet-stream")
        pdf_attachment.set_payload(pdf_file.read())
        encoders.encode_base64(pdf_attachment)
        pdf_attachment.add_header(
            "Content-Disposition",
            f"attachment; filename={pdf_path.split('/')[-1]}"
        )
        pdf_attachment.add_header("Content-ID", "<pdf_attachment>")  # Identifier unique
        message.attach(pdf_attachment)

    # Envoi de l'email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Chiffrement TLS
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_string())