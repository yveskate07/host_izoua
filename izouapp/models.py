from datetime import datetime, timedelta

import django
from asgiref.sync import sync_to_async
from django.db import models
from django.utils import timezone


class SendMailReminder(models.Model):
    weekly_digest_sent = models.BooleanField(default=False)
    monthly_digest_sent = models.BooleanField(default=False)

# Create your models here.
class DeliveryPerson(models.Model):
    id_deliveryman = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=False, null=False)
    phone_number = models.CharField(max_length=20,blank=True, null=True, default='')
    email = models.EmailField(blank=True,null=True)
    add_at = models.DateField(max_length=50,  blank=False, null=False, default=django.utils.timezone.now) # quand il a debuté


    def description(self):
        return f'Base de données des livreurs. Le numéro de telephone devra toujours commencer par +221.'

    description.short_description = "Description: "


    class Meta:
        verbose_name = 'livreur'


    def __str__(self):
        return self.name

class PizzaSizePrice(models.Model):

    Petite = models.IntegerField(blank=False, null=False, default=0)
    Grande = models.IntegerField(blank=False, null=False, default=0)


    def description(self):
        return f"Base de données contenant les prix des pizzas selon la taille. Veuillez ne pas ajouter d'autres lignes, modifiez seulement les prix."

    description.short_description = "Description: "


    class Meta:
        verbose_name = 'Prix par taille de pizza'


    def __str__(self):
        return f'Pizza petite taille: {self.Petite} \n Pizza grande taille: {self.Grande}'

class ExtraTopping(models.Model): # classe pour les supplements de pizza
    extratopping_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50,  blank=False, null=False, unique=True,)
    price = models.IntegerField(blank=False, null=False)


    def description(self):
        return f'Base de données contenant les noms et prix des supplements. Vous pouvez ajouter ou supprimer des lignes'

    description.short_description = "Description: "


    class Meta:
        verbose_name = 'Supplément'


    def __str__(self):
        return f'Supplément {self.name}'

class PizzaName(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, blank=False, null=False, default='Pizza normale',unique=True)


    def description(self):
        return f'Base de données contenant les noms des pizzas. Ajoutez de nouveaux noms ou supprimez en.'

    description.short_description = "Description: "


    class Meta:
        verbose_name = 'Noms des pizza'


    def __str__(self):
        return f'Pizza {self.name}'

class Pizza(models.Model):

    STATUS = [('Spéciale','Spéciale'),
              ('Normale','Normale'),]

    SIZE = [('Grande','Grande'),
            ('Petite','Petite')]

    pizza_id = models.AutoField(primary_key=True)
    create_at = models.DateField(blank=False, null=False, default=django.utils.timezone.now)
    moitie_1 = models.CharField(max_length=50, null=True, blank=True)
    moitie_2 = models.CharField(max_length=50,  null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS, default='Normale') # est une pizza speciale ou pas
    name = models.CharField(max_length=50, blank=False, null=False, default='Pizza normale')
    size = models.CharField(max_length=50, choices=SIZE, default='Grande')
    extratoppings = models.ManyToManyField(ExtraTopping)


    def description(self):
        return f"Base de données contenant les informations de chaque ayant été vendu. Il n'est pas conseillé d'enregistrer de nouvelles données vous même à moins que ce soit nécéssaire. \nPar défaut, le programme lui-même stocke les pizzas achetées."

    description.short_description = "Description: "


    class Meta:
        verbose_name = 'pizzas achetée'


    @property
    def price(self):
        plus_500 = 0 if self.status == 'Normale' else 500
        extratopping_price = sum([extratopping.price for extratopping in self.extratoppings.all()])
        try:
            size_prices = PizzaSizePrice.objects.first()
            if not size_prices:
                raise ValueError("Aucun prix de pizza n'est défini.")

            return size_prices.Grande + extratopping_price + plus_500 if self.size == "Grande" else size_prices.Petite + extratopping_price + plus_500
        except PizzaSizePrice.DoesNotExist:
            return 0  # Retourne un prix par défaut si aucun prix n'est configuré

    def __str__(self):
        if self.extratoppings.all():
            if self.status == 'Normale':
                return self.name + ' Taille '+ self.size +' Supplements: ' + ", ".join([extratopping.name for extratopping in self.extratoppings.all()])
            else:
                return self.moitie_1 +' - ' + self.moitie_2 + ' Taille ' + self.size + ' Supplements: ' + ", ".join(
                    [extratopping.name for extratopping in self.extratoppings.all()])

        elif self.status == 'Normale':
            return self.name + ' Taille ' + self.size
        else:
            return self.moitie_1 + ' - ' + self.moitie_2 + ' Taille ' + self.size

    @property
    def get_name(self):
        if self.status == 'Normale':
            return self.name
        return self.moitie_1 + ' - ' + self.moitie_2

class Client(models.Model):
    id_client = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50,  blank=False, null=False)
    #number = PhoneNumberField(validators=[validate_senegal_phone_number],blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    adress = models.CharField(max_length=50,  blank=True, default='', null=True)


    def description(self):
        return f'Base de données contenant les informations des clients ayant déjà commandé chez Izoua Pizza. Le numéro de telephone devra toujours commencer par +221.'

    description.short_description = "Description: "


    class Meta:
        verbose_name = 'client'


    def __str__(self):
        if self.adress and self.phone_number:
            return self.name + ' ' + self.adress + '\n' + self.phone_number

        return self.name

def get_current_time():
    return django.utils.timezone.now().time()

class orders(models.Model):

    STATUS_CHOICES = [
        ('delivered','Livrée'),
        ('canceled', 'Annulée'),
        ('on-site', 'Sur place'),
        ('pending','En attente'),
    ]

    PAYMENT_METHOD = [('izoua','Izoua'),('delivered_man','Livreur')] # payment_method,

    order_id = models.AutoField(primary_key=True)
    deliveryHour = models.TimeField(blank=True, null=True) # champs à renseigner dans le cas d'une commande sur livraison
    onSiteHour = models.TimeField(blank=False, null=False, default=get_current_time)
    deliveryAdress = models.CharField(max_length=50,  blank=True, null=True) # champs à renseigner dans le cas d'une commande sur livraison
    payment_method_on_site = models.CharField(max_length=50, blank=False, null=False, choices=PAYMENT_METHOD, default='izoua') # champs à renseigner dans le cas d'une commande sur place
    payment_method_order = models.CharField(max_length=50, blank=False, null=False, choices=PAYMENT_METHOD)  # champs à renseigner, moyen de paiement de la livraison
    payment_method_delivery = models.CharField(max_length=50, blank=False, null=False, choices=PAYMENT_METHOD)  # champs à renseigner, moyen de paiement de la commande
    create_at = models.DateField(blank=False, null=False,default=django.utils.timezone.now)
    update_at = models.DateField(blank=True,default=django.utils.timezone.now)
    surplace = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=False, default='pending')
    edit_requested = models.BooleanField(default=False)
    deliveryPerson = models.ForeignKey(DeliveryPerson, on_delete=models.SET_NULL, null=True, blank=True) # champs à renseigner dans le cas d'une commande sur livraison
    pizzas = models.ManyToManyField(Pizza)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True)
    deliveryPrice = models.IntegerField(null=True, blank=True, default=0) # champs à renseigner dans le cas d'une commande sur livraison
    notified = models.BooleanField(default=False)
    html_code = models.TextField(blank=False, null=False, default='') # code html de la commande

    def description(self):
        return f'Base de données contenant les informations des commandes livrées ou annulées. \nedit requested: indique si une modification pour cette commande a été demandée, pour refuser cette modification, decocher cette case.'

    description.short_description = "Description: "


    class Meta:
        verbose_name = 'commande'


    @property
    def total_price(self):
        if self.deliveryPrice:
            return sum([pizza.price for pizza in self.pizzas.all()]) + int(self.deliveryPrice)

        return sum([pizza.price for pizza in self.pizzas.all()])

    @property
    def pizza_and_extratopping_price(self):
        return sum([pizza.price for pizza in self.pizzas.all()])

    def __str__(self):
        return f'Commande No {str(self.order_id)} du {str(self.create_at)}'

    @property
    async def str_for_alert(self):
        #return f"La commande de M/Mme {self.client} {self.deliveryAdress} est à livrer dans moins de 30 min"
        client = await sync_to_async(lambda: self.client)()  # Récupération asynchrone de l'objet client
        return f"La commande de M/Mme {client} {self.deliveryAdress} est à livrer dans moins de 30 min"

    @property
    def get_nb_sold_pizzas_by_sizes(self):
        sold={'Petite':0,'Grande':0}
        for pizza in self.pizzas.all():
            if pizza.size=='Petite':
                sold['Petite'] += 1
            else:
                sold['Grande'] += 1

        return sold

    def is_deadline_close(self):

        now = datetime.now()  # Date et heure actuelles
        today_delivery_time = datetime.combine(self.create_at, self.deliveryHour)  # Combine la date du jour avec l'heure de livraison

        time_difference = today_delivery_time - now  # Calculer la différence
        return timedelta(0) <= time_difference <= timedelta(minutes=30)


class DailyInventory(models.Model):
    inventaire_id = models.AutoField(primary_key=True)
    small_pizzas_count = models.IntegerField(blank=False, null=False, default=0)
    large_pizzas_count = models.IntegerField(blank=False, null=False, default=0)
    sold_small_pizzas_count = models.IntegerField(blank=False, null=False, default=0)
    sold_large_pizzas_count = models.IntegerField(blank=False, null=False, default=0)
    date = models.DateField(blank=False, null=False, default=django.utils.timezone.now, unique=True,)

    def description(self):
        return f'Base de données contenant les informations quotidiennes des quantités de pates nécéssaires pour preparer les pizzas'

    description.short_description = "Description: "

    class Meta:
        verbose_name = 'Inventaire'

    @property
    def remaining(self):
        return self.small_pizzas_count + self.large_pizzas_count - (self.sold_small_pizzas_count + self.sold_large_pizzas_count)

    @property
    def sold(self):
        return self.sold_small_pizzas_count + self.sold_large_pizzas_count

    def __str__(self):
        return f'Inventaire du {self.date}'

    def save(self, *args, **kwargs):
        # Vérification 1 : Les pizzas vendues (small) ne doivent pas excéder le stock
        if self.sold_small_pizzas_count > self.small_pizzas_count:
            raise ValueError(
                "Le nombre de petites pizzas vendues ne peut pas dépasser le stock disponible."
            )

        # Vérification 2 : Les pizzas vendues (large) ne doivent pas excéder le stock
        if self.sold_large_pizzas_count > self.large_pizzas_count:
            raise ValueError(
                "Le nombre de grandes pizzas vendues ne peut pas dépasser le stock disponible."
            )

        # Appeler la méthode `save` de la classe parente
        super().save(*args, **kwargs)

