import os
import smtplib
import calendar
from datetime import date, timedelta, datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from environ import environ
from izouapp.datas_to_export import get_periodicaly_orders_info, \
    get_periodicaly_orders_by_type, get_most_and_least_sold_pizza_names, generate_2x_charts, generate_4x_charts
from izouapp.views import create_excel_with_data
from izouaproject.settings import BASE_DIR


env = environ.Env()
environ.Env.read_env(env_file=str(BASE_DIR / 'izouapp' / '.env'))


def get_chart_imgs_datas(period):

    orders_ = get_periodicaly_orders_info(period=period)  # toutes les commandes des deux dernieres périodes

    orders_type = get_periodicaly_orders_by_type(period=period)  # toutes les commandes des deux dernieres periodes mais par type

    pizzas_count_sold = get_most_and_least_sold_pizza_names(period=period)

    last_period_str = {'week':'Semaine passée', 'month':'Mois passé'}.get(period)
    before_period_str = {'week':"Semaine d'avant", 'month':"Mois d'avant"}.get(period)

    title1 = "Commandes pour "+ {'week':'les deux dernières semaines', 'month':'les deux derniers mois'}.get(period)

    title2 = f"Chiffres d'affaire pour "+ {'week':'les deux dernières semaines', 'month':'les deux derniers mois'}.get(period)

    title3 = f"Commandes par type pour "+ {'week':'les deux dernières semaines', 'month':'les deux derniers mois'}.get(period)

    title4 = f"Chiffres d'affaire pour "+ {'week':'les deux dernières semaines', 'month':'les deux derniers mois'}.get(period)

    title5 = f"Pizzas les plus vendues durant "+ {'week':'la semaine dernière', 'month':'le mois dernier'}.get(period)

    title6 = "Pizzas les plus vendues durant "+ {'week':"la semaine d'avant",'month':"le mois d'avant"}.get(period)


    data1 = [{'Catégorie':['Nombre de commandes'],'dataset1':[orders_['last_period_order_count']],'dataset2':[orders_['period_before_order_count']]}, None, 'Commandes', last_period_str, before_period_str, title1]
    data2 = [{'Catégorie':["Chiffres d'affaire"],'dataset1':[orders_['last_period_turnover']],'dataset2':[orders_['period_before_turnover']]}, None, "Chiffres d'affaire", last_period_str, before_period_str, title2]
    data3 = [{'Catégorie':[last_period_str, before_period_str],'dataset1':[orders_type['on_site_orders_info']['last_period_order_count'], orders_type['on_site_orders_info']['period_before_order_count']],'dataset2':[orders_type['delivery_orders_info']['last_period_order_count'], orders_type['delivery_orders_info']['period_before_order_count']]}, "Périodes","Total Commandes", 'Sur place','Livrées',title3]
    data4 = [{'Catégorie':[last_period_str, before_period_str],'dataset1':[orders_type['on_site_orders_info']['last_period_turnover'], orders_type['on_site_orders_info']['period_before_turnover']],'dataset2':[orders_type['delivery_orders_info']['last_period_turnover'], orders_type['delivery_orders_info']['period_before_turnover']]}, None, "Chiffres d'affaires", 'Sur place','Livrées',title4]

    try:
        data5=[pd.DataFrame({"Pizzas":list(pizzas_count_sold['previous_period'].keys()), 'Ventes': list(pizzas_count_sold['previous_period'].values())}),title5]
    except Exception as e:
        data5=None

    try:
        data6 = [pd.DataFrame({"Pizzas": [list(pizzas_count_sold['before_period'].keys())],'Ventes': list(pizzas_count_sold['before_period'].values())}), title6]
    except Exception as e:
        data6=None

    return [data1,data2,data3,data4],[data5,data6]


def get_all_paths(period):

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

    datas = get_chart_imgs_datas(period)
    file1 = generate_2x_charts(datas[1])
    file2 = generate_4x_charts(datas[0])
    file3 = create_excel_with_data('rapport.xlsx', first_period=previous_period_start, second_period=previous_period_end)

    return file1, file2, file3


def send_period_digest(period, to_email, subject):

    period_in_mail = {'week': "hebdomadaire", 'month': "mensuel"}.get(period)

    html_content = f"""
        <h2 style="text-align: center;">Faisons le point !!! 😉</h2>
        <p style="text-align: center;">Hello Izoua, voici votre digest {period_in_mail}:</p>
    """

    # Ajouter un lien vers le fichier PDF dans l'HTML
    #download_link1 = '<p><a href="cid:pdf_attachment_0">Télécharger le rapport complet.</a></p>'
    #download_link2 = '<p><a href="cid:pdf_attachment_1">Télécharger les données graphiques</a></p>'
    #download_link = ''.join([download_link1,download_link2])
    #html_content += download_link

    # Configuration du serveur SMTP
    smtp_server = env("SMTP_SERVER")
    smtp_port = env("SMTP_PORT")
    sender_email = env("SENDER")
    sender_password = env("PASSWORD")

    # Création du message
    message = MIMEMultipart("mixed")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = to_email

    # Ajout du contenu HTML
    html_part = MIMEText(html_content, "html")
    message.attach(html_part)

    files_paths = get_all_paths(period)
    if files_paths[0]==None:
        files_paths = files_paths[1:]


    """if not os.path.exists(pdf_path):
        pdf_path.parent.mkdir(parents=True, exist_ok=True)"""

    # Joindre les fichiers PDF
    for i, pdf_path in enumerate(files_paths):
        with open(pdf_path, "rb") as pdf_file:
            pdf_attachment = MIMEBase("application", "octet-stream")
            pdf_attachment.set_payload(pdf_file.read())
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={pdf_path.split(os.path.sep)[-1]}"
            )
            #pdf_attachment.add_header("Content-ID", f"<pdf_attachment_{i}>")  # Identifier unique
            message.attach(pdf_attachment)

    # Envoi de l'email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Chiffrement TLS
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_string())
