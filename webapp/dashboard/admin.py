"""
Django admin configuration for dashboard app
"""

from django.contrib import admin

from .models import Alert, Configuration, SystemStatus, UserActivity


@admin.register(SystemStatus)
class SystemStatusAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "cpu_usage", "memory_usage", "disk_usage"]
    list_filter = ["timestamp"]
    ordering = ["-timestamp"]
    readonly_fields = ["timestamp"]


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ["user", "action", "ip_address", "timestamp", "success"]
    list_filter = ["success", "timestamp", "user"]
    search_fields = ["action", "user__username", "ip_address"]
    ordering = ["-timestamp"]
    readonly_fields = ["timestamp"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["title", "severity", "acknowledged", "timestamp"]
    list_filter = ["severity", "acknowledged", "timestamp"]
    search_fields = ["title", "message"]
    ordering = ["-timestamp"]
    actions = ["mark_acknowledged"]

    def mark_acknowledged(self, request, queryset):
        queryset.update(acknowledged=True, acknowledged_by=request.user)

    mark_acknowledged.short_description = "Mark selected alerts as acknowledged"


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "updated_at", "updated_by"]
    search_fields = ["key", "description"]
    ordering = ["key"]
