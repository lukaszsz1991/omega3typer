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
admin.site.register(League)
admin.site.register(TypingGroup, TypingGroupAdmin)
admin.site.register(TypingGroupMember)
admin.site.register(Match)
