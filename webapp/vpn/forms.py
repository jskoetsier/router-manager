"""
VPN management forms
"""
from django import forms
from django.core.validators import RegexValidator
from .models import VPNTunnel
# Comment out missing imports for now
# from .utils import validate_ip_address, validate_subnet, generate_psk
import re
import secrets
import string
import ipaddress


def validate_subnet(subnet):
    """Validate subnet in CIDR notation"""
    try:
        ipaddress.ip_network(subnet, strict=False)
        return True
    except ValueError:
        return False


def generate_psk(length=32):
    """Generate a random pre-shared key"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class VPNTunnelForm(forms.ModelForm):
    """Form for creating/editing VPN tunnels"""

    # Custom fields for easier input - supporting IPs, hostnames, and IKE IDs
    local_id = forms.CharField(
        label="Local Identity",
        max_length=255,
        help_text="Local identity: IP address, hostname, FQDN, or email (e.g., 192.168.1.1, vpn.local.com, gateway@company.com)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '192.168.1.1 or vpn.local.com'
        })
    )

    remote_id = forms.CharField(
        label="Remote Identity",
        max_length=255,
        help_text="Remote identity: IP address, hostname, FQDN, or email (e.g., 203.0.113.1, remote.company.com, gateway@remote.com)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '203.0.113.1 or remote.company.com'
        })
    )

    local_subnet = forms.CharField(
        label="Local Subnet",
        help_text="Local network in CIDR notation (e.g., 192.168.1.0/24)",
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$',
                message='Enter a valid CIDR notation (e.g., 192.168.1.0/24)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '192.168.1.0/24'
        })
    )

    remote_subnet = forms.CharField(
        label="Remote Subnet",
        help_text="Remote network in CIDR notation (e.g., 10.0.0.0/24)",
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$',
                message='Enter a valid CIDR notation (e.g., 10.0.0.0/24)'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10.0.0.0/24'
        })
    )

    pre_shared_key = forms.CharField(
        label="Pre-Shared Key",
        help_text="Shared secret for authentication (leave blank to auto-generate)",
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter shared secret or leave blank to generate'
        })
    )

    generate_key = forms.BooleanField(
        label="Generate random pre-shared key",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'onchange': 'togglePSKField()'
        })
    )

    class Meta:
        model = VPNTunnel
        fields = [
            'name', 'description', 'tunnel_type',
            'local_id', 'remote_id', 'local_subnet',
            'remote_subnet', 'pre_shared_key', 'auto_start'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter tunnel name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description for this tunnel'
            }),
            'tunnel_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'auto_start': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set field order
        self.fields['name'].help_text = "Unique name for this VPN tunnel"
        self.fields['description'].help_text = "Optional description for documentation"
        self.fields['tunnel_type'].help_text = "Type of VPN connection"
        self.fields['auto_start'].help_text = "Start tunnel automatically on system boot"

    def clean_name(self):
        """Validate tunnel name"""
        name = self.cleaned_data['name']

        # Check for valid characters (alphanumeric, dash, underscore)
        if not name.replace('-', '').replace('_', '').isalnum():
            raise forms.ValidationError(
                "Tunnel name can only contain letters, numbers, hyphens, and underscores"
            )

        # Check if name already exists (excluding current instance)
        qs = VPNTunnel.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError(
                "A tunnel with this name already exists"
            )

        return name

    def clean_local_subnet(self):
        """Validate local subnet"""
        subnet = self.cleaned_data['local_subnet']
        if not validate_subnet(subnet):
            raise forms.ValidationError(
                "Enter a valid subnet in CIDR notation (e.g., 192.168.1.0/24)"
            )
        return subnet

    def clean_remote_subnet(self):
        """Validate remote subnet"""
        subnet = self.cleaned_data['remote_subnet']
        if not validate_subnet(subnet):
            raise forms.ValidationError(
                "Enter a valid subnet in CIDR notation (e.g., 10.0.0.0/24)"
            )
        return subnet

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()

        # Generate PSK if requested
        generate_key = cleaned_data.get('generate_key')
        pre_shared_key = cleaned_data.get('pre_shared_key')

        if generate_key or not pre_shared_key:
            cleaned_data['pre_shared_key'] = generate_psk()

        # Ensure PSK is provided
        if not cleaned_data.get('pre_shared_key'):
            raise forms.ValidationError(
                "Pre-shared key is required. Either enter one or enable auto-generation."
            )

        return cleaned_data


class QuickVPNForm(forms.Form):
    """Simplified form for quick VPN setup"""

    tunnel_name = forms.CharField(
        label="Tunnel Name",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'site-to-branch'
        })
    )

    remote_ip = forms.GenericIPAddressField(
        label="Remote IP Address",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '203.0.113.1'
        })
    )

    remote_subnet = forms.CharField(
        label="Remote Subnet",
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$',
                message='Enter a valid CIDR notation'
            )
        ],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10.0.0.0/24'
        })
    )

    def clean_tunnel_name(self):
        """Validate tunnel name"""
        name = self.cleaned_data['tunnel_name']

        if not name.replace('-', '').replace('_', '').isalnum():
            raise forms.ValidationError(
                "Name can only contain letters, numbers, hyphens, and underscores"
            )

        if VPNTunnel.objects.filter(name=name).exists():
            raise forms.ValidationError(
                "A tunnel with this name already exists"
            )

        return name
