from django.contrib import admin

from .models import Task


@admin.register(Task)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_at")
    search_fields = ("title", "statement")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
