from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Sport, Team, League, Group, GroupMember, Match, Prediction, Points

admin.site.register(User, UserAdmin)
admin.site.register(Sport)
admin.site.register(Team)
admin.site.register(League)
admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(Match)
admin.site.register(Prediction)
admin.site.register(Points)