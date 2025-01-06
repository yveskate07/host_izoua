import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from environ import environ
from izouapp.datas_to_export import create_pdf_with_data, get_periodicaly_orders_info, \
    get_periodicaly_orders_by_type, get_most_and_least_sold_pizza_names, create_pdf_with_images
from izouapp.generate_charts import generate_barplots, generate_polarArea
from izouaproject.settings import BASE_DIR
from django.templatetags.static import static


env = environ.Env()
environ.Env.read_env(env_file=str(BASE_DIR / 'izouapp' / '.env'))

script_dir = os.path.dirname(os.path.abspath(__file__)) # chemin absolu vers ce script
parent_img_path = os.path.join(script_dir,'static', 'izouapp', 'images','img_gen_from_charts')


def get_chart_imgs_path(period):

    orders_ = get_periodicaly_orders_info(period=period)  # toutes les commandes des deux dernieres périodes

    orders_type = get_periodicaly_orders_by_type(period=period)  # toutes les commandes des deux dernieres periodes mais par type

    pizzas_count_sold = get_most_and_least_sold_pizza_names(period=period)

    last_period_str = {'week':'Semaine passée', 'month':'Mois passé'}.get(period)
    before_period_str = {'week':"Semaine d'avant", 'month':"Mois d'avant"}.get(period)

    title1 = f"Comparaison des commandes pour {dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"

    title2 = f"Comparaison des chiffres d'affaire pour {dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"

    title3 = f"Comparaison des commandes par type pour {dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"

    title4 = f"Comparaison des chiffres d'affaire pour {dict(week='les deux dernières semaines', month='les deux derniers mois').get(period)}"

    title5 = f"Proportion des pizzas les plus vendues durant {dict(week='la semaine dernière', month='le mois dernier').get(period)}"

    title6 = f"""Proportion des pizzas les plus vendues durant {dict(week="la semaine d'avant",month="le mois d'avant").get(period)}"""

    img1_path = os.path.join(parent_img_path, generate_barplots(title=title1, file_name='paired_period_orders.png',data={'Catégorie':['Nombre de commandes'],last_period_str: [orders_['last_period_order_count']],before_period_str: [orders_['period_before_order_count']],}, ylab="Commandes", legend="Périodes"))
    img2_path = os.path.join(parent_img_path, generate_barplots(title=title2, file_name='paired_period_turnovers.png',data={'Catégorie':["Chiffres d'affaire"],last_period_str: [orders_['last_period_turnover']],before_period_str: [orders_['period_before_turnover']],}, ylab="Chiffres d'affaire", legend="Périodes"))
    img3_path = os.path.join(parent_img_path, generate_barplots(title=title3, file_name='paired_period_orders_by_type.png', data={'Catégorie': [last_period_str, before_period_str], 'Sur place': [orders_type['on_site_orders_info']['last_period_order_count'], orders_type['on_site_orders_info']['period_before_order_count']], 'Livrées': [orders_type['delivery_orders_info']['last_period_order_count'], orders_type['delivery_orders_info']['period_before_order_count']]}, xlab='Périodes', ylab="Commandes", legend="Types de commandes"))
    img4_path = os.path.join(parent_img_path, generate_barplots(title=title4, file_name='paired_period_turnovers_by_type.png', data={'Catégorie': [last_period_str, before_period_str], 'Sur place': [orders_type['on_site_orders_info']['last_period_turnover'], orders_type['on_site_orders_info']['period_before_turnover']], 'Livrées': [orders_type['delivery_orders_info']['last_period_turnover'], orders_type['delivery_orders_info']['period_before_turnover']], }, ylab="Chiffres d'affaires", xlab='Périodes', legend="Périodes"))

    try:
        img5_path = os.path.join(parent_img_path, generate_polarArea('previous_top_sold_pizzas.png', title=title5,categories=list(pizzas_count_sold['previous_period'].keys()),  values=list(pizzas_count_sold['previous_period'].values())))
    except Exception as e:
        img5_path = os.path.join(parent_img_path, 'Pas de données disponibles.png')

    try:
        img6_path = os.path.join(parent_img_path, generate_polarArea('before_top_sold_pizzas.png', title=title6,categories=list(pizzas_count_sold['before_period'].keys()), values=list(pizzas_count_sold['before_period'].values())))
    except Exception as e:
        img6_path = os.path.join(parent_img_path, 'Pas de données disponibles.png')

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

    return [img1_path,img2_path,img3_path,img4_path,img5_path,img6_path]


def send_period_digest(period, to_email, subject):

    print("send_period_digest called")

    period_in_mail = {'week': "hebdomadaire", 'month': "mensuel"}.get(period)

    html_content = f"""
        <h2 style="text-align: center;">Faisons le point !!! 😉</h2>
        <p style="text-align: center;">Hello Izoua, voici votre digest {period_in_mail}:</p>
    """

    # Ajouter un lien vers le fichier PDF dans l'HTML
    download_link1 = '<p><a href="cid:pdf_attachment_1">Télécharger le rapport complet.</a></p>'
    download_link2 = '<p><a href="cid:pdf_attachment_2">Télécharger les données graphiques</a></p>'
    download_link = ''.join([download_link1,download_link2])
    html_content += download_link

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

    pdf_paths = [create_pdf_with_data()[1], create_pdf_with_images(image_paths=get_chart_imgs_path(period), titles=['Commandes','Distribution des Commandes','Pizzas les plus vendues'], output_file='charts.pdf')]

    """if not os.path.exists(pdf_path):
        pdf_path.parent.mkdir(parents=True, exist_ok=True)"""

    # Joindre les fichiers PDF
    for i, pdf_path in enumerate(pdf_paths):
        with open(pdf_path, "rb") as pdf_file:
            pdf_attachment = MIMEBase("application", "octet-stream")
            pdf_attachment.set_payload(pdf_file.read())
            encoders.encode_base64(pdf_attachment)
            pdf_attachment.add_header(
                "Content-Disposition",
                f"attachment; filename={pdf_path.split('/')[-1]}"
            )
            pdf_attachment.add_header("Content-ID", f"<pdf_attachment_{i}>")  # Identifier unique
            message.attach(pdf_attachment)

    # Envoi de l'email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Chiffrement TLS
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_string())