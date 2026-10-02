from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Sport, Team, League, LeagueMember, Match, Prediction, Points

admin.site.register(User, UserAdmin)
admin.site.register(Sport)
admin.site.register(Team)
admin.site.register(League)
admin.site.register(LeagueMember)
admin.site.register(Match)
admin.site.register(Prediction)
admin.site.register(Points)