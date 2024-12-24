from django.contrib import admin
from django.contrib.auth.models import Group
from .models import *

# Register your models here.
admin.site.unregister(Group)

@admin.register(PizzaName)
class PizzaNameAdmin(admin.ModelAdmin):
    fields = ('name',
        'description',)

    readonly_fields = ('description',)
    list_display = (
        'name',
    )

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
    fields = ('deliveryHour',
              'deliveryAdress',
              'payment_method',
              'create_at',
              'update_at',
              'surplace',
              'status',
              'deliveryPerson',
              'pizzas',
              'client',
              'deliveryPrice',
              'edit_requested',
              'description',)
    readonly_fields = ('description',)

    list_display = (
        'order_id',
        'payment_method',
        'create_at',
        'status',
        'client',
        'deliveryHour',
        'deliveryAdress',
        'get_pizza_id',
        'deliveryPrice',
        'pizza_and_extratopping_price',
        'total_price',
    )
    search_fields = (
        'client',
        'pizzas',
        'extratoppings',
        'status',
    )

    def get_pizza_id(self, obj):
        return ", ".join([pizza.name for pizza in obj.pizzas.all()])

    def get_extratoppings(self, obj):
        return ", ".join([extratopping.name for extratopping in obj.extratoppings.all()])

    get_pizza_id.short_description = 'Pizzas'
    get_extratoppings.short_description = 'Suppléments'

@admin.register(Client)
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

@admin.register(Pizza)
class PizzaAdmin(admin.ModelAdmin):
    readonly_fields = ('description',)
    list_display = (
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