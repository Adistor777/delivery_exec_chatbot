// Delivery Executive Chatbot Frontend
class DeliveryChatbot {
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.token = localStorage.getItem('delivery_token');
        this.user = JSON.parse(localStorage.getItem('delivery_user') || '{}');
        
        this.initializeElements();
        this.attachEventListeners();
        this.initialize();
    }

    initializeElements() {
        // Screens
        this.loadingScreen = document.getElementById('loading-screen');
        this.loginScreen = document.getElementById('login-screen');
        this.chatInterface = document.getElementById('chat-interface');
        
        // Login elements
        this.usernameInput = document.getElementById('username');
        this.passwordInput = document.getElementById('password');
        this.loginBtn = document.getElementById('login-btn');
        this.loginError = document.getElementById('login-error');
        
        // Chat elements
        this.chatMessages = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.suggestionsContainer = document.getElementById('suggestions-container');
        this.suggestions = document.getElementById('suggestions');
        
        // Header elements
        this.userName = document.getElementById('user-name');
        this.userStatus = document.getElementById('user-status');
        this.activeDeliveriesCount = document.getElementById('active-deliveries-count');
        this.deliveriesBtn = document.getElementById('deliveries-btn');
        this.profileBtn = document.getElementById('profile-btn');
        this.logoutBtn = document.getElementById('logout-btn');
        
        // Modals
        this.deliveriesModal = document.getElementById('deliveries-modal');
        this.profileModal = document.getElementById('profile-modal');
        this.deliveriesList = document.getElementById('deliveries-list');
        this.profileContent = document.getElementById('profile-content');
        
        // Quick actions
        this.quickActionBtns = document.querySelectorAll('.quick-action-btn');
    }

    attachEventListeners() {
        // Login
        this.loginBtn.addEventListener('click', () => this.login());
        this.passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.login();
        });

        // Chat
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Quick actions
        this.quickActionBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.dataset.message;
                this.sendQuickMessage(message);
            });
        });

        // Header buttons
        this.deliveriesBtn.addEventListener('click', () => this.showDeliveries());
        this.profileBtn.addEventListener('click', () => this.showProfile());
        this.logoutBtn.addEventListener('click', () => this.logout());

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.target.closest('.modal').classList.add('hidden');
            });
        });

        // Close modals on backdrop click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.add('hidden');
                }
            });
        });
    }

    async initialize() {
        // Show loading screen
        setTimeout(() => {
            this.loadingScreen.classList.add('hidden');
            
            if (this.token && this.user.username) {
                this.showChatInterface();
                this.loadUserDashboard();
            } else {
                this.loginScreen.classList.remove('hidden');
            }
        }, 2000);
    }

    async login() {
        const username = this.usernameInput.value.trim();
        const password = this.passwordInput.value.trim();

        if (!username || !password) {
            this.showError('Please enter both username and password');
            return;
        }

        this.loginBtn.disabled = true;
        this.loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing In...';

        try {
            const response = await fetch(`${this.apiBase}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (response.ok) {
                this.token = data.access_token;
                this.user = {
                    id: data.user_id,
                    username: data.username
                };

                localStorage.setItem('delivery_token', this.token);
                localStorage.setItem('delivery_user', JSON.stringify(this.user));

                this.loginScreen.classList.add('hidden');
                this.showChatInterface();
                this.loadUserDashboard();
            } else {
                this.showError(data.detail || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('Network error. Please check your connection.');
        } finally {
            this.loginBtn.disabled = false;
            this.loginBtn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Sign In';
        }
    }

    showError(message) {
        this.loginError.textContent = message;
        this.loginError.classList.remove('hidden');
        setTimeout(() => {
            this.loginError.classList.add('hidden');
        }, 5000);
    }

    showChatInterface() {
        this.chatInterface.classList.remove('hidden');
        this.userName.textContent = this.user.username || 'User';
        this.messageInput.focus();
    }

    async loadUserDashboard() {
        try {
            // Load user profile
            const profileResponse = await this.apiCall('/api/user/profile');
            if (profileResponse.ok) {
                const profile = await profileResponse.json();
                this.userName.textContent = profile.full_name || profile.username;
            }

            // Load active deliveries count
            const deliveriesResponse = await this.apiCall('/api/deliveries?limit=50');
            if (deliveriesResponse.ok) {
                const deliveries = await deliveriesResponse.json();
                const activeCount = deliveries.filter(d => 
                    ['assigned', 'picked_up', 'in_transit'].includes(d.status)
                ).length;
                this.activeDeliveriesCount.textContent = activeCount;
            }

            // Load dashboard summary
            const dashboardResponse = await this.apiCall('/api/dashboard/summary');
            if (dashboardResponse.ok) {
                const dashboard = await dashboardResponse.json();
                this.activeDeliveriesCount.textContent = dashboard.active_deliveries || 0;
            }
        } catch (error) {
            console.error('Dashboard load error:', error);
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        this.addMessage(message, 'user');
        this.messageInput.value = '';
        this.sendBtn.disabled = true;
        this.showTyping();

        try {
            const response = await this.apiCall('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    context: {}
                }),
            });

            if (response.ok) {
                const data = await response.json();
                this.addMessage(data.response, 'bot');
                
                if (data.suggestions && data.suggestions.length > 0) {
                    this.showSuggestions(data.suggestions);
                }
            } else {
                const errorData = await response.json();
                this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
                console.error('Chat error:', errorData);
            }
        } catch (error) {
            console.error('Send message error:', error);
            this.addMessage('Network error. Please check your connection and try again.', 'bot');
        } finally {
            this.hideTyping();
            this.sendBtn.disabled = false;
        }
    }

    sendQuickMessage(message) {
        this.messageInput.value = message;
        this.sendMessage();
    }

    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = sender === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';

        const content = document.createElement('div');
        content.className = 'message-content';

        const messageText = document.createElement('div');
        messageText.className = 'message-text';
        messageText.innerHTML = text.replace(/\n/g, '<br>');

        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.textContent = new Date().toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        content.appendChild(messageText);
        content.appendChild(messageTime);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);

        this.chatMessages.appendChild(messageDiv);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showSuggestions(suggestions) {
        this.suggestions.innerHTML = '';
        suggestions.forEach(suggestion => {
            const btn = document.createElement('button');
            btn.className = 'suggestion-btn';
            btn.textContent = suggestion;
            btn.addEventListener('click', () => {
                this.sendQuickMessage(suggestion);
                this.hideSuggestions();
            });
            this.suggestions.appendChild(btn);
        });
        this.suggestionsContainer.classList.remove('hidden');
    }

    hideSuggestions() {
        this.suggestionsContainer.classList.add('hidden');
    }

    showTyping() {
        this.typingIndicator.classList.remove('hidden');
    }

    hideTyping() {
        this.typingIndicator.classList.add('hidden');
    }

    async showDeliveries() {
        this.deliveriesModal.classList.remove('hidden');
        this.deliveriesList.innerHTML = '<div class="loading">Loading deliveries...</div>';

        try {
            const response = await this.apiCall('/api/deliveries?limit=20');
            if (response.ok) {
                const deliveries = await response.json();
                this.renderDeliveries(deliveries);
            } else {
                this.deliveriesList.innerHTML = '<div class="loading">Failed to load deliveries</div>';
            }
        } catch (error) {
            console.error('Load deliveries error:', error);
            this.deliveriesList.innerHTML = '<div class="loading">Network error</div>';
        }
    }

    renderDeliveries(deliveries) {
        if (deliveries.length === 0) {
            this.deliveriesList.innerHTML = '<div class="loading">No deliveries found</div>';
            return;
        }

        this.deliveriesList.innerHTML = '';
        deliveries.forEach(delivery => {
            const deliveryDiv = document.createElement('div');
            deliveryDiv.className = `delivery-item ${delivery.status}`;
            
            deliveryDiv.innerHTML = `
                <div class="delivery-header">
                    <span class="delivery-id">#${delivery.order_id}</span>
                    <span class="delivery-status status-${delivery.status}">${delivery.status}</span>
                </div>
                <div class="delivery-details">
                    <strong>Customer:</strong> ${delivery.customer_name || 'N/A'}<br>
                    <strong>Address:</strong> ${delivery.delivery_address || 'N/A'}<br>
                    <strong>Priority:</strong> ${delivery.priority}<br>
                    ${delivery.special_instructions ? `<strong>Instructions:</strong> ${delivery.special_instructions}<br>` : ''}
                    ${delivery.cod_amount > 0 ? `<strong>COD Amount:</strong> ${delivery.cod_amount}<br>` : ''}
                    <strong>Created:</strong> ${new Date(delivery.created_at).toLocaleString()}
                </div>
            `;
            
            this.deliveriesList.appendChild(deliveryDiv);
        });
    }

    async showProfile() {
        this.profileModal.classList.remove('hidden');
        this.profileContent.innerHTML = '<div class="loading">Loading profile...</div>';

        try {
            const [profileResponse, preferencesResponse] = await Promise.all([
                this.apiCall('/api/user/profile'),
                this.apiCall('/api/user/preferences')
            ]);

            const profile = profileResponse.ok ? await profileResponse.json() : null;
            const preferences = preferencesResponse.ok ? await preferencesResponse.json() : null;

            this.renderProfile(profile, preferences);
        } catch (error) {
            console.error('Load profile error:', error);
            this.profileContent.innerHTML = '<div class="loading">Failed to load profile</div>';
        }
    }

    renderProfile(profile, preferences) {
        if (!profile) {
            this.profileContent.innerHTML = '<div class="loading">Failed to load profile</div>';
            return;
        }

        this.profileContent.innerHTML = `
            <div class="profile-section">
                <h3><i class="fas fa-user"></i> Personal Information</h3>
                <div class="profile-info">
                    <div class="info-item">
                        <div class="info-label">Full Name</div>
                        <div class="info-value">${profile.full_name || 'N/A'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Username</div>
                        <div class="info-value">${profile.username}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Email</div>
                        <div class="info-value">${profile.email}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Phone</div>
                        <div class="info-value">${profile.phone || 'N/A'}</div>
                    </div>
                </div>
            </div>
            
            <div class="profile-section">
                <h3><i class="fas fa-truck"></i> Work Information</h3>
                <div class="profile-info">
                    <div class="info-item">
                        <div class="info-label">Employee ID</div>
                        <div class="info-value">${profile.employee_id || 'N/A'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Vehicle Type</div>
                        <div class="info-value">${profile.vehicle_type || 'N/A'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Status</div>
                        <div class="info-value">${profile.status}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Joined</div>
                        <div class="info-value">${new Date(profile.created_at).toLocaleDateString()}</div>
                    </div>
                </div>
            </div>
            
            ${preferences ? `
            <div class="profile-section">
                <h3><i class="fas fa-cog"></i> Preferences</h3>
                <div class="profile-info">
                    <div class="info-item">
                        <div class="info-label">Language</div>
                        <div class="info-value">${preferences.preferred_language}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Voice Enabled</div>
                        <div class="info-value">${preferences.voice_enabled ? 'Yes' : 'No'}</div>
                    </div>
                </div>
            </div>
            ` : ''}
        `;
    }

    async apiCall(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Authorization': `Bearer ${this.token}`,
                'Content-Type': 'application/json',
            },
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers,
            },
        };

        return fetch(`${this.apiBase}${endpoint}`, mergedOptions);
    }

    logout() {
        localStorage.removeItem('delivery_token');
        localStorage.removeItem('delivery_user');
        
        this.token = null;
        this.user = {};
        
        this.chatInterface.classList.add('hidden');
        this.loginScreen.classList.remove('hidden');
        
        // Clear chat messages
        this.chatMessages.innerHTML = `
            <div class="message bot-message">
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">
                        👋 Hello! I'm your delivery assistant. I can help you with:
                        <br>• Package handling procedures
                        <br>• Customer communication
                        <br>• Route optimization
                        <br>• Emergency protocols
                        <br>• Technical support
                        <br><br>What can I help you with today?
                    </div>
                    <div class="message-time">Just now</div>
                </div>
            </div>
        `;
        
        // Reset form
        this.usernameInput.value = 'demo_user';
        this.passwordInput.value = 'demo123';
    }
}

// Initialize the chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DeliveryChatbot();
});