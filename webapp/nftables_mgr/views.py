"""
nftables management views
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .forms import NFTableRuleForm, PortForwardForm
from .models import NFTableRule, PortForward
from network.utils import get_nftables_rules, parse_nftables_rules, create_nftables_rule, create_port_forward_rule


@login_required
def home(request):
    """nftables management home"""
    return render(request, "nftables/home.html")


@login_required
def rules_list(request):
    """List firewall rules"""
    # Get current nftables rules from system
    nftables_info = get_nftables_rules()

    # Get parsed rules for better display
    parsed_rules = parse_nftables_rules()

    # Get saved rules from database
    saved_rules = NFTableRule.objects.filter(enabled=True).order_by('priority', 'name')

    context = {
        'nftables_info': nftables_info,
        'parsed_rules': parsed_rules.get('rules', []),
        'saved_rules': saved_rules,
    }
    return render(request, "nftables/rules_list.html", context)


@login_required
def add_rule(request):
    """Add new firewall rule"""
    if request.method == 'POST':
        form = NFTableRuleForm(request.POST)
        if form.is_valid():
            # Save to database
            rule = form.save(commit=False)
            rule.created_by = request.user
            rule.save()

            # Apply to nftables if enabled
            if rule.enabled:
                rule_data = {
                    'name': rule.name,
                    'protocol': rule.protocol,
                    'source_ip': rule.source_ip,
                    'source_port': rule.source_port,
                    'destination_ip': rule.destination_ip,
                    'destination_port': rule.destination_port,
                    'action': rule.action,
                }

                result = create_nftables_rule(rule_data)
                if result.get('success'):
                    messages.success(request, f'Firewall rule "{rule.name}" created successfully!')
                else:
                    messages.error(request, f'Rule saved but failed to apply to nftables: {result.get("error", "Unknown error")}')
            else:
                messages.success(request, f'Firewall rule "{rule.name}" saved (disabled)!')

            return redirect('nftables:rules_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = NFTableRuleForm()

    context = {'form': form}
    return render(request, "nftables/add_rule.html", context)


@login_required
def port_forward_list(request):
    """List port forwarding rules"""
    # Get saved port forward rules
    port_forwards = PortForward.objects.filter(enabled=True).order_by('external_port')

    context = {
        'port_forwards': port_forwards,
    }
    return render(request, "nftables/port_forward_list.html", context)


@login_required
def add_port_forward(request):
    """Add new port forwarding rule"""
    if request.method == 'POST':
        form = PortForwardForm(request.POST)
        if form.is_valid():
            # Save to database
            port_forward = form.save(commit=False)
            port_forward.created_by = request.user
            port_forward.save()

            # Apply to nftables if enabled
            if port_forward.enabled:
                port_forward_data = {
                    'name': port_forward.name,
                    'external_port': port_forward.external_port,
                    'internal_ip': port_forward.internal_ip,
                    'internal_port': port_forward.internal_port,
                    'protocol': port_forward.protocol,
                }

                result = create_port_forward_rule(port_forward_data)
                if result.get('success'):
                    messages.success(request, f'Port forward rule "{port_forward.name}" created successfully!')
                else:
                    messages.error(request, f'Rule saved but failed to apply to nftables: {result.get("error", "Unknown error")}')
            else:
                messages.success(request, f'Port forward rule "{port_forward.name}" saved (disabled)!')

            return redirect('nftables:port_forward_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PortForwardForm()

    context = {'form': form}
    return render(request, "nftables/add_port_forward.html", context)
