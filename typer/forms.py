from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import User, League, TypingGroup


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Konto z tym adresem e-mail już istnieje.")
        return email


class TypingGroupForm(forms.ModelForm):
    class Meta:
        model = TypingGroup
        fields = ["name", "league"]
        labels = {"name": "Nazwa grupy", "league": "Rozgrywki"}
        help_texts = {"league": "Wyniki meczów tych rozgrywek będą liczone w rankingu grupy."}
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
            lambda league: f"{league.name} {league.year} ({league.sport.name})"
        )


class JoinGroupForm(forms.Form):
    code = forms.CharField(
        max_length=20,
        label="Kod zaproszenia",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
