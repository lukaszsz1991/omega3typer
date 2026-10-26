from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Sport, Team, League, TypingGroup, TypingGroupMember, Match, Prediction, Points


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "match")
    list_filter = ("match__league",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Points)
class PointsAdmin(admin.ModelAdmin):
    list_display = ("prediction", "points_awarded")
    list_filter = ("prediction__match__league",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "sport")
    list_filter = ("sport",)
    search_fields = ("name",)


class TypingGroupMemberInline(admin.TabularInline):
    model = TypingGroupMember
    extra = 1


class TypingGroupAdmin(admin.ModelAdmin):
    inlines = [TypingGroupMemberInline]


admin.site.register(User, UserAdmin)
admin.site.register(Sport)
admin.site.register(TypingGroup, TypingGroupAdmin)
admin.site.register(TypingGroupMember)


@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ("name", "year", "sport", "end_date")
    list_filter = ("sport", "year")
    search_fields = ("name",)


class RoundListFilter(admin.SimpleListFilter):
    """Filtr kolejki. Po wybraniu ligi pokazuje tylko jej kolejki, inaczej wszystkie."""
    title = "kolejka"
    parameter_name = "round"

    def lookups(self, request, model_admin):
        matches = Match.objects.filter(round__isnull=False)
        league_id = request.GET.get("league__id__exact", "")
        if league_id.isdigit():
            matches = matches.filter(league_id=league_id)
        rounds = matches.order_by("round").values_list("round", flat=True).distinct()
        return [(number, f"Kolejka {number}") for number in rounds]

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None and value.isdigit():
            return queryset.filter(round=int(value))
        return queryset


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("scheduled_at", "league", "round", "home_team", "away_team", "score", "status")
    list_display_links = ("home_team", "away_team")
    list_filter = ("league", RoundListFilter, "status", "league__sport")
    search_fields = ("home_team__name", "away_team__name")
    date_hierarchy = "scheduled_at"
    ordering = ("-scheduled_at",)
    list_select_related = ("league", "home_team", "away_team")
    list_per_page = 50
    autocomplete_fields = ("home_team", "away_team")

    @admin.display(description="Wynik")
    def score(self, obj):
        if obj.home_score is None or obj.away_score is None:
            return "–"
        return f"{obj.home_score}:{obj.away_score}"
