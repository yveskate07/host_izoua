from django import forms
from django.contrib.auth.forms import AuthenticationForm

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150, required=True , widget=forms.TextInput(attrs={'class': 'form-control','placeholder': "Entrer le nom d'utilisateur", "autofocus": True}))
    password = forms.CharField(strip=False, widget=forms.PasswordInput(attrs={'class': 'form-control','placeholder': "Entrer mot de passe", "autocomplete": "current-password"}))

