from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import User, Prediction, League, TypingGroup, Sport


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


class TypingGroupForm(forms.ModelForm):
    class Meta:
        model = TypingGroup
        fields = ["name", "league"]
        labels = {"name": "Nazwa grupy", "league": "Rozgrywki"}
        help_texts = {"league": "Wyniki meczóe tych rozgrywek będą liczone w rankingu grupy."}
        widgets = {
            "name": forms.TextInput(attrs={'class': 'form-control'}),
            "league": forms.Select(attrs={'class': 'select'}), }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['league'].queryset = (
            League.objects.filter(end_date__gte=timezone.localdate()).select_related("sport").
            order_by("sport__name", "name")
        )
        self.fields['league'].empty_label = "Wybierz rozgrywki"
        self.fields['league'].label_from_instance = (
            lambda league: f"{league.name} {league.year}({league.sport.name})"
        )


class JoinGroupForm(forms.Form):
    code = forms.CharField(
        max_length=20,
        label="Kod zaproszenia",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
