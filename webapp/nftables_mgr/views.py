"""
nftables management views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def home(request):
    """nftables management home"""
    return render(request, 'nftables/home.html')


@login_required
def rules_list(request):
    """List firewall rules"""
    return render(request, 'nftables/rules_list.html')


@login_required
def add_rule(request):
    """Add new firewall rule"""
    return render(request, 'nftables/add_rule.html')


@login_required
def port_forward_list(request):
    """List port forwarding rules"""
    return render(request, 'nftables/port_forward_list.html')


@login_required
def add_port_forward(request):
    """Add new port forwarding rule"""
    return render(request, 'nftables/add_port_forward.html')