from django import forms
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, HTML, Row, Column
from crispy_forms.bootstrap import AppendedText
from .models import NginxProxyConfig
import json


class NginxProxyConfigForm(forms.ModelForm):
    """Form for creating and editing nginx proxy configurations"""
    
    custom_headers_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Enter custom headers as JSON\ne.g., {"X-Custom-Header": "value", "X-Another-Header": "value2"}'}),
        help_text="Custom headers in JSON format"
    )
    
    class Meta:
        model = NginxProxyConfig
        fields = [
            'name', 'description', 'domain_name', 'ssl_enabled', 'auto_ssl', 'force_https',
            'upstream_host', 'upstream_port', 'upstream_protocol',
            'proxy_read_timeout', 'proxy_connect_timeout', 'proxy_send_timeout',
            'rate_limit_enabled', 'rate_limit_rpm',
            'access_log_enabled', 'error_log_enabled', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g., production-proxy'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional description of this proxy configuration'}),
            'domain_name': forms.TextInput(attrs={'placeholder': 'e.g., example.com'}),
            'upstream_host': forms.TextInput(attrs={'placeholder': '127.0.0.1 or backend-server.local'}),
            'upstream_port': forms.NumberInput(attrs={'min': 1, 'max': 65535}),
            'proxy_read_timeout': forms.NumberInput(attrs={'min': 1, 'max': 3600}),
            'proxy_connect_timeout': forms.NumberInput(attrs={'min': 1, 'max': 3600}),
            'proxy_send_timeout': forms.NumberInput(attrs={'min': 1, 'max': 3600}),
            'rate_limit_rpm': forms.NumberInput(attrs={'min': 1, 'max': 10000}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load custom headers if editing existing config
        if self.instance.pk and self.instance.custom_headers:
            self.fields['custom_headers_text'].initial = json.dumps(self.instance.custom_headers, indent=2)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        
        self.helper.layout = Layout(
            HTML('<h4 class="mb-3"><i class="fas fa-server"></i> Basic Configuration</h4>'),
            Div(
                Row(
                    Column('name', css_class='col-md-6'),
                    Column('is_active', css_class='col-md-6 d-flex align-items-center'),
                ),
                'description',
                css_class='mb-4'
            ),
            
            HTML('<h4 class="mb-3"><i class="fas fa-globe"></i> Domain & SSL Settings</h4>'),
            Div(
                'domain_name',
                Row(
                    Column('ssl_enabled', css_class='col-md-4'),
                    Column('auto_ssl', css_class='col-md-4'),
                    Column('force_https', css_class='col-md-4'),
                ),
                css_class='mb-4'
            ),
            
            HTML('<h4 class="mb-3"><i class="fas fa-arrow-right"></i> Upstream Server</h4>'),
            Div(
                Row(
                    Column('upstream_host', css_class='col-md-6'),
                    Column(AppendedText('upstream_port', 'port'), css_class='col-md-3'),
                    Column('upstream_protocol', css_class='col-md-3'),
                ),
                css_class='mb-4'
            ),
            
            HTML('<h4 class="mb-3"><i class="fas fa-clock"></i> Proxy Timeouts</h4>'),
            Div(
                Row(
                    Column(AppendedText('proxy_read_timeout', 'seconds'), css_class='col-md-4'),
                    Column(AppendedText('proxy_connect_timeout', 'seconds'), css_class='col-md-4'),
                    Column(AppendedText('proxy_send_timeout', 'seconds'), css_class='col-md-4'),
                ),
                css_class='mb-4'
            ),
            
            HTML('<h4 class="mb-3"><i class="fas fa-shield-alt"></i> Security & Rate Limiting</h4>'),
            Div(
                Row(
                    Column('rate_limit_enabled', css_class='col-md-6'),
                    Column(AppendedText('rate_limit_rpm', 'req/min'), css_class='col-md-6'),
                ),
                css_class='mb-4'
            ),
            
            HTML('<h4 class="mb-3"><i class="fas fa-code"></i> Custom Headers</h4>'),
            Div(
                'custom_headers_text',
                css_class='mb-4'
            ),
            
            HTML('<h4 class="mb-3"><i class="fas fa-file-alt"></i> Logging</h4>'),
            Div(
                Row(
                    Column('access_log_enabled', css_class='col-md-6'),
                    Column('error_log_enabled', css_class='col-md-6'),
                ),
                css_class='mb-4'
            ),
            
            Div(
                Submit('save', 'Save Configuration', css_class='btn btn-primary btn-lg me-2'),
                HTML('<a href="{% url \'nginx_mgr:list\' %}" class="btn btn-secondary btn-lg">Cancel</a>'),
                css_class='text-center'
            )
        )
    
    def clean_custom_headers_text(self):
        """Validate and parse custom headers JSON"""
        custom_headers_text = self.cleaned_data.get('custom_headers_text', '').strip()
        
        if not custom_headers_text:
            return {}
        
        try:
            headers = json.loads(custom_headers_text)
            if not isinstance(headers, dict):
                raise ValidationError("Custom headers must be a JSON object (dictionary)")
            
            # Validate header names and values
            for name, value in headers.items():
                if not isinstance(name, str) or not isinstance(value, str):
                    raise ValidationError("Header names and values must be strings")
                if not name.strip():
                    raise ValidationError("Header names cannot be empty")
            
            return headers
        
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON format: {e}")
    
    def save(self, commit=True):
        """Save the form and update custom headers"""
        instance = super().save(commit=False)
        instance.custom_headers = self.cleaned_data.get('custom_headers_text', {})
        
        if commit:
            instance.save()
        
        return instance


class QuickProxyForm(forms.Form):
    """Quick form for creating simple proxy configurations"""
    
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., my-app-proxy'}),
        help_text="A unique name for this proxy configuration"
    )
    domain_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'e.g., myapp.example.com'}),
        help_text="The domain name for your application"
    )
    upstream_port = forms.IntegerField(
        min_value=1,
        max_value=65535,
        initial=8000,
        widget=forms.NumberInput(attrs={'placeholder': '8000'}),
        help_text="The port your application is running on"
    )
    enable_ssl = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Automatically generate SSL certificate via Let's Encrypt"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-3'
        self.helper.field_class = 'col-lg-9'
        
        self.helper.layout = Layout(
            HTML('<div class="alert alert-info"><i class="fas fa-info-circle"></i> Quick setup for a simple reverse proxy with automatic SSL</div>'),
            
            'name',
            'domain_name',
            AppendedText('upstream_port', 'port'),
            'enable_ssl',
            
            Div(
                Submit('create', 'Create Proxy Configuration', css_class='btn btn-success btn-lg me-2'),
                HTML('<a href="{% url \'nginx_mgr:list\' %}" class="btn btn-secondary btn-lg">Cancel</a>'),
                css_class='text-center mt-4'
            )
        )
    
    def create_proxy_config(self):
        """Create a NginxProxyConfig from the form data"""
        if not self.is_valid():
            return None
        
        data = self.cleaned_data
        
        config = NginxProxyConfig(
            name=data['name'],
            description=f"Quick proxy configuration for {data['domain_name']}",
            domain_name=data['domain_name'],
            upstream_host='127.0.0.1',
            upstream_port=data['upstream_port'],
            upstream_protocol='http',
            ssl_enabled=data['enable_ssl'],
            auto_ssl=data['enable_ssl'],
            force_https=data['enable_ssl'],
            is_active=True
        )
        
        return config


class DeployConfigForm(forms.Form):
    """Form for deploying nginx configurations"""
    
    force_reload = forms.BooleanField(
        initial=False,
        required=False,
        help_text="Force reload nginx configuration (use if changes aren't reflecting)"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        self.helper.layout = Layout(
            HTML('<div class="alert alert-warning"><i class="fas fa-exclamation-triangle"></i> This will deploy the configuration to nginx and restart the service if needed.</div>'),
            
            'force_reload',
            
            Div(
                Submit('deploy', 'Deploy Configuration', css_class='btn btn-warning btn-lg me-2'),
                HTML('<button type="button" class="btn btn-secondary btn-lg" data-bs-dismiss="modal">Cancel</button>'),
                css_class='text-center mt-3'
            )
        )