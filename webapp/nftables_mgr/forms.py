"""
nftables management forms
"""

from django import forms
from .models import NFTableRule, PortForward


class NFTableRuleForm(forms.ModelForm):
    """Form for creating nftables firewall rules"""

    class Meta:
        model = NFTableRule
        fields = [
            'name', 'description', 'protocol', 'source_ip', 'source_port',
            'destination_ip', 'destination_port', 'action', 'enabled', 'priority'
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rule name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
            'protocol': forms.Select(attrs={'class': 'form-select'}),
            'source_ip': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 192.168.1.0/24 or leave empty for any'
            }),
            'source_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Source port (optional)'
            }),
            'destination_ip': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 192.168.1.100 or leave empty for any'
            }),
            'destination_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Destination port (optional)'
            }),
            'action': forms.Select(attrs={'class': 'form-select'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.NumberInput(attrs={
                'class': 'form-control',
                'value': 100,
                'min': 1,
                'max': 999
            })
        }

    def clean_source_port(self):
        port = self.cleaned_data.get('source_port')
        if port is not None and (port < 1 or port > 65535):
            raise forms.ValidationError("Port must be between 1 and 65535")
        return port

    def clean_destination_port(self):
        port = self.cleaned_data.get('destination_port')
        if port is not None and (port < 1 or port > 65535):
            raise forms.ValidationError("Port must be between 1 and 65535")
        return port

    def clean_source_ip(self):
        ip = self.cleaned_data.get('source_ip')
        if ip:
            from network.utils import validate_ip_address, validate_cidr
            # Check if it's a CIDR notation or single IP
            if '/' in ip:
                if not validate_cidr(ip):
                    raise forms.ValidationError("Invalid IP address or CIDR notation")
            else:
                if not validate_ip_address(ip):
                    raise forms.ValidationError("Invalid IP address")
        return ip

    def clean_destination_ip(self):
        ip = self.cleaned_data.get('destination_ip')
        if ip:
            from network.utils import validate_ip_address, validate_cidr
            # Check if it's a CIDR notation or single IP
            if '/' in ip:
                if not validate_cidr(ip):
                    raise forms.ValidationError("Invalid IP address or CIDR notation")
            else:
                if not validate_ip_address(ip):
                    raise forms.ValidationError("Invalid IP address")
        return ip


class PortForwardForm(forms.ModelForm):
    """Form for creating port forwarding rules"""

    class Meta:
        model = PortForward
        fields = ['name', 'external_port', 'internal_ip', 'internal_port', 'protocol', 'enabled']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Port forward rule name'
            }),
            'external_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'External port (e.g., 80)'
            }),
            'internal_ip': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Internal IP (e.g., 192.168.1.100)'
            }),
            'internal_port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Internal port (e.g., 80)'
            }),
            'protocol': forms.Select(attrs={'class': 'form-select'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean_external_port(self):
        port = self.cleaned_data.get('external_port')
        if port < 1 or port > 65535:
            raise forms.ValidationError("Port must be between 1 and 65535")
        return port

    def clean_internal_port(self):
        port = self.cleaned_data.get('internal_port')
        if port < 1 or port > 65535:
            raise forms.ValidationError("Port must be between 1 and 65535")
        return port

    def clean_internal_ip(self):
        ip = self.cleaned_data.get('internal_ip')
        from network.utils import validate_ip_address
        if not validate_ip_address(ip):
            raise forms.ValidationError("Invalid IP address")
        return ip
