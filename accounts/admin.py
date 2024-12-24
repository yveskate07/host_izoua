from django.contrib import admin
from django.contrib.auth.hashers import is_password_usable
from accounts.models import Manager_or_Admin


# Register your models here.

@admin.register(Manager_or_Admin)
class Manager_or_AdminAdmin(admin.ModelAdmin):
    fields = ('password',
              'username',
              'email',
              'is_active',
              'is_admin',
              'is_superuser',
              'description',)

    readonly_fields = ('description',)
    ordering = ('username',)

    list_display = ('username','email', 'is_admin', 'is_superuser',)

    def save_model(self, request, obj, form, change):
        
        # Vérifiez si le mot de passe est déjà hashé
        if not obj.password.startswith('pbkdf2_sha256$'):  # Si le mot de passe utilisable (non hashé)
            obj.set_password(obj.password)
        
        super().save_model(request, obj, form, change)
