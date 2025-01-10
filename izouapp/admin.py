from django.contrib import admin
from django.contrib.auth.models import Group
from .models import *


# Register your models here.
admin.site.unregister(Group)

def check_and_update_inventory(obj):

    if len(DailyInventory.objects.filter(date=obj.create_at)):
        current_inventory = DailyInventory.objects.filter(date=obj.create_at)
        soldTotalStart = {'Petite': current_inventory[0].sold_small_pizzas_count,
                          'Grande': current_inventory[0].sold_large_pizzas_count}

        current_inventory.update(
            sold_small_pizzas_count=soldTotalStart['Petite'] - obj.get_nb_sold_pizzas_by_sizes['Petite'],
            # son solde de petites / grandes pizzas s'ajoute à l'inventaire du même jour
            sold_large_pizzas_count=soldTotalStart['Grande'] - obj.get_nb_sold_pizzas_by_sizes['Grande'])



@admin.register(PizzaName)
class PizzaNameAdmin(admin.ModelAdmin):
    fields = ('name',
        'description',)

    readonly_fields = ('description',)
    list_display = (
        'name',
    )

#@admin.register(SendMailReminder)
class SendMailReminderAdmin(admin.ModelAdmin):
    fields = ('weekly_digest_sent',
        'monthly_digest_sent',)

    list_display = ('weekly_digest_sent',
        'monthly_digest_sent',)


@admin.register(DeliveryPerson)
class DeliveryPersonAdmin(admin.ModelAdmin):
    fields = ('name',
              'phone_number',
              'add_at',
              'description',)

    readonly_fields = ('description',)
    list_display = (
        'name',
        'phone_number'
    )

@admin.register(orders)
class ordersAdmin(admin.ModelAdmin):

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            check_and_update_inventory(obj)

        super().delete_queryset(request, queryset)

    list_per_page = 30

    fields = ('deliveryHour',
              'deliveryAdress',
              'payment_method_order',
              'payment_method_delivery',
              'create_at',
              'update_at',
              'surplace',
              'status',
              'deliveryPerson',
              'client',
              'deliveryPrice',
              'description',)
    readonly_fields = ('description',)

    list_display = (
        'client',
        'payment_method_order',
        'payment_method_delivery',
        'create_at',
        'status',
        'deliveryHour',
        'deliveryAdress',
        'get_pizza_id',
        'deliveryPrice',
        'pizza_and_extratopping_price',
        'total_price',
    )
    """search_fields = (
        'client',
        'pizzas',
        'extratoppings',
        'status',
    )"""
    def delete_model(self, request, obj): # quand une commande est supprimée

        check_and_update_inventory(obj)

        super().delete_model(request, obj)

    def get_pizza_id(self, obj):
        return ", ".join([pizza.name for pizza in obj.pizzas.all()])

    def get_extratoppings(self, obj):
        return ", ".join([extratopping.name for extratopping in obj.extratoppings.all()])

    get_pizza_id.short_description = 'Pizzas'
    get_extratoppings.short_description = 'Suppléments'

#@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    fields = ('name',
              'phone_number',
              'adress',
              'description',)

    readonly_fields = ('description',)
    list_display = (
        'name',
        'phone_number',
        'adress',
    )

#@admin.register(Pizza)
class PizzaAdmin(admin.ModelAdmin):
    readonly_fields = ('description',)
    list_display = (
            'create_at',
            'name',
            'moitie_1',
            'moitie_2',
            'status',
            'size',
        )

    class Media:
        js = ('izouapp/js/custom_admin.js',)


@admin.register(PizzaSizePrice)
class PizzaSizePriceAdmin(admin.ModelAdmin):
    fields = ('Petite',
              'Grande',
              'description',)

    readonly_fields = ('description',)
    list_display = (
        'Petite',
        'Grande',
    )

@admin.register(DailyInventory)
class DailyInventoryAdmin(admin.ModelAdmin):
    fields = ('small_pizzas_count',
              'large_pizzas_count',
              'sold_small_pizzas_count',
              'sold_large_pizzas_count',
              'date',
              'description',)

    readonly_fields = ('description',)
    list_display = (
        'date',
        'large_pizzas_count',
        'small_pizzas_count',
        'sold_small_pizzas_count',
        'sold_large_pizzas_count',
        'remaining',
    )

@admin.register(ExtraTopping)
class ExtraToppingAdmin(admin.ModelAdmin):
    fields = ('name',
              'price',
              'description',)
    readonly_fields = ('description',)
    list_display = (
        'name',
        'price',
    )