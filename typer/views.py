from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import Match
from .forms import RegistrationForm

@login_required
def match_list_view(request):
    matches = Match.objects.select_related("league", "home_team", "away_team")
    upcoming = matches.exclude(status=Match.Status.FINISHED).order_by("scheduled_at")
    finished = matches.filter(status=Match.Status.FINISHED)
    return render(request,"typer/match_list.html", {
        "upcoming": upcoming,
        "finished": finished,
    })

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