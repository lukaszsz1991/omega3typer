from urllib.request import HTTPRedirectHandler

from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.template.backends import django
from django.http import HttpRequest, HttpResponse
from .models import Match, Prediction, User, TypingGroup, TypingGroupMember
from .forms import RegistrationForm, PredictionForm, TypingGroupForm


@login_required
def match_list_view(request: HttpRequest) -> HttpResponse:
    matches = Match.objects.select_related("league", "home_team", "away_team")
    upcoming = matches.exclude(status=Match.Status.FINISHED).order_by("scheduled_at")
    finished = matches.filter(status=Match.Status.FINISHED)
    return render(request, "typer/match_list.html", {
        "upcoming": upcoming,
        "finished": finished,
    })


def register_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # od razu loguje po rejestracji
            return redirect("typer:home")
    else:
        form = RegistrationForm()

    return render(request, "typer/register.html", {"form": form})


def home_view(request: HttpRequest) -> HttpResponse:
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
def ranking_view(request: HttpRequest) -> HttpResponse:
    users = (
        User.objects.annotate(total_points=Sum("predictions__points__points_awarded"))
        .filter(total_points__isnull=False)
        .order_by("-total_points", "username")
    )
    return render(request, "typer/ranking.html", {"users": users})

@login_required
def group_list_view(request: HttpRequest) -> HttpResponse:
    groups = request.user.typing_groups.all().order_by("name")
    return render(request, "typer/group_list.html", {"groups": groups})

@login_required
def group_create_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = TypingGroupForm(request.POST)
        if form.is_valid():
            group = form.save(commit=False)
            group.owner = request.user
            group.is_private = True
            group.save()
            TypingGroupMember.objects.create(user=request.user, group=group)
            messages.success(request, "Grupa utworzona.")
            return redirect("typer:group_detail", group_id=group.id)
    else:
        form = TypingGroupForm()
    return render(request, "typer/group_form.html", {"form": form})

@login_required
def group_detail_view(request: HttpRequest, group_id: int) -> HttpResponse:
    group = get_object_or_404(TypingGroup, pk=group_id, members=request.user)
    memberships = group.typinggroupmember_set.select_related("user").order_by("joined_at")
    return render(request, "typer/group_detail.html", {"group": group, "memberships": memberships})
