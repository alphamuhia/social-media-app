from django.contrib import admin
from .models import Profile, Post, Report, ActivityLog, Block

admin.site.register(Profile)
admin.site.register(Post)
admin.site.register(Report)
admin.site.register(ActivityLog)
admin.site.register(Block)

