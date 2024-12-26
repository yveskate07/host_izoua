from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

from django.db import models


# Create your models here.

class MyUserManager(BaseUserManager):

    def create_user(self, username, email=None, password=None):
        if not username:
            raise ValueError("L'utilisateur doit avoir un nom d'utilisateur.")
        if not email:
            raise ValueError("L'utilisateur doit avoir une adresse email.")
        if not password:
            raise ValueError("L'utilisateur doit avoir un mot de passe.")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None):
        user = self.create_user(username=username, email=email, password=password)
        user.is_staff = True
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class Manager_or_Admin(AbstractBaseUser, PermissionsMixin):

    username = models.CharField(max_length=50,  blank=False, null=False, unique=True)
    email = models.EmailField(unique=True, blank=False, null=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_admin =  models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email",]

    def description(self):
        return f'Base de données des utilisateurs.\n\nis_active: designe si cet utilisateur fais partie oui ou non de IzouaPizza. ;\n\nis_admin: Accorde ou pas certains privileges à cet utilisateur, dans ce cas-ci, definir un utilisateur comme admin lui permettra simplement de modifier une commande. ;\n\nis_superuser: cet utilisateur à tous les droits.'

    description.short_description = "Description: "

    class Meta:
        verbose_name = 'utilisateur'

    def __str__(self):
        return f"Utilisateur {self.username}"

