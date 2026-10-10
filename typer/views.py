from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from .models import Match, Prediction, User
from .forms import RegistrationForm, PredictionForm


@login_required
def match_list_view(request):
    matches = Match.objects.select_related("league", "home_team", "away_team")
    upcoming = matches.exclude(status=Match.Status.FINISHED).order_by("scheduled_at")
    finished = matches.filter(status=Match.Status.FINISHED)
    return render(request, "typer/match_list.html", {
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


@login_required
def predict_view(request, match_id):
    match = get_object_or_404(Match, pk=match_id)

    if match.is_locked:
        messages.error(request, "Typowanie tego meczu jest już zakończone.")
        return redirect("typer:match_list")

    existing_prediction = Prediction.objects.filter(user=request.user, match=match).first()

    if request.method == "POST":
        form = PredictionForm(request.POST, instance=existing_prediction)
        if form.is_valid():
            prediction = form.save(commit=False)
            prediction.user = request.user
            prediction.match = match
            prediction.save()
            messages.success(request, "Typ zapisany.")
            return redirect("typer:match_list")
    else:
        form = PredictionForm(instance=existing_prediction)

    return render(request, "typer/predict.html", {"form": form, "match": match})

@login_required
def ranking_view(request):
    users = (
        User.objects.annotate(total_points=Sum("predictions__points__points_awarded"))
        .filter(total_points__isnull=False)
        .order_by("-total_points", "username")
    )
    return render(request, "typer/ranking.html", {"users": users})