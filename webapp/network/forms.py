"""
Network management forms
"""

from django import forms
from .models import Route, NetworkInterface


class RouteForm(forms.ModelForm):
    """Form for creating/editing static routes"""

    class Meta:
        model = Route
        fields = ['destination', 'gateway', 'interface', 'metric', 'enabled']
        widgets = {
            'destination': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '192.168.1.0/24 or default',
                'help_text': 'Network destination in CIDR notation'
            }),
            'gateway': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '192.168.1.1'
            }),
            'interface': forms.Select(attrs={
                'class': 'form-select'
            }),
            'metric': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': 100,
                'min': 1,
                'max': 999
            }),
            'enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interface'].queryset = NetworkInterface.objects.filter(enabled=True)
        self.fields['interface'].empty_label = "Select interface"

    def clean_destination(self):
        destination = self.cleaned_data.get('destination')
        if destination:
            # Allow 'default' as a special case
            if destination.lower() == 'default':
                return 'default'
            # Validate CIDR format
            try:
                from ipaddress import ip_network
                ip_network(destination, strict=False)
            except ValueError:
                raise forms.ValidationError('Invalid network format. Use CIDR notation (e.g., 192.168.1.0/24)')
        return destination

    def clean_gateway(self):
        gateway = self.cleaned_data.get('gateway')
        if gateway:
            try:
                from ipaddress import ip_address
                ip_address(gateway)
            except ValueError:
                raise forms.ValidationError('Invalid IP address format')
        return gateway
