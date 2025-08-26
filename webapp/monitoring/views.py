"""
Monitoring views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    """Monitoring home"""
    return render(request, 'monitoring/home.html')


@login_required
def metrics_view(request):
    """System metrics and charts"""
    return render(request, 'monitoring/metrics.html')


@login_required
def alerts_list(request):
    """Monitoring alerts list"""
    return render(request, 'monitoring/alerts_list.html')


@login_required
def services_status(request):
    """System services status"""
    return render(request, 'monitoring/services_status.html')