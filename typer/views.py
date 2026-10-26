from collections import defaultdict
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Q, F, Count
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from types import SimpleNamespace
from .constants import (UPCOMING_DAYS, FINISHED_LIMIT, RANKING_PREVIEW, MAX_PREDICTED_GOALS,
                        POINTS_EXACT_SCORE, POINTS_GOAL_DIFFERENCE, POINTS_WINNER)
from .models import League, Match, Points, Prediction, User, TypingGroup, TypingGroupMember, Sport
from .forms import RegistrationForm, TypingGroupForm, JoinGroupForm
from .utils import assign_ranks, attach_predictions, parse_score


def match_list_view(request: HttpRequest) -> HttpResponse:
    now = timezone.now()
    sport_id = request.GET.get("sport", "")
    league_id = request.GET.get("league", "")

    matches = Match.objects.select_related("league", "home_team", "away_team")
    if sport_id.isdigit():
        matches = matches.filter(league__sport_id=sport_id)
    if league_id.isdigit():
        matches = matches.filter(league_id=league_id)

    upcoming = matches.filter(
        status__in=[Match.Status.SCHEDULED, Match.Status.LIVE],
        scheduled_at__gte=now - timedelta(hours=3),
        scheduled_at__lte=now + timedelta(days=UPCOMING_DAYS),
    ).order_by("scheduled_at")

    if request.user.is_authenticated:
        my_league_ids = request.user.typing_groups.values("league_id")
        my_upcoming = attach_predictions(request.user, upcoming.filter(league_id__in=my_league_ids))
        other_upcoming = attach_predictions(request.user, upcoming.exclude(league_id__in=my_league_ids))
    else:
        my_upcoming = []
        other_upcoming = attach_predictions(request.user, upcoming)

    finished = attach_predictions(
        request.user, matches.filter(status=Match.Status.FINISHED).order_by("-scheduled_at")[:FINISHED_LIMIT])
    return render(request, "typer/match_list.html", {
        "my_upcoming": my_upcoming,
        "other_upcoming": other_upcoming,
        "has_open_matches": any(not m.is_locked for m in [*my_upcoming, *other_upcoming]),
        "finished": finished,
        "upcoming_days": UPCOMING_DAYS,
        "finished_limit": FINISHED_LIMIT,
        "sports": Sport.objects.order_by("name"),
        "leagues": League.objects.select_related("sport").order_by("sport__name", "name", "-year"),
        "selected_sport": sport_id,
        "selected_league": league_id,
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


def global_ranking():
    return assign_ranks(
        User.objects.annotate(total_points=Sum("predictions__points__points_awarded"))
        .filter(total_points__isnull=False)
        .order_by("-total_points", "username")
    )


HOME_MATCHES = 6


def home_view(request: HttpRequest) -> HttpResponse:
    now = timezone.now()
    upcoming = (Match.objects.filter(status=Match.Status.SCHEDULED, scheduled_at__gt=now)
                .select_related("league", "home_team", "away_team").order_by("scheduled_at", "id"))
    ranking = global_ranking()
    context = {
        "top_ranking": ranking[:RANKING_PREVIEW],
        "points": {
            "exact": POINTS_EXACT_SCORE, "difference": POINTS_GOAL_DIFFERENCE, "winner": POINTS_WINNER,
        },
    }
    if request.user.is_authenticated:
        my_leagues = list(request.user.typing_groups.values_list("league_id", flat=True))
        if my_leagues:
            upcoming = upcoming.filter(league_id__in=my_leagues)
        todo = upcoming.exclude(predictions__user=request.user)[:HOME_MATCHES]
        mine = next((row for row in ranking if row.id == request.user.id), None)
        context.update({
            "todo": attach_predictions(request.user, todo),
            "my_points": mine.total_points if mine else 0,
            "my_rank": mine.rank if mine else None,
            "ranked_players": len(ranking),
            "predictions_count": request.user.predictions.count(),
        })
    else:
        context["next_matches"] = attach_predictions(request.user, upcoming[:HOME_MATCHES])
    return render(request, "typer/home.html", context)


@login_required
@require_POST
def predict_bulk_view(request: HttpRequest) -> HttpResponse:
    """Zbiorczy zapis typów: pola home_<id_meczu> i away_<id_meczu>.

    Puste pary są pomijane, poprawne zapisywane, a błędne zgłaszane komunikatem."""
    ids = {
        int(key[5:]) for key in request.POST
        if key[:5] in ("home_", "away_") and key[5:].isdigit() and len(key) <= 14
    }
    matches = Match.objects.select_related("home_team", "away_team").in_bulk(ids)
    existing = {
        p.match_id: p for p in Prediction.objects.filter(user=request.user, match_id__in=ids)
    }
    saved = 0
    errors = 0
    for match_id in sorted(ids):
        match = matches.get(match_id)
        raw_home = request.POST.get(f"home_{match_id}", "").strip()
        raw_away = request.POST.get(f"away_{match_id}", "").strip()
        if match is None or (not raw_home and not raw_away):
            continue
        label = f"{match.home_team} – {match.away_team}"
        if match.is_locked:
            messages.error(request, f"{label}: typowanie tego meczu jest już zakończone.")
            errors += 1
            continue
        try:
            home = parse_score(raw_home, MAX_PREDICTED_GOALS)
            away = parse_score(raw_away, MAX_PREDICTED_GOALS)
        except ValueError:
            messages.error(
                request,
                f"{label}: podaj oba wyniki jako liczby od 0 do {MAX_PREDICTED_GOALS}. Typ nie został zapisany.",
            )
            errors += 1
            continue
        prediction = existing.get(match_id)
        if prediction is None:
            Prediction.objects.create(user=request.user, match=match, predicted_home=home, predicted_away=away)
            saved += 1
        elif (prediction.predicted_home, prediction.predicted_away) != (home, away):
            prediction.predicted_home, prediction.predicted_away = home, away
            prediction.save()
            saved += 1
    if saved:
        messages.success(request, f"Zapisano typy: {saved}.")
    elif not errors:
        messages.info(request, "Nie wprowadzono żadnych zmian.")

    target = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                           require_https=request.is_secure()):
        target = "typer:match_list"
    return redirect(target)


def ranking_view(request: HttpRequest) -> HttpResponse:
    users = global_ranking()

    # jedno zapytanie na wszystkie ligi, grupowanie w Pythonie
    rows = (
        Points.objects
        .values(lid=F("prediction__match__league_id"), username=F("prediction__user__username"))
        .annotate(total_points=Sum("points_awarded"))
        .order_by("-total_points", "username")
    )
    by_league = defaultdict(list)
    for r in rows:
        by_league[r["lid"]].append(
            SimpleNamespace(username=r["username"], total_points=r["total_points"])
        )

    league_tables = []
    for league in League.objects.select_related("sport").order_by("sport__name", "name", "-year"):
        ranked = assign_ranks(by_league.get(league.id, []))
        if ranked:
            league_tables.append({"league": league, "rows": ranked[:RANKING_PREVIEW]})

    return render(request, "typer/ranking.html", {"users": users, "league_tables": league_tables})


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
    ranking = assign_ranks(
        group.members
        .annotate(total_points=Sum("predictions__points__points_awarded",
                                   filter=Q(predictions__match__league=group.league),
                                   default=0))
        .order_by("-total_points", "username")
    )
    now = timezone.now()
    upcoming = attach_predictions(request.user, Match.objects.filter(
        league=group.league, status=Match.Status.SCHEDULED,
        scheduled_at__gte=now, scheduled_at__lte=now + timedelta(days=UPCOMING_DAYS),
    ).select_related("league", "home_team", "away_team").order_by("scheduled_at"))
    return render(request, "typer/group_detail.html", {
        "group": group, "ranking": ranking, "is_owner": group.owner_id == request.user.id,
        "upcoming": upcoming, "upcoming_days": UPCOMING_DAYS,
    })


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
    all_matches = Match.objects.filter(league=league)

    # kolejki ligi; "open" = liczba jeszcze niezagranych meczów w kolejce
    rounds = list(
        all_matches.filter(round__isnull=False).values("round")
        .annotate(open=Count("id", filter=Q(status=Match.Status.SCHEDULED)))
        .order_by("round")
    )
    round_numbers = [r["round"] for r in rounds]
    has_unassigned = all_matches.filter(round__isnull=True).exists()

    selected_round = None
    unassigned = False
    if rounds:
        raw = request.GET.get("round", "")
        if raw == "none" and has_unassigned:
            unassigned = True
        elif raw.isdigit() and int(raw) in round_numbers:
            selected_round = int(raw)
        else:  # domyślnie bieżąca kolejka: pierwsza z niezagranymi meczami, a gdy brak, ostatnia
            selected_round = next((r["round"] for r in rounds if r["open"]), round_numbers[-1])
        matches_qs = (all_matches.filter(round=selected_round) if selected_round is not None
                      else all_matches.filter(round__isnull=True))
    else:
        matches_qs = all_matches  # liga bez podziału na kolejki: jedna lista

    matches = attach_predictions(
        request.user,
        matches_qs.select_related("league", "home_team", "away_team").order_by("scheduled_at", "id"),
    )

    prev_round = next_round = None
    if selected_round is not None:
        index = round_numbers.index(selected_round)
        prev_round = round_numbers[index - 1] if index > 0 else None
        next_round = round_numbers[index + 1] if index + 1 < len(round_numbers) else None

    ranking = assign_ranks(
        User.objects.annotate(
            total_points=Sum(
                "predictions__points__points_awarded",
                filter=Q(predictions__match__league=league), ))
        .filter(total_points__isnull=False)
        .order_by("-total_points", "username")
    )
    return render(request, "typer/league_detail.html", {
        "league": league,
        "matches": matches,
        "no_open_matches": all(m.is_locked for m in matches),
        "round_numbers": round_numbers,
        "has_unassigned": has_unassigned,
        "selected_round": selected_round,
        "unassigned": unassigned,
        "prev_round": prev_round,
        "next_round": next_round,
        "ranking": ranking,
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


def match_detail_view(request: HttpRequest, match_id: int) -> HttpResponse:
    match = get_object_or_404(
        Match.objects.select_related("league", "home_team", "away_team"), pk=match_id
    )
    my_prediction = None
    if request.user.is_authenticated:
        my_prediction = (
            Prediction.objects.filter(user=request.user, match=match)
            .select_related("points").first()
        )
    match.my_prediction = my_prediction
    predictions = None
    if match.is_locked:
        predictions = (
            match.predictions.select_related("user", "points")
            .order_by(F("points__points_awarded").desc(nulls_last=True), "user__username")
        )
    return render(request, "typer/match_detail.html", {
        "match": match,
        "my_prediction": my_prediction,
        "editable": [match],
        "predictions": predictions,
    })
