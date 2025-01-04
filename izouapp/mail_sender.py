import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from environ import environ

from izouapp.views import get_periodicaly_orders_info, get_periodicaly_orders_by_type, \
    get_most_and_least_sold_pizza_names
from izouaproject import settings
from izouaproject.settings import BASE_DIR


env = environ.Env()
environ.Env.read_env(env_file=str(BASE_DIR / 'izouapp' / '.env'))

def set_html_content(period):

    orders_ = get_periodicaly_orders_info(period=period)  # toutes les commandes des deux dernieres périodes

    orders_type = get_periodicaly_orders_by_type(period=period)  # toutes les commandes des deux dernieres periodes mais par type

    pizzas_count_sold = get_most_and_least_sold_pizza_names(period=period)

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
        <h2>Faisons le point !!! ☺</h2>
        <p>Hello Izoua, voici votre digest hbedomadaire/mensuel:</p>
    
        <h3>Commandes</h3> <!-- ******************************************************* -->
        <!--affricher deux barplots cote a cote ou chaque bar plot affiche respectivement le nombre de comandes et le chiffre d'affaire des deux semaines-->
        <div class="row">
            <div class="card col-md-6" style="width: 18rem;">
            <!-- dans ce canvas ci sera affiché la distribution du nombre de commandes des deux précédentes semaines -->
                <canvas id="chart1"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Distributions des commandes sur les deux dernières semaines</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                <!-- dans ce canvas ci sera affiché la distribution des chiffres d'affaires des deux précédentes semaines -->
                <canvas id="chart2"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Distributions des chiffres d'affaires sur les deux dernières semaines</h5>
                </div>
            </div>
        </div>
    
        <h3>Distribution des Commandes</h3> <!-- ******************************************************* -->
        <!--afficher 4 barplot sur deux lignes, le premier barplot met en relief le nombre de commandes sur place et livrées, le deuxieme,
        les CA générés par ces deux types de commandes et tout ceci pour la semaine qui vient de passer.
        le troisieme et le quatrième reprennent le meme schema mais pour la semaine d'avant.
    
        rangée additionnelle pour afficher la proportion des commandes sur place et en ligne pour les deux semaines sous forme de deux pie chart cote à cote-->
    
        <div class="row">
            <div class="card col-md-6" style="width: 18rem;">
                <canvas id="chart3"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Distributions des commandes sur place / livrées sur les deux dernières semaines</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                <canvas id="chart4"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Distributions des chiffres d'affaire par types de commandes sur les deux dernières semaines</h5>
                </div>
            </div>
            
        </div>
        <div class="row">
            <div class="card col-md-6" style="width: 18rem;">
                <canvas id="chart5"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Proportion des types commandes pour la semaine précédente</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                <canvas id="chart6"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Proportion des types commandes pour la semaine d'avant</h5>
                </div>
            </div>
        </div>
    
        <h3>Distribution des livraisons par livreurs</h3> <!-- ******************************************************* -->
    
        <!--affiche d'abord le nombre total de livraisons
        puis comme d'ans l'interface manager, affiche les infos par livreurs-->
    
        <h3>Pizzas les plus vendues</h3> <!-- ******************************************************* -->
        
        <!--deux rangées contenant chacunes 2 barplots/polarchart affichant la distribution des ventes par pizzas durant chacune des 2 semaines pour voir lesquelles ont été les plus vendues-->
        <div class="row">
            <div class="card col-md-6" style="width: 18rem;">
                <canvas id="chart7"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Distributions des pizzas vendues pour la semaine précédente</h5>
                </div>
            </div>
            <div class="card col-md-6" style="width: 18rem;">
                <canvas id="chart8"></canvas>
                <div class="card-body">
                    <h5 class="card-title">Distributions des pizzas vendues pour la semaine d'avant</h5>
                </div>
            </div>
        </div>
    
    
    <script>
        const ctx1 = document.getElementById('chart1');
        const ctx2 = document.getElementById('chart2');
        const ctx3 = document.getElementById('chart3');
        const ctx4 = document.getElementById('chart4');
        const ctx5 = document.getElementById('chart5');
        const ctx6 = document.getElementById('chart6');
        const ctx7 = document.getElementById('chart7');
        const ctx8 = document.getElementById('chart8');
    
        new Chart(ctx1,{type: 'bar',
                        data: {labels:['Commandes'],
                                datasets:[
                                        {
                                        label:["Semaine précédente"]
                                        ,data:"""+f"""{orders_['last_week_order_count']}"""+"""
                                        ,fill:true
                                        ,borderColor:'rgb(0,255,0)'
                                        ,backgroundColor:'rgb(50,255,0)'
                                        },
                                        {
                                        label:["Semaine d'avant"]
                                        ,data: """+f"""{orders_['week_before_order_count']}"""+"""
                                        ,fill: true
                                        ,borderColor: 'rgb(0,255,0)'
                                        ,backgroundColor:'rgb(50,255,0)'
                                        }
                                        ]
                                    },
                        options: {responsive: true,
                                plugins: {
                                    legend: {
                                    position: 'top',
                                    },
                                title: {
                                    display: true,
                                    text: "Chiffres des commandes Semaine précédente vs Semaine d'avant"
                                }
                                        }
                                },
                        }
                    )
    
        new Chart(ctx2,{type: 'bar',
                        data: {labels:["Chiffres d'affaires"],
                                datasets:[
                                        {
                                        label:["Semaine précédente"]
                                        ,data:"""+f"""{orders_['last_week_turnover']}"""+"""
                                        ,fill:true
                                        ,borderColor:'rgb(0,255,0)'
                                        ,backgroundColor:'rgb(50,255,0)'
                                        },
                                        {
                                        label:["Semaine d'avant"]
                                        ,data: """+f"""{orders_['week_before_turnover']}"""+"""
                                        ,fill: true
                                        ,borderColor: 'rgb(0,255,0)'+
                                        ,backgroundColor:'rgb(50,255,0)'
                                        }
                                        ]
                                    },
                        options: {responsive: true,
                                plugins: {
                                    legend: {
                                    position: 'top',
                                    },
                                title: {
                                    display: true,
                                    text: "Chiffres d'affaire Semaine précédente vs Semaine d'avant"
                                }
                                        }
                                },
                        }
                    )
    
        new Chart(ctx3,{type: 'bar',
        data: {labels:["Commandes sur places", "Commandes livrées"],
                datasets:[
                        {
                        label:["Semaine précédente"]
                        ,data:["""+f"""{orders_type['on_site_orders_info']['last_week_order_count']}"""+""", """+f"""{orders_type['delivery_orders_info']['last_week_order_count']}"""+"""]
                        ,fill:true
                        ,borderColor:'rgb(0,255,0)'
                        ,backgroundColor:'rgb(50,255,0)'
                        },
                        {
                        label:["Semaine d'avant"]
                        ,data:["""+f"""{orders_type['on_site_orders_info']['week_before_order_count']}"""+""", """+f"""{orders_type['delivery_orders_info']['week_before_order_count']}"""+"""]
                        ,fill: true
                        ,borderColor: 'rgb(0,255,0)'
                        ,backgroundColor:'rgb(50,255,0)'
                        }
                        ]
                    },
        options: {responsive: true,
                plugins: {
                    legend: {
                    position: 'top',
                    },
                title: {
                    display: true,
                    text: "Chiffres d'affaire Semaine précédente vs Semaine d'avant"
                }
                        }
                },
        }
                )
    
        new Chart(ctx4,{type: 'bar',
        data: {labels:["Chiffres d'affaires (commandes sur places)", "Chiffres d'affaires (Commandes livrées)"],
                datasets:[
                        {
                        label:["Semaine précédente"]
                        ,data:["""+f"""{orders_type['on_site_orders_info']['last_week_turnover']}"""+""", """+f"""{orders_type['delivery_orders_info']['last_week_turnover']}"""+"""]
                        ,fill:true
                        ,borderColor:'rgb(0,255,0)'
                        ,backgroundColor:'rgb(50,255,0)'
                        },
                        {
                        label:["Semaine d'avant"]
                        ,data:["""+f"""{orders_type['on_site_orders_info']['week_before_turnover']}"""+""", """+f"""{orders_type['delivery_orders_info']['week_before_turnover']}"""+"""]
                        ,fill: true
                        ,borderColor: 'rgb(0,255,0)'
                        ,backgroundColor:'rgb(50,255,0)'
                        }
                        ]
                    },
        options: {responsive: true,
                plugins: {
                    legend: {
                    position: 'top',
                    },
                title: {
                    display: true,
                    text: "Chiffres d'affaire par type de commandes Semaine précédente vs Semaine d'avant"
                }
                        }
                },
        }
    )
    
    new Chart(ctx5,{type: 'polarArea',
        data: {labels:["Proportions (Commandes sur places)", "Proportions (Commandes livrées)"],
                datasets:[
                        {
                        label:["Semaine précédente"]
                        ,data:["""+f"""{orders_type['on_site_orders_info']['last_week_on_site_out_of_total']}"""+""", """+f"""{orders_type['delivery_orders_info']['last_week_delivery_out_of_total']}"""+"""]
                        ,fill:true
                        ,borderColor:'rgb(0,255,0)'
                        ,backgroundColor:['rgb(50,255,0)','rgb(0,255,80)']
                        }
                        ]
                    },
        options: {responsive: true,
            scales:{
                r: {
                  pointLabels: 
                    {
                    display: true,
                    centerPointLabels: true,
                    font: 
                    {
                    size: 18
                    }
                    }
                    },
                    },
                    plugins: 
                    {
                    legend: 
                    {
                    position: 'top',
                    },
                    title: 
                    {
                    display: true,
                    text: "Proportions (Commandes sur places vs Commandes livrées)"
                    }
                    }
                },
        }
    )
    
    new Chart(ctx6,{type: 'polarArea',
        data: {labels:["Proportions (Commandes sur places)", "Proportions (Commandes livrées)"],
                datasets:[
                        {
                        label:["Semaine d'avant"]
                        ,data:["""+f"""{orders_type['on_site_orders_info']['last_week_delivery_out_of_total']}"""+""", """+f"""{orders_type['delivery_orders_info']['week_before_delivery_out_of_total']}"""+"""]
                        ,fill:true
                        ,borderColor:'rgb(0,255,0)'
                        ,backgroundColor:['rgb(50,255,0)','rgb(0,255,80)']
                        }
                        ]
                    },
        options: {responsive: true,
            scales:{
                r: {
                    pointLabels: 
                    {
                    display: true,
                    centerPointLabels: true,
                    font: 
                    {
                    size: 18
                    }
                    }
                    },
                    },
                    plugins: 
                    {
                    legend: 
                    {
                    position: 'top',
                    },
                    title: 
                    {
                    display: true,
                    text: "Proportions (Commandes sur places vs Commandes livrées)"
                    }
                    }
                },
        }
    )
    
    new Chart(ctx7,{type: 'polarArea',
        data: {labels:["""+f"""{list(pizzas_count_sold.previous_week.keys())}"""+"""],
                datasets:[
                        {
                        label:["Semaine précédente"]
                        ,data:["""+f"""{list(pizzas_count_sold.previous_week.values())}"""+"""]
                        ,fill:true
                        ,borderColor:'rgb(0,255,0)'
                        ,backgroundColor:['rgb(50,255,0)','rgb(0,255,80)']
                        }
                        ]
                    },
        options: {responsive: true,
            scales: {
                r:  {
                    pointLabels: 
                    {
                    display: true,
                    centerPointLabels: true,
                    font: 
                    {
                    size: 18
                    }
                    }
                    },
                    },
                    plugins:
                    {
                    legend: 
                    {
                    position: 'top',
                    },
                    title:
                    {
                    display: true,
                    text: "Distribution des pizzas vendues pour la semaine précédente"
                    }
                    }
                },
        }
    )
    
    new Chart(ctx8,{type: 'polarArea',
        data: {labels:["""+f"""{list(pizzas_count_sold.before_week.keys())}"""+"""],
                datasets:[
                        {
                        label:["Semaine d'avant"]
                        ,data:["""+f"""{list(pizzas_count_sold.before_week.values())}"""+"""]
                        ,fill:true
                        ,borderColor:'rgb(0,255,0)'
                        ,backgroundColor:['rgb(50,255,0)','rgb(0,255,80)']
                        }
                        ]
                    },
        options: {responsive: true,
            scales: {
                r:  {
                    pointLabels: 
                    {
                    display: true,
                    centerPointLabels: true,
                    font: 
                    {
                    size: 18
                    }
                    }
                    },
                    },
                    plugins:
                    {
                    legend: 
                    {
                    position: 'top',data
                    },
                    title:
                    {
                    display: true,
                    text: "Distribution des pizzas vendues pour la semaine d'avant"
                    }
                    }
                },
        }
    )
    </script>
    </body>
    </html>
    """

    return html_content

def send_period_digest(period, to_email, subject):

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