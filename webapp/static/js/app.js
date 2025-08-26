/**
 * Router Manager JavaScript Application
 */

// Global application object
const RouterManager = {
    // Configuration
    config: {
        updateInterval: 30000, // 30 seconds
        chartColors: {
            primary: '#007bff',
            success: '#28a745',
            danger: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8',
            secondary: '#6c757d'
        }
    },

    // Charts storage
    charts: {},

    // Initialize application
    init: function() {
        this.setupEventListeners();
        this.initializeCharts();
        this.startAutoRefresh();
    },

    // Setup event listeners
    setupEventListeners: function() {
        // Handle form submissions with CSRF token
        document.addEventListener('DOMContentLoaded', function() {
            const forms = document.querySelectorAll('form');
            forms.forEach(form => {
                form.addEventListener('submit', RouterManager.handleFormSubmit);
            });
        });

        // Handle modal events
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.addEventListener('shown.bs.modal', function() {
                const firstInput = modal.querySelector('input, select, textarea');
                if (firstInput) firstInput.focus();
            });
        });

        // Handle tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    // Handle form submissions
    handleFormSubmit: function(event) {
        const form = event.target;
        const submitButton = form.querySelector('button[type="submit"]');

        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="loading-spinner"></span> Processing...';

            // Re-enable button after 5 seconds as fallback
            setTimeout(() => {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Submit';
            }, 5000);
        }
    },

    // Initialize charts
    initializeCharts: function() {
        // System metrics chart
        const metricsChart = document.getElementById('systemMetricsChart');
        if (metricsChart) {
            this.createSystemMetricsChart(metricsChart);
        }

        // Network traffic chart
        const trafficChart = document.getElementById('networkTrafficChart');
        if (trafficChart) {
            this.createNetworkTrafficChart(trafficChart);
        }
    },

    // Create system metrics chart
    createSystemMetricsChart: function(canvas) {
        const ctx = canvas.getContext('2d');

        this.charts.systemMetrics = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU %',
                    data: [],
                    borderColor: this.config.chartColors.primary,
                    backgroundColor: this.config.chartColors.primary + '20',
                    fill: false,
                    tension: 0.1
                }, {
                    label: 'Memory %',
                    data: [],
                    borderColor: this.config.chartColors.success,
                    backgroundColor: this.config.chartColors.success + '20',
                    fill: false,
                    tension: 0.1
                }, {
                    label: 'Disk %',
                    data: [],
                    borderColor: this.config.chartColors.warning,
                    backgroundColor: this.config.chartColors.warning + '20',
                    fill: false,
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'System Resource Usage'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    },

    // Create network traffic chart
    createNetworkTrafficChart: function(canvas) {
        const ctx = canvas.getContext('2d');

        this.charts.networkTraffic = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'RX (MB/s)',
                    data: [],
                    backgroundColor: this.config.chartColors.info + '80',
                    borderColor: this.config.chartColors.info,
                    borderWidth: 1
                }, {
                    label: 'TX (MB/s)',
                    data: [],
                    backgroundColor: this.config.chartColors.danger + '80',
                    borderColor: this.config.chartColors.danger,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Network Traffic'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    },

    // Start auto-refresh functionality
    startAutoRefresh: function() {
        // Only refresh on dashboard pages
        if (window.location.pathname.includes('dashboard')) {
            setInterval(() => {
                this.updateSystemStatus();
            }, this.config.updateInterval);
        }
    },

    // Update system status
    updateSystemStatus: function() {
        // Add CSRF token to the request
        const csrfToken = this.utils.getCSRFToken();

        fetch('/dashboard/api/status/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    console.error('Status update error:', data.error);
                    return;
                }

                // Update status cards
                this.updateStatusCards(data);

                // Update charts if they exist
                if (this.charts.systemMetrics) {
                    this.updateSystemMetricsChart(data);
                }
            })
            .catch(error => {
                console.error('Status fetch error:', error);
                // Try to get status from a simpler endpoint
                this.fallbackSystemStatus();
            });
    },

    // Fallback method to get basic system status
    fallbackSystemStatus: function() {
        // Use client-side performance API for basic info
        if (navigator.hardwareConcurrency) {
            const cpuElement = document.getElementById('cpu-usage');
            const memoryElement = document.getElementById('memory-usage');
            const diskElement = document.getElementById('disk-usage');

            if (cpuElement) cpuElement.textContent = 'N/A';
            if (memoryElement) memoryElement.textContent = 'N/A';
            if (diskElement) diskElement.textContent = 'N/A';
        }
    },

    // Update status cards
    updateStatusCards: function(data) {
        const cpuElement = document.getElementById('cpu-usage');
        const memoryElement = document.getElementById('memory-usage');
        const diskElement = document.getElementById('disk-usage');

        if (cpuElement) cpuElement.textContent = data.cpu_usage.toFixed(1) + '%';
        if (memoryElement) memoryElement.textContent = data.memory_usage.toFixed(1) + '%';
        if (diskElement) diskElement.textContent = data.disk_usage.toFixed(1) + '%';
    },

    // Update system metrics chart
    updateSystemMetricsChart: function(data) {
        const chart = this.charts.systemMetrics;
        const now = new Date().toLocaleTimeString();

        // Add new data point
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(data.cpu_usage);
        chart.data.datasets[1].data.push(data.memory_usage);
        chart.data.datasets[2].data.push(data.disk_usage);

        // Keep only last 20 data points
        if (chart.data.labels.length > 20) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(dataset => {
                dataset.data.shift();
            });
        }

        chart.update('none');
    },

    // Utility functions
    utils: {
        // Format bytes to human readable format
        formatBytes: function(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';

            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

            const i = Math.floor(Math.log(bytes) / Math.log(k));

            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        },

        // Format uptime
        formatUptime: function(seconds) {
            const days = Math.floor(seconds / (24 * 60 * 60));
            const hours = Math.floor((seconds % (24 * 60 * 60)) / (60 * 60));
            const minutes = Math.floor((seconds % (60 * 60)) / 60);

            let result = '';
            if (days > 0) result += days + 'd ';
            if (hours > 0) result += hours + 'h ';
            if (minutes > 0) result += minutes + 'm';

            return result || '0m';
        },

        // Show notification
        showNotification: function(message, type = 'info', duration = 3000) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
            alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;

            document.body.appendChild(alertDiv);

            // Auto-dismiss after duration
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, duration);
        },

        // Confirm action
        confirmAction: function(message, callback) {
            if (confirm(message)) {
                callback();
            }
        }
    },

    // API helper functions
    api: {
        // Make authenticated API request
        request: function(url, options = {}) {
            const defaultOptions = {
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': RouterManager.utils.getCSRFToken()
                }
            };

            return fetch(url, { ...defaultOptions, ...options });
        },

        // Get CSRF token
        getCSRFToken: function() {
            const cookieValue = document.cookie
                .split('; ')
                .find(row => row.startsWith('csrftoken='))
                ?.split('=')[1];
            return cookieValue || '';
        }
    }
};

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    RouterManager.init();
});

// Add CSRF token to utility functions
RouterManager.utils.getCSRFToken = function() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
    return cookieValue || '';
};

// Global helper functions for templates
window.refreshPage = function() {
    location.reload();
};

window.showLoading = function(element) {
    if (element) {
        element.innerHTML = '<span class="loading-spinner"></span> Loading...';
        element.disabled = true;
    }
};

window.hideLoading = function(element, originalText = 'Submit') {
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
};

// Export for use in other scripts
window.RouterManager = RouterManager;
