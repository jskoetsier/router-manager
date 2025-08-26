"""
Dashboard views for Router Manager
"""

import json
import subprocess
from datetime import datetime, timedelta

import psutil
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Alert, Configuration, SystemStatus, UserActivity
from .utils import get_network_interfaces, get_system_info, log_user_activity


@login_required
def dashboard_home(request):
    """Main dashboard view"""
    # Get latest system status
    try:
        latest_status = SystemStatus.objects.latest()
    except SystemStatus.DoesNotExist:
        latest_status = None

    # Get system information
    system_info = get_system_info()

    # Get network interfaces
    network_interfaces = get_network_interfaces()

    # Get recent alerts
    recent_alerts = Alert.objects.filter(acknowledged=False)[:5]

    # Get recent user activity
    recent_activity = UserActivity.objects.all()[:10]

    context = {
        "system_status": latest_status,
        "system_info": system_info,
        "network_interfaces": network_interfaces,
        "recent_alerts": recent_alerts,
        "recent_activity": recent_activity,
    }

    return render(request, "dashboard/home.html", context)


@login_required
def system_status_api(request):
    """API endpoint for real-time system status"""
    try:
        # Get current system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        # Get network statistics
        network_io = psutil.net_io_counters()

        # Save to database
        status = SystemStatus.objects.create(
            cpu_usage=cpu_percent,
            memory_usage=memory.percent,
            disk_usage=(disk.used / disk.total) * 100,
            network_rx=network_io.bytes_recv,
            network_tx=network_io.bytes_sent,
        )

        data = {
            "cpu_usage": status.cpu_usage,
            "memory_usage": status.memory_usage,
            "disk_usage": status.disk_usage,
            "network_rx": status.network_rx,
            "network_tx": status.network_tx,
            "timestamp": status.timestamp.isoformat(),
        }

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def alerts_view(request):
    """Alerts management view"""
    alerts_list = Alert.objects.all()

    # Filter by severity if specified
    severity_filter = request.GET.get("severity")
    if severity_filter:
        alerts_list = alerts_list.filter(severity=severity_filter)

    # Filter by acknowledgment status
    ack_filter = request.GET.get("acknowledged")
    if ack_filter == "true":
        alerts_list = alerts_list.filter(acknowledged=True)
    elif ack_filter == "false":
        alerts_list = alerts_list.filter(acknowledged=False)

    # Pagination
    paginator = Paginator(alerts_list, 20)
    page_number = request.GET.get("page")
    alerts = paginator.get_page(page_number)

    context = {
        "alerts": alerts,
        "severity_filter": severity_filter,
        "ack_filter": ack_filter,
    }

    return render(request, "dashboard/alerts.html", context)


@login_required
def acknowledge_alert(request, alert_id):
    """Acknowledge an alert"""
    try:
        alert = Alert.objects.get(id=alert_id)
        alert.acknowledged = True
        alert.acknowledged_by = request.user
        alert.acknowledged_at = timezone.now()
        alert.save()

        log_user_activity(
            request.user,
            f"Acknowledged alert: {alert.title}",
            request.META.get("REMOTE_ADDR", ""),
            True,
        )

        messages.success(request, "Alert acknowledged successfully.")
    except Alert.DoesNotExist:
        messages.error(request, "Alert not found.")

    return redirect("dashboard:alerts")


@login_required
def activity_log(request):
    """User activity log view"""
    activities = UserActivity.objects.all()

    # Filter by user if specified
    user_filter = request.GET.get("user")
    if user_filter:
        activities = activities.filter(user__username__icontains=user_filter)

    # Filter by action if specified
    action_filter = request.GET.get("action")
    if action_filter:
        activities = activities.filter(action__icontains=action_filter)

    # Filter by date range
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    if date_from:
        activities = activities.filter(timestamp__gte=date_from)
    if date_to:
        activities = activities.filter(timestamp__lte=date_to)

    # Pagination
    paginator = Paginator(activities, 25)
    page_number = request.GET.get("page")
    activities_page = paginator.get_page(page_number)

    context = {
        "activities": activities_page,
        "user_filter": user_filter,
        "action_filter": action_filter,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "dashboard/activity_log.html", context)


@login_required
def system_info_view(request):
    """System information view"""
    system_info = get_system_info()

    # Get historical data for charts
    end_date = timezone.now()
    start_date = end_date - timedelta(hours=24)

    historical_data = SystemStatus.objects.filter(
        timestamp__range=[start_date, end_date]
    ).order_by("timestamp")

    # Prepare chart data
    chart_data = {
        "labels": [status.timestamp.strftime("%H:%M") for status in historical_data],
        "cpu_data": [status.cpu_usage for status in historical_data],
        "memory_data": [status.memory_usage for status in historical_data],
        "disk_data": [status.disk_usage for status in historical_data],
    }

    context = {
        "system_info": system_info,
        "chart_data": json.dumps(chart_data),
    }

    return render(request, "dashboard/system_info.html", context)


@login_required
def settings_view(request):
    """System settings view"""
    if request.method == "POST":
        # Handle settings update
        for key, value in request.POST.items():
            if key.startswith("config_"):
                config_key = key.replace("config_", "")
                config, created = Configuration.objects.get_or_create(
                    key=config_key,
                    defaults={"value": value, "updated_by": request.user},
                )
                if not created:
                    config.value = value
                    config.updated_by = request.user
                    config.save()

        log_user_activity(
            request.user,
            "Updated system settings",
            request.META.get("REMOTE_ADDR", ""),
            True,
        )

        messages.success(request, "Settings updated successfully.")
        return redirect("dashboard:settings")

    # Get all configurations
    configurations = Configuration.objects.all()

    context = {
        "configurations": configurations,
    }

    return render(request, "dashboard/settings.html", context)


class CustomLoginView(auth_views.LoginView):
    """Custom login view with activity logging"""

    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)

        log_user_activity(
            self.request.user,
            "User login",
            self.request.META.get("REMOTE_ADDR", ""),
            True,
        )

        return response

    def form_invalid(self, form):
        response = super().form_invalid(form)

        # Log failed login attempt
        username = form.cleaned_data.get("username", "Unknown")
        try:
            from django.contrib.auth.models import User

            user = User.objects.get(username=username)
            log_user_activity(
                user,
                "Failed login attempt",
                self.request.META.get("REMOTE_ADDR", ""),
                False,
            )
        except User.DoesNotExist:
            pass

        return response


class CustomLogoutView(auth_views.LogoutView):
    """Custom logout view with activity logging"""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            log_user_activity(
                request.user, "User logout", request.META.get("REMOTE_ADDR", ""), True
            )

        return super().dispatch(request, *args, **kwargs)
