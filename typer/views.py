from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegistrationForm


def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # od razu loguje po rejestracji
            return redirect("typer:home")
    else:
        form = RegistrationForm()

    return render(request, "typer/register.html", {"form": form})

def home_view(request):
    return render(request, "typer/home.html")