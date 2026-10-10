from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Prediction

class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class PredictionForm(forms.ModelForm):
    class Meta:
        model = Prediction
        fields = ("predicted_home", "predicted_away")
        labels = {
            "predicted_home": "Bramki gospodarzy",
            "predicted_away": "Bramki gości",
        }
        widgets = {
            "predicted_home": forms.NumberInput(attrs={'class': 'form-control', "min": 0}),
            "predicted_away": forms.NumberInput(attrs={'class': 'form-control', "min": 0}),
        }