// Main JavaScript file for the badminton website

// Global variables
let currentUser = null;
let notifications = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    checkUserStatus();
});

function initializeApp() {
    // Add loading states to buttons
    addLoadingStates();
    
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in');
        }, index * 100);
    });
}

function setupEventListeners() {
    // Handle form submissions with loading states
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                addLoadingState(submitBtn);
            }
        });
    });
    
    // Handle click events with ripple effect
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('click', createRipple);
    });
}

function createRipple(event) {
    const button = event.currentTarget;
    const circle = document.createElement('span');
    const diameter = Math.max(button.clientWidth, button.clientHeight);
    const radius = diameter / 2;
    
    circle.style.width = circle.style.height = `${diameter}px`;
    circle.style.left = `${event.clientX - button.offsetLeft - radius}px`;
    circle.style.top = `${event.clientY - button.offsetTop - radius}px`;
    circle.classList.add('ripple');
    
    const ripple = button.getElementsByClassName('ripple')[0];
    if (ripple) {
        ripple.remove();
    }
    
    button.appendChild(circle);
}

function addLoadingState(element) {
    const originalText = element.innerHTML;
    element.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>處理中...';
    element.disabled = true;
    
    // Remove loading state after 5 seconds (fallback)
    setTimeout(() => {
        removeLoadingState(element, originalText);
    }, 5000);
}

function removeLoadingState(element, originalText) {
    element.innerHTML = originalText;
    element.disabled = false;
}

function addLoadingStates() {
    // Add loading states to all buttons
    const style = document.createElement('style');
    style.textContent = `
        .ripple {
            position: absolute;
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 600ms linear;
            background-color: rgba(255, 255, 255, 0.6);
        }
        
        @keyframes ripple {
            to {
                transform: scale(4);
                opacity: 0;
            }
        }
        
        .btn {
            position: relative;
            overflow: hidden;
        }
    `;
    document.head.appendChild(style);
}

function checkUserStatus() {
    // Check if user is banned or has notifications
    // This would typically make an API call
    console.log('Checking user status...');
}

// Utility functions
function formatDateTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return '今天 ' + date.toLocaleTimeString('zh-TW', {hour: '2-digit', minute: '2-digit'});
    } else if (diffDays === 1) {
        return '昨天 ' + date.toLocaleTimeString('zh-TW', {hour: '2-digit', minute: '2-digit'});
    } else if (diffDays < 7) {
        return diffDays + '天前';
    } else {
        return date.toLocaleDateString('zh-TW');
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// API helper functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        showNotification('網路連線發生錯誤，請稍後再試', 'danger');
        throw error;
    }
}

// Team-related functions
function validateTeamForm(formData) {
    const errors = [];
    
    if (!formData.name || formData.name.trim().length < 2) {
        errors.push('隊伍名稱至少需要2個字元');
    }
    
    if (!formData.location_city) {
        errors.push('請選擇縣市');
    }
    
    if (!formData.location_venue || formData.location_venue.trim().length < 2) {
        errors.push('請輸入球場名稱');
    }
    
    if (!formData.start_time) {
        errors.push('請選擇開始時間');
    }
    
    if (!formData.end_time) {
        errors.push('請選擇結束時間');
    }
    
    if (formData.start_time && formData.end_time) {
        const startTime = new Date(formData.start_time);
        const endTime = new Date(formData.end_time);
        
        if (endTime <= startTime) {
            errors.push('結束時間必須晚於開始時間');
        }
        
        if (startTime <= new Date()) {
            errors.push('開始時間必須是未來時間');
        }
    }
    
    return errors;
}

// Message handling
function sanitizeMessage(message) {
    const div = document.createElement('div');
    div.textContent = message;
    return div.innerHTML;
}

function formatMessage(message) {
    // Handle @mentions
    return message.replace(/@(\w+)/g, '<span class="text-primary fw-bold">@$1</span>');
}

// Local storage helpers
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
}

function loadFromLocalStorage(key) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : null;
    } catch (error) {
        console.error('Failed to load from localStorage:', error);
        return null;
    }
}

// Form validation helpers
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePhone(phone) {
    const re = /^[\d\-\+\(\)\s]+$/;
    return re.test(phone) && phone.replace(/\D/g, '').length >= 10;
}

// Image handling
function previewImage(input, previewElement) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            previewElement.src = e.target.result;
            previewElement.style.display = 'block';
        };
        
        reader.readAsDataURL(input.files[0]);
    }
}

function validateImageFile(file) {
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif'];
    const maxSize = 5 * 1024 * 1024; // 5MB
    
    if (!allowedTypes.includes(file.type)) {
        return '請選擇 JPG、PNG 或 GIF 格式的圖片';
    }
    
    if (file.size > maxSize) {
        return '圖片大小不能超過 5MB';
    }
    
    return null;
}

// Geolocation helpers
function getCurrentLocation() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('瀏覽器不支援定位功能'));
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            position => {
                resolve({
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude
                });
            },
            error => {
                reject(new Error('無法取得位置資訊'));
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 300000
            }
        );
    });
}

// Export functions for use in other scripts
window.BadmintonApp = {
    formatDateTime,
    showNotification,
    confirmAction,
    apiCall,
    validateTeamForm,
    sanitizeMessage,
    formatMessage,
    saveToLocalStorage,
    loadFromLocalStorage,
    validateEmail,
    validatePhone,
    previewImage,
    validateImageFile,
    getCurrentLocation
};
