"""
Monitoring forms
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Alert, MonitoringSettings, MetricData, SystemLog


class AlertForm(forms.ModelForm):
    """Form for creating/editing alerts"""

    class Meta:
        model = Alert
        fields = [
            'name', 'alert_type', 'metric_type', 'threshold_value',
            'comparison_operator', 'severity', 'enabled',
            'notification_enabled', 'email_recipients',
            'check_interval', 'source'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter alert name'
            }),
            'alert_type': forms.Select(attrs={'class': 'form-select'}),
            'metric_type': forms.Select(attrs={'class': 'form-select'}),
            'threshold_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'comparison_operator': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notification_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_recipients': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter email addresses (one per line)'
            }),
            'check_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '30'
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional: specific source to monitor'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['email_recipients'].help_text = "Enter email addresses, one per line"
        self.fields['check_interval'].help_text = "Check interval in seconds (minimum 30)"
        self.fields['source'].help_text = "Optional: Leave blank to monitor all sources"
        
        # Set initial values
        if not self.instance.pk:
            self.fields['enabled'].initial = True
            self.fields['notification_enabled'].initial = True
            self.fields['check_interval'].initial = 300

    def clean_email_recipients(self):
        """Validate email recipients"""
        emails_text = self.cleaned_data.get('email_recipients', '')
        if not emails_text:
            return []
        
        emails = []
        for line in emails_text.strip().split('\n'):
            email = line.strip()
            if email:
                # Basic email validation
                if '@' not in email or '.' not in email:
                    raise ValidationError(f"Invalid email address: {email}")
                emails.append(email)
        
        return emails

    def clean_check_interval(self):
        """Validate check interval"""
        interval = self.cleaned_data.get('check_interval')
        if interval and interval < 30:
            raise ValidationError("Check interval must be at least 30 seconds")
        return interval

    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        
        # Validate threshold value based on metric type
        metric_type = cleaned_data.get('metric_type')
        threshold_value = cleaned_data.get('threshold_value')
        
        if metric_type and threshold_value is not None:
            # Validate percentage metrics
            if metric_type in ['cpu', 'memory', 'disk', 'bandwidth_utilization'] and \
               (threshold_value < 0 or threshold_value > 100):
                raise ValidationError({
                    'threshold_value': 'Percentage values must be between 0 and 100'
                })
            
            # Validate temperature metrics
            if metric_type == 'temperature' and threshold_value > 120:
                raise ValidationError({
                    'threshold_value': 'Temperature threshold seems too high (>120°C)'
                })
        
        return cleaned_data


class MonitoringSettingsForm(forms.ModelForm):
    """Form for monitoring settings configuration"""

    class Meta:
        model = MonitoringSettings
        fields = [
            'metric_retention_days', 'log_retention_days', 'collection_interval',
            'email_notifications_enabled', 'smtp_host', 'smtp_port',
            'smtp_username', 'smtp_password', 'smtp_use_tls',
            'default_alert_email', 'temperature_monitoring_enabled',
            'network_monitoring_enabled', 'connection_monitoring_enabled',
            'log_aggregation_enabled'
        ]
        widgets = {
            'metric_retention_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '365'
            }),
            'log_retention_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '90'
            }),
            'collection_interval': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '15',
                'max': '3600'
            }),
            'email_notifications_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'smtp_host': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'smtp.example.com'
            }),
            'smtp_port': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'smtp_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'username@example.com'
            }),
            'smtp_password': forms.PasswordInput(attrs={
                'class': 'form-control'
            }),
            'smtp_use_tls': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'default_alert_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'admin@example.com'
            }),
            'temperature_monitoring_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'network_monitoring_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'connection_monitoring_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'log_aggregation_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['metric_retention_days'].help_text = "Days to keep historical metrics (1-365)"
        self.fields['log_retention_days'].help_text = "Days to keep log entries (1-90)"
        self.fields['collection_interval'].help_text = "Seconds between metric collections (15-3600)"
        self.fields['smtp_password'].help_text = "Leave blank to keep current password"

    def clean_smtp_password(self):
        """Handle password field"""
        password = self.cleaned_data.get('smtp_password')
        
        # If password is empty and we're updating, keep the existing password
        if not password and self.instance.pk:
            return self.instance.smtp_password
        
        return password

    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        
        # If email notifications are enabled, validate SMTP settings
        if cleaned_data.get('email_notifications_enabled'):
            smtp_host = cleaned_data.get('smtp_host')
            smtp_port = cleaned_data.get('smtp_port')
            default_email = cleaned_data.get('default_alert_email')
            
            if not smtp_host:
                raise ValidationError({
                    'smtp_host': 'SMTP host is required when email notifications are enabled'
                })
            
            if not smtp_port:
                raise ValidationError({
                    'smtp_port': 'SMTP port is required when email notifications are enabled'
                })
            
            if not default_email:
                raise ValidationError({
                    'default_alert_email': 'Default alert email is required when notifications are enabled'
                })
        
        return cleaned_data


class MetricFilterForm(forms.Form):
    """Form for filtering metrics in the dashboard"""

    HOURS_CHOICES = [
        ('1', 'Last Hour'),
        ('6', 'Last 6 Hours'),
        ('24', 'Last 24 Hours'),
        ('168', 'Last Week'),
        ('720', 'Last Month'),
    ]

    metric_type = forms.ChoiceField(
        choices=MetricData.METRIC_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    source = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Source (optional)'
        }),
        required=False
    )
    
    hours = forms.ChoiceField(
        choices=HOURS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='24'
    )


class LogFilterForm(forms.Form):
    """Form for filtering system logs"""

    HOURS_CHOICES = [
        ('1', 'Last Hour'),
        ('6', 'Last 6 Hours'),
        ('24', 'Last 24 Hours'),
        ('168', 'Last Week'),
    ]

    source = forms.ChoiceField(
        choices=[('all', 'All Sources')] + list(SystemLog.LOG_SOURCES),
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='all',
        required=False
    )
    
    level = forms.ChoiceField(
        choices=[('all', 'All Levels')] + list(SystemLog.LOG_LEVELS),
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='all',
        required=False
    )
    
    hours = forms.ChoiceField(
        choices=HOURS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='24'
    )
    
    search = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search logs...'
        }),
        required=False
    )


class ConnectionFilterForm(forms.Form):
    """Form for filtering network connections"""

    protocol = forms.ChoiceField(
        choices=[('all', 'All Protocols'), ('tcp', 'TCP'), ('udp', 'UDP')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        initial='all',
        required=False
    )
    
    state = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Connection state (optional)'
        }),
        required=False
    )