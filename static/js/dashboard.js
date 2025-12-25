// Dashboard JavaScript
class DevilCloudDashboard {
    constructor() {
        this.initializeEventListeners();
        this.startAutoRefresh();
    }
    
    initializeEventListeners() {
        // Bot action confirmations
        document.querySelectorAll('a[href*="/delete/"]').forEach(link => {
            link.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to delete this bot?')) {
                    e.preventDefault();
                }
            });
        });
        
        // Start/Stop buttons with loading states
        document.querySelectorAll('a[href*="/start/"], a[href*="/stop/"]').forEach(btn => {
            btn.addEventListener('click', function(e) {
                const originalHTML = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                this.disabled = true;
                
                // Re-enable after 5 seconds even if page doesn't reload
                setTimeout(() => {
                    this.innerHTML = originalHTML;
                    this.disabled = false;
                }, 5000);
            });
        });
        
        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', this.toggleTheme.bind(this));
        }
        
        // File upload preview
        const fileInput = document.getElementById('bot_file');
        if (fileInput) {
            fileInput.addEventListener('change', this.updateFilePreview.bind(this));
        }
    }
    
    toggleTheme() {
        const html = document.documentElement;
        const currentTheme = html.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        html.setAttribute('data-theme', newTheme);
        localStorage.setItem('devilcloud-theme', newTheme);
        
        // Update button icon
        const icon = document.querySelector('#theme-toggle i');
        if (icon) {
            icon.className = newTheme === 'dark' ? 'fas fa-moon' : 'fas fa-sun';
        }
    }
    
    updateFilePreview(event) {
        const input = event.target;
        const preview = document.getElementById('file-preview');
        const fileName = document.getElementById('file-name');
        
        if (input.files && input.files[0]) {
            const file = input.files[0];
            
            if (fileName) {
                fileName.textContent = `${file.name} (${this.formatBytes(file.size)})`;
            }
            
            // Auto-detect language
            const ext = file.name.split('.').pop().toLowerCase();
            const langSelect = document.getElementById('bot_language');
            
            if (langSelect) {
                if (ext === 'py') langSelect.value = 'python';
                else if (ext === 'php') langSelect.value = 'php';
                else if (ext === 'js') langSelect.value = 'node';
                else if (ext === 'sh') langSelect.value = 'bash';
            }
        }
    }
    
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
    
    startAutoRefresh() {
        // Auto-refresh stats every 30 seconds
        if (window.location.pathname === '/dashboard' || window.location.pathname === '/admin') {
            setInterval(() => {
                this.refreshStats();
            }, 30000);
        }
    }
    
    async refreshStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();
            
            // Update running bots count
            const runningEl = document.querySelector('.stat-value:first-child');
            if (runningEl && data.running_bots !== undefined) {
                runningEl.textContent = data.running_bots;
            }
            
            // Update system stats if available
            if (data.system) {
                this.updateSystemStats(data.system);
            }
        } catch (error) {
            console.error('Error refreshing stats:', error);
        }
    }
    
    updateSystemStats(system) {
        // Update CPU usage
        const cpuEl = document.querySelector('.progress-bar.cpu');
        if (cpuEl) {
            cpuEl.style.width = system.cpu + '%';
            cpuEl.textContent = system.cpu.toFixed(1) + '%';
        }
        
        // Update memory usage
        const memoryEl = document.querySelector('.progress-bar.memory');
        if (memoryEl) {
            memoryEl.style.width = system.memory_percent + '%';
        }
    }
    
    // Toast notifications
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${this.getToastIcon(type)}"></i>
                <span>${message}</span>
            </div>
            <button class="toast-close">&times;</button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
        
        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.remove();
        });
    }
    
    getToastIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new DevilCloudDashboard();
    
    // Load saved theme
    const savedTheme = localStorage.getItem('devilcloud-theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    }
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(el => {
        el.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.textContent = this.getAttribute('data-tooltip');
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.top = (rect.top - tooltip.offsetHeight - 10) + 'px';
            tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
            
            this._tooltip = tooltip;
        });
        
        el.addEventListener('mouseleave', function() {
            if (this._tooltip) {
                this._tooltip.remove();
            }
        });
    });
});

// Real-time logs updates
function startLogsStream(botId) {
    if (typeof EventSource !== 'undefined') {
        const eventSource = new EventSource(`/api/logs/stream/${botId}`);
        
        eventSource.onmessage = function(event) {
            const logsContainer = document.getElementById('logs-container');
            if (logsContainer) {
                logsContainer.innerHTML += event.data + '\n';
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        };
        
        eventSource.onerror = function() {
            console.error('EventSource failed.');
            eventSource.close();
        };
        
        return eventSource;
    }
    return null;
}

// File upload with progress
function uploadFileWithProgress(formId, progressCallback) {
    const form = document.getElementById(formId);
    const fileInput = form.querySelector('input[type="file"]');
    
    if (!fileInput || !fileInput.files.length) {
        return Promise.reject('No file selected');
    }
    
    const formData = new FormData(form);
    
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                if (progressCallback) {
                    progressCallback(percentComplete);
                }
            }
        });
        
        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                resolve(xhr.responseText);
            } else {
                reject('Upload failed: ' + xhr.statusText);
            }
        });
        
        xhr.addEventListener('error', function() {
            reject('Network error');
        });
        
        xhr.open('POST', form.action);
        xhr.send(formData);
    });
    }
