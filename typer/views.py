from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q, F
from django.http import HttpRequest, HttpResponse
from django.views.decorators.http import require_POST
from .models import League, Match, Prediction, User, TypingGroup, TypingGroupMember
from .forms import RegistrationForm, PredictionForm, TypingGroupForm, JoinGroupForm


@login_required
def match_list_view(request: HttpRequest) -> HttpResponse:
    matches = Match.objects.select_related("league", "home_team", "away_team")
    upcoming = matches.exclude(status=Match.Status.FINISHED).order_by("scheduled_at")
    finished = matches.filter(status=Match.Status.FINISHED).order_by("-scheduled_at")
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
def predict_view(request: HttpRequest, match_id) -> HttpResponse:
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
def group_list_view(request):
    groups = request.user.typing_groups.select_related("league")
    active = [g for g in groups if g.is_active]
    archived = [g for g in groups if not g.is_active]
    return render(request, "typer/group_list.html", {"active": active, "archived": archived})


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
    if not group.is_active:
        messages.error(request, "Sezon tej ligi już się zakończył.")
        return redirect("typer:group_list")
    ranking = (group.members
               .annotate(total_points=Sum("predictions__points__points_awarded",
                                          filter=Q(predictions__match__league=group.league),
                                          default=0))
               .order_by("-total_points", "username"))
    return render(request, "typer/group_detail.html", {"group": group, "ranking": ranking, "is_owner": group.owner_id == request.user.id})


@login_required
def group_join_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = JoinGroupForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            group = TypingGroup.objects.filter(invite_code=code).first()
            if group is None:
                form.add_error("code", "Nieprawidłowy kod zaproszenia.")
            elif not group.is_active:
                messages.error(request, "Nie można dołączyć do grupy, której sezon rozgrywkowy się zakończył.")
                return redirect("typer:group_list")
            else:
                _, created = TypingGroupMember.objects.get_or_create(
                    user=request.user, group=group
                )
                if created:
                    messages.success(request, f"Dołączyłeś do grupy {group.name}.")
                else:
                    messages.info(request, "Już należysz do tej grupy.")
                return redirect("typer:group_detail", group_id=group.id)
    else:
        form = JoinGroupForm()
    return render(request, "typer/group_join.html", {"form": form})


def league_list_view(request: HttpRequest) -> HttpResponse:
    leagues = League.objects.all().select_related("sport").order_by("sport__name", "name")
    return render(request, "typer/league_list.html", {"leagues": leagues})


def league_detail_view(request: HttpRequest, league_id: int) -> HttpResponse:
    league = get_object_or_404(League.objects.select_related("sport"), pk=league_id)
    matches = Match.objects.filter(league=league).select_related("home_team", "away_team")
    upcoming = matches.filter(status=Match.Status.SCHEDULED).order_by("scheduled_at")
    finished = matches.filter(status=Match.Status.FINISHED).order_by("-scheduled_at")[:10]
    return render(request, "typer/league_detail.html", {
        "league": league,
        "upcoming": upcoming,
        "finished": finished,
    })

@login_required
@require_POST
def group_remove_member_view(request, group_id, user_id):
    group = get_object_or_404(TypingGroup, pk=group_id, owner=request.user)
    if user_id == request.user.id:
        messages.error(request, "Właściciel nie może usunąć samego siebie.")
    else:
        deleted, _ = TypingGroupMember.objects.filter(group=group, user_id=user_id).delete()
        if deleted:
            messages.success(request, "Usunięto członka grupy.")
    return redirect("typer:group_detail", group_id=group.id)


@login_required
@require_POST
def group_regenerate_code_view(request, group_id):
    group = get_object_or_404(TypingGroup, pk=group_id, owner=request.user, is_private=True)
    group.regenerate_invite_code()
    messages.success(request, "Wygenerowano nowy kod zaproszenia. Stary kod już nie działa.")
    return redirect("typer:group_detail", group_id=group.id)


@login_required
@require_POST
def group_leave_view(request, group_id):
    group = get_object_or_404(TypingGroup, pk=group_id, members=request.user)
    if group.owner_id == request.user.id:
        messages.error(request, "Właściciel nie może opuścić grupy.")
        return redirect("typer:group_detail", group_id=group.id)
    TypingGroupMember.objects.filter(group=group, user=request.user).delete()
    messages.success(request, f"Opuściłeś grupę „{group.name}”.")
    return redirect("typer:group_list")

@login_required
def match_detail_view(request: HttpRequest, match_id: int) -> HttpResponse:
    match = get_object_or_404(
        Match.objects.select_related("league", "home_team", "away_team"), pk=match_id
    )
    my_prediction = (
        Prediction.objects.filter(user=request.user, match=match)
        .select_related("points").first()
    )
    predictions = None
    if match.is_locked:
        predictions = (
            match.predictions.select_related("user", "points")
            .order_by(F("points__points_awarded").desc(nulls_last=True), "user__username")
        )
    return render(request, "typer/match_detail.html", {
        "match": match,
        "my_prediction": my_prediction,
        "predictions": predictions,
    })
