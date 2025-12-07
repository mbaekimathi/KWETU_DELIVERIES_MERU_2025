/**
 * Main JavaScript file for Kwetu Deliveries
 * Handles sidebar toggle, cart updates, and general interactivity
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile menu toggle
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const sidebarClose = document.getElementById('sidebar-close');
    
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            sidebar.classList.remove('-translate-x-full');
            sidebarOverlay.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        });
    }
    
    if (sidebarClose) {
        sidebarClose.addEventListener('click', closeSidebar);
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }
    
    function closeSidebar() {
        sidebar.classList.add('-translate-x-full');
        sidebarOverlay.classList.add('hidden');
        document.body.style.overflow = '';
    }
    
    // Login Modal Functionality
    initLoginModal();
    
    // Sign-Up Modals Functionality
    initSignUpModals();
    
    // Update cart count on page load
    updateCartCount();
    
    // Close sidebar when clicking on a link (mobile)
    const sidebarLinks = sidebar.querySelectorAll('a');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            setTimeout(closeSidebar, 100);
        });
    });
});

/**
 * Initialize Login Modal
 */
function initLoginModal() {
    const modal = document.getElementById('login-modal');
    const modalToggle = document.getElementById('login-modal-toggle');
    const modalClose = document.getElementById('login-modal-close');
    const modalOverlay = document.getElementById('login-modal-overlay');
    const employeeBtn = document.getElementById('employee-login-btn');
    const shopBtn = document.getElementById('shop-login-btn');
    const employeeForm = document.getElementById('employee-login-form');
    const shopForm = document.getElementById('shop-login-form');
    
    // Open modal
    if (modalToggle) {
        modalToggle.addEventListener('click', function() {
            openLoginModal();
        });
    }
    
    // Close modal
    if (modalClose) {
        modalClose.addEventListener('click', closeLoginModal);
    }
    
    if (modalOverlay) {
        modalOverlay.addEventListener('click', closeLoginModal);
    }
    
    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeLoginModal();
        }
    });
    
    // Switch between Employee and Shop login
    if (employeeBtn) {
        employeeBtn.addEventListener('click', function() {
            switchLoginType('employee');
        });
    }
    
    if (shopBtn) {
        shopBtn.addEventListener('click', function() {
            switchLoginType('shop');
        });
    }
    
    // Password toggle functionality
    document.querySelectorAll('.toggle-password').forEach(btn => {
        btn.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const eyeIcon = this.querySelector('.eye-icon');
            const eyeOffIcon = this.querySelector('.eye-off-icon');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeIcon.classList.add('hidden');
                eyeOffIcon.classList.remove('hidden');
            } else {
                passwordInput.type = 'password';
                eyeIcon.classList.remove('hidden');
                eyeOffIcon.classList.add('hidden');
            }
        });
    });
    
    // Input validation - Only allow numbers for codes
    const employeeCodeInput = document.getElementById('employee-code');
    const shopCodeInput = document.getElementById('shop-code');
    
    if (employeeCodeInput) {
        employeeCodeInput.addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }
    
    if (shopCodeInput) {
        shopCodeInput.addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }
    
    // Form submission
    if (employeeForm) {
        employeeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleLogin('employee', {
                code: employeeCodeInput.value,
                password: document.getElementById('employee-password').value
            });
        });
    }
    
    if (shopForm) {
        shopForm.addEventListener('submit', function(e) {
            e.preventDefault();
            handleLogin('shop', {
                code: shopCodeInput.value,
                password: document.getElementById('shop-password').value
            });
        });
    }
}

function openLoginModal() {
    const modal = document.getElementById('login-modal');
    const overlay = document.getElementById('login-modal-overlay');
    const modalContent = modal?.querySelector('.relative');
    
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Reset to employee login by default
        switchLoginType('employee');
        
        // Animate overlay and modal content
        setTimeout(() => {
            if (overlay) {
                overlay.classList.remove('bg-opacity-0');
                overlay.classList.add('bg-opacity-70');
            }
            if (modalContent) {
                modalContent.classList.remove('scale-95', 'opacity-0');
                modalContent.classList.add('scale-100', 'opacity-100');
            }
        }, 10);
    }
}

function closeLoginModal() {
    const modal = document.getElementById('login-modal');
    const overlay = document.getElementById('login-modal-overlay');
    const modalContent = modal?.querySelector('.relative');
    
    if (modal) {
        // Animate out
        if (overlay) {
            overlay.classList.remove('bg-opacity-70');
            overlay.classList.add('bg-opacity-0');
        }
        if (modalContent) {
            modalContent.classList.remove('scale-100', 'opacity-100');
            modalContent.classList.add('scale-95', 'opacity-0');
        }
        
        // Hide modal after animation
        setTimeout(() => {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
            // Clear forms
            document.getElementById('employee-login-form')?.reset();
            document.getElementById('shop-login-form')?.reset();
        }, 300);
    }
}

function switchLoginType(type) {
    const employeeBtn = document.getElementById('employee-login-btn');
    const shopBtn = document.getElementById('shop-login-btn');
    const employeeForm = document.getElementById('employee-login-form');
    const shopForm = document.getElementById('shop-login-form');
    
    if (type === 'employee') {
        employeeBtn?.classList.add('active', 'bg-kwetu-orange', 'text-white');
        employeeBtn?.classList.remove('bg-white', 'text-gray-700');
        shopBtn?.classList.remove('active', 'bg-kwetu-orange', 'text-white');
        shopBtn?.classList.add('bg-white', 'text-gray-700');
        employeeForm?.classList.remove('hidden');
        shopForm?.classList.add('hidden');
    } else {
        shopBtn?.classList.add('active', 'bg-kwetu-orange', 'text-white');
        shopBtn?.classList.remove('bg-white', 'text-gray-700');
        employeeBtn?.classList.remove('active', 'bg-kwetu-orange', 'text-white');
        employeeBtn?.classList.add('bg-white', 'text-gray-700');
        shopForm?.classList.remove('hidden');
        employeeForm?.classList.add('hidden');
    }
}

function handleLogin(type, data) {
    console.log(`${type} login attempt:`, data);
    
    // Validate input
    if (!data.code || !data.password) {
        showNotification('Please enter both code and password', 'error');
        return;
    }
    
    // Show loading state
    const submitBtn = type === 'employee' 
        ? document.querySelector('#employee-login-form button[type="submit"]')
        : document.querySelector('#shop-login-form button[type="submit"]');
    
    const originalText = submitBtn ? submitBtn.textContent : '';
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging in...';
    }
    
    // Make API call
    const endpoint = type === 'employee' ? '/api/login/employee' : '/api/login/shop';
    
    fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
        
        if (result.success) {
            showNotification(result.message || 'Login successful!', 'success');
            closeLoginModal();
            
            // Redirect to role-specific page
            if (result.redirect_url) {
                setTimeout(() => {
                    window.location.href = result.redirect_url;
                }, 1000);
            } else {
                // Default redirect if no specific URL provided
                window.location.href = type === 'employee' ? '/dashboard/employee' : '/dashboard/shop';
            }
        } else {
            showNotification(result.message || 'Login failed', 'error');
        }
    })
    .catch(error => {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
        console.error('Login error:', error);
        showNotification('Network error. Please try again.', 'error');
    });
}

/**
 * Update cart count in header
 */
function updateCartCount() {
    const cartCountEl = document.getElementById('cart-count');
    if (!cartCountEl) return;
    
    fetch('/api/cart')
        .then(response => response.json())
        .then(data => {
            const count = data.cart ? data.cart.length : 0;
            cartCountEl.textContent = count;
            if (count === 0) {
                cartCountEl.style.display = 'none';
            } else {
                cartCountEl.style.display = 'flex';
            }
        })
        .catch(error => {
            console.error('Error fetching cart:', error);
        });
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500'
    };
    
    notification.className = `fixed top-20 right-4 px-6 py-3 rounded-lg shadow-lg z-50 ${colors[type] || colors.info} text-white transform transition-all duration-300`;
    notification.textContent = message;
    notification.style.transform = 'translateX(400px)';
    
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(400px)';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    return `KES ${parseFloat(amount).toFixed(2)}`;
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Initialize Sign-Up Modals
 */
function initSignUpModals() {
    // Employee Sign-Up Modal
    const employeeSignupModal = document.getElementById('employee-signup-modal');
    const employeeSignupToggle = document.getElementById('open-employee-signup');
    const employeeSignupClose = document.getElementById('employee-signup-close');
    const employeeSignupOverlay = document.getElementById('employee-signup-overlay');
    const employeeSignupForm = document.getElementById('employee-signup-form');
    const employeeCodeInput = employeeSignupForm?.querySelector('input[name="login_code"]');
    
    // Shop Sign-Up Modal
    const shopSignupModal = document.getElementById('shop-signup-modal');
    const shopSignupToggle = document.getElementById('open-shop-signup');
    const shopSignupClose = document.getElementById('shop-signup-close');
    const shopSignupOverlay = document.getElementById('shop-signup-overlay');
    const shopSignupForm = document.getElementById('shop-signup-form');
    const shopCodeInput = shopSignupForm?.querySelector('input[name="login_code"]');
    const getLocationBtn = document.getElementById('get-current-location');
    
    // Open Employee Sign-Up
    if (employeeSignupToggle) {
        employeeSignupToggle.addEventListener('click', function(e) {
            e.preventDefault();
            closeLoginModal();
            setTimeout(() => openEmployeeSignupModal(), 300);
        });
    }
    
    // Open Shop Sign-Up
    if (shopSignupToggle) {
        shopSignupToggle.addEventListener('click', function(e) {
            e.preventDefault();
            closeLoginModal();
            setTimeout(() => openShopSignupModal(), 300);
        });
    }
    
    // Close Employee Sign-Up
    if (employeeSignupClose) {
        employeeSignupClose.addEventListener('click', closeEmployeeSignupModal);
    }
    if (employeeSignupOverlay) {
        employeeSignupOverlay.addEventListener('click', closeEmployeeSignupModal);
    }
    
    // Close Shop Sign-Up
    if (shopSignupClose) {
        shopSignupClose.addEventListener('click', closeShopSignupModal);
    }
    if (shopSignupOverlay) {
        shopSignupOverlay.addEventListener('click', closeShopSignupModal);
    }
    
    // Code availability check - Employee
    if (employeeCodeInput) {
        employeeCodeInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value.length === 4) {
                checkCodeAvailability(this.value, 'employee');
            } else {
                document.getElementById('employee-code-status').textContent = '';
            }
        });
    }
    
    // Code availability check - Shop
    if (shopCodeInput) {
        shopCodeInput.addEventListener('input', function() {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value.length === 6) {
                checkCodeAvailability(this.value, 'shop');
            } else {
                document.getElementById('shop-code-status').textContent = '';
            }
        });
    }
    
    // Get current location - Use event delegation to handle dynamically loaded modals
    // Also attach directly if button exists
    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', getCurrentLocation);
        console.log('Location button event listener attached on init');
    } else {
        console.warn('Location button not found during initialization - will attach when modal opens');
    }
    
    // Also use event delegation as fallback
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'get-current-location') {
            e.preventDefault();
            getCurrentLocation();
        }
    });
    
    // File upload previews
    setupFilePreview('employee-profile-picture', 'employee-profile-preview', 'Profile Picture');
    setupFilePreview('employee-id-front', 'employee-id-front-preview', 'ID Front');
    setupFilePreview('employee-id-back', 'employee-id-back-preview', 'ID Back');
    setupFilePreview('shop-profile-image', 'shop-profile-preview', 'Shop Profile');
    setupFilePreview('shop-business-document', 'shop-document-preview', 'Business Document');
    
    // Form submissions
    if (employeeSignupForm) {
        employeeSignupForm.addEventListener('submit', handleEmployeeSignup);
    }
    
    if (shopSignupForm) {
        shopSignupForm.addEventListener('submit', handleShopSignup);
    }
    
    // Uppercase inputs (except email)
    document.querySelectorAll('input[type="text"]').forEach(input => {
        if (input.name !== 'email' && input.type === 'text') {
            input.addEventListener('input', function() {
                if (this.name !== 'email' && this.name !== 'location_name') {
                    this.value = this.value.toUpperCase();
                }
            });
        }
    });
}

function openEmployeeSignupModal() {
    const modal = document.getElementById('employee-signup-modal');
    const overlay = document.getElementById('employee-signup-overlay');
    const modalContent = modal?.querySelector('.relative');
    
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        setTimeout(() => {
            if (overlay) {
                overlay.classList.remove('bg-opacity-0');
                overlay.classList.add('bg-opacity-70');
            }
            if (modalContent) {
                modalContent.classList.remove('scale-95', 'opacity-0');
                modalContent.classList.add('scale-100', 'opacity-100');
            }
        }, 10);
    }
}

function closeEmployeeSignupModal() {
    const modal = document.getElementById('employee-signup-modal');
    const overlay = document.getElementById('employee-signup-overlay');
    const modalContent = modal?.querySelector('.relative');
    
    if (modal) {
        if (overlay) {
            overlay.classList.remove('bg-opacity-70');
            overlay.classList.add('bg-opacity-0');
        }
        if (modalContent) {
            modalContent.classList.remove('scale-100', 'opacity-100');
            modalContent.classList.add('scale-95', 'opacity-0');
        }
        
        setTimeout(() => {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
            document.getElementById('employee-signup-form')?.reset();
            document.getElementById('employee-code-status').textContent = '';
        }, 300);
    }
}

function openShopSignupModal() {
    const modal = document.getElementById('shop-signup-modal');
    const overlay = document.getElementById('shop-signup-overlay');
    const modalContent = modal?.querySelector('.relative');
    
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        
        // Ensure event listener is attached when modal opens
        const getLocationBtn = document.getElementById('get-current-location');
        if (getLocationBtn) {
            // Remove any existing listeners to avoid duplicates
            const newBtn = getLocationBtn.cloneNode(true);
            getLocationBtn.parentNode.replaceChild(newBtn, getLocationBtn);
            // Attach event listener to the new button
            document.getElementById('get-current-location').addEventListener('click', getCurrentLocation);
            console.log('Location button event listener attached');
        } else {
            console.warn('Location button not found when opening modal');
        }
        
        setTimeout(() => {
            if (overlay) {
                overlay.classList.remove('bg-opacity-0');
                overlay.classList.add('bg-opacity-70');
            }
            if (modalContent) {
                modalContent.classList.remove('scale-95', 'opacity-0');
                modalContent.classList.add('scale-100', 'opacity-100');
            }
        }, 10);
    }
}

function closeShopSignupModal() {
    const modal = document.getElementById('shop-signup-modal');
    const overlay = document.getElementById('shop-signup-overlay');
    const modalContent = modal?.querySelector('.relative');
    
    if (modal) {
        if (overlay) {
            overlay.classList.remove('bg-opacity-70');
            overlay.classList.add('bg-opacity-0');
        }
        if (modalContent) {
            modalContent.classList.remove('scale-100', 'opacity-100');
            modalContent.classList.add('scale-95', 'opacity-0');
        }
        
        setTimeout(() => {
            modal.classList.add('hidden');
            document.body.style.overflow = '';
            document.getElementById('shop-signup-form')?.reset();
            document.getElementById('shop-code-status').textContent = '';
        }, 300);
    }
}

function checkCodeAvailability(code, type) {
    const statusEl = document.getElementById(`${type}-code-status`);
    if (!statusEl) {
        console.error(`Status element not found for type: ${type}`);
        return;
    }
    
    // Validate code before sending
    if (!code || code.length === 0) {
        statusEl.textContent = '';
        statusEl.className = '';
        return;
    }
    
    // Validate code length
    if (type === 'employee' && code.length !== 4) {
        return; // Wait for full 4 digits
    }
    if (type === 'shop' && code.length !== 6) {
        return; // Wait for full 6 digits
    }
    
    statusEl.textContent = 'Checking...';
    statusEl.className = 'code-status checking';
    
    console.log(`Checking code availability: code=${code}, type=${type}`);
    
    fetch('/api/check-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code, type: type })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.message || 'Failed to check code');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log(`Code check response:`, data);
        if (data.available) {
            statusEl.textContent = '✓ Code available';
            statusEl.className = 'code-status available';
        } else {
            statusEl.textContent = '✗ Code already taken';
            statusEl.className = 'code-status taken';
        }
    })
    .catch(error => {
        console.error('Error checking code:', error);
        statusEl.textContent = 'Error checking code';
        statusEl.className = 'code-status taken';
    });
}

// Make function globally accessible
window.getCurrentLocation = function getCurrentLocation() {
    console.log('getCurrentLocation function called');
    const locationNameInput = document.getElementById('location-name');
    const longitudeInput = document.getElementById('longitude');
    const latitudeInput = document.getElementById('latitude');
    const btn = document.getElementById('get-current-location');
    const GOOGLE_API_KEY = 'AIzaSyD8-l6NrR0CbJvADIXdM7KSGOjGvFWjbT0';
    
    console.log('Elements found:', {
        locationNameInput: !!locationNameInput,
        longitudeInput: !!longitudeInput,
        latitudeInput: !!latitudeInput,
        btn: !!btn
    });
    
    // Check if elements exist
    if (!locationNameInput || !longitudeInput || !latitudeInput) {
        console.error('Location input elements not found', {
            locationNameInput: locationNameInput,
            longitudeInput: longitudeInput,
            latitudeInput: latitudeInput
        });
        if (typeof showNotification === 'function') {
            showNotification('Location form elements not found. Please refresh the page.', 'error');
        } else {
            alert('Location form elements not found. Please refresh the page.');
        }
        return;
    }
    
    if (!btn) {
        console.error('Get location button not found');
        return;
    }
    
    if (!navigator.geolocation) {
        console.error('Geolocation not supported');
        if (typeof showNotification === 'function') {
            showNotification('Geolocation is not supported by your browser', 'error');
        } else {
            alert('Geolocation is not supported by your browser');
        }
        return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Getting location...';
    console.log('Requesting geolocation...');
    
    navigator.geolocation.getCurrentPosition(
        function(position) {
            console.log('Geolocation success:', position);
            const lat = position.coords.latitude;
            const lng = position.coords.longitude;
            
            console.log('Coordinates:', { lat, lng });
            
            // Set coordinates immediately
            if (latitudeInput) {
                latitudeInput.value = lat;
                // Trigger input event to ensure form validation sees the value
                latitudeInput.dispatchEvent(new Event('input', { bubbles: true }));
                latitudeInput.dispatchEvent(new Event('change', { bubbles: true }));
                console.log('Latitude set:', latitudeInput.value);
                console.log('Latitude input element after setting:', latitudeInput);
            } else {
                console.error('latitudeInput is null');
            }
            if (longitudeInput) {
                longitudeInput.value = lng;
                // Trigger input event to ensure form validation sees the value
                longitudeInput.dispatchEvent(new Event('input', { bubbles: true }));
                longitudeInput.dispatchEvent(new Event('change', { bubbles: true }));
                console.log('Longitude set:', longitudeInput.value);
                console.log('Longitude input element after setting:', longitudeInput);
            } else {
                console.error('longitudeInput is null');
            }
            
            // Visual verification - highlight the inputs to show they were updated
            if (latitudeInput) {
                latitudeInput.style.borderColor = '#10b981';
                setTimeout(() => {
                    if (latitudeInput) latitudeInput.style.borderColor = '';
                }, 2000);
            }
            if (longitudeInput) {
                longitudeInput.style.borderColor = '#10b981';
                setTimeout(() => {
                    if (longitudeInput) longitudeInput.style.borderColor = '';
                }, 2000);
            }
            
            // Use Google Geocoding API to get location name
            const geocodeUrl = `https://maps.googleapis.com/maps/api/geocode/json?latlng=${lat},${lng}&key=${GOOGLE_API_KEY}`;
            console.log('Fetching geocode from:', geocodeUrl);
            
            fetch(geocodeUrl)
                .then(response => {
                    console.log('Geocode response status:', response.status, response.statusText);
                    console.log('Geocode response headers:', response.headers);
                    if (!response.ok) {
                        console.error('Geocode HTTP error:', response.status, response.statusText);
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Geocode API full response:', JSON.stringify(data, null, 2));
                    console.log('Geocode API status:', data.status);
                    console.log('Geocode API results count:', data.results ? data.results.length : 0);
                    
                    if (data.status === 'OK' && data.results && data.results.length > 0) {
                        // Get the formatted address from the first result
                        const formattedAddress = data.results[0].formatted_address;
                        console.log('Formatted address found:', formattedAddress);
                        
                        if (locationNameInput) {
                            locationNameInput.value = formattedAddress;
                            // Trigger input event to ensure form validation sees the value
                            locationNameInput.dispatchEvent(new Event('input', { bubbles: true }));
                            locationNameInput.dispatchEvent(new Event('change', { bubbles: true }));
                            console.log('Location name input value set to:', locationNameInput.value);
                            console.log('Location name input element:', locationNameInput);
                            
                            // Visual verification - highlight the input to show it was updated
                            locationNameInput.style.borderColor = '#10b981';
                            setTimeout(() => {
                                if (locationNameInput) locationNameInput.style.borderColor = '';
                            }, 2000);
                        } else {
                            console.error('locationNameInput is null after geocoding success');
                        }
                        
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = '📍 Use Current Location';
                        }
                        if (typeof showNotification === 'function') {
                            showNotification('Location retrieved successfully!', 'success');
                        } else {
                            alert('Location retrieved successfully!');
                        }
                    } else if (data.status === 'REQUEST_DENIED') {
                        console.error('Geocoding API REQUEST_DENIED:', data.error_message || 'API key may be invalid or restricted');
                        const fallbackName = `Location at ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                        if (locationNameInput) {
                            locationNameInput.value = fallbackName;
                            locationNameInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = '📍 Use Current Location';
                        }
                        const errorMsg = `Geocoding API access denied. Coordinates saved. Please enter location name manually. Error: ${data.error_message || 'Check API key permissions'}`;
                        if (typeof showNotification === 'function') {
                            showNotification(errorMsg, 'error');
                        } else {
                            alert(errorMsg);
                        }
                    } else {
                        console.warn('Geocoding API returned non-OK status:', data.status, data);
                        // Fallback if geocoding fails
                        const fallbackName = `Location at ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                        if (locationNameInput) {
                            locationNameInput.value = fallbackName;
                            locationNameInput.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                        if (btn) {
                            btn.disabled = false;
                            btn.textContent = '📍 Use Current Location';
                        }
                        let warningMsg = 'Location coordinates retrieved. Please enter location name manually.';
                        if (data.error_message) {
                            warningMsg += ` (${data.error_message})`;
                        }
                        if (data.status) {
                            warningMsg += ` [Status: ${data.status}]`;
                        }
                        console.warn('Warning message:', warningMsg);
                        if (typeof showNotification === 'function') {
                            showNotification(warningMsg, 'warning');
                        } else {
                            alert(warningMsg);
                        }
                    }
                })
                .catch(error => {
                    console.error('Geocoding error:', error);
                    // Fallback if API call fails
                    const fallbackName = `Location at ${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                    if (locationNameInput) {
                        locationNameInput.value = fallbackName;
                    }
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = '📍 Use Current Location';
                    }
                    const errorMsg = `Location coordinates retrieved. Geocoding failed: ${error.message}. Please enter location name manually.`;
                    if (typeof showNotification === 'function') {
                        showNotification(errorMsg, 'warning');
                    } else {
                        alert(errorMsg);
                    }
                });
        },
        function(error) {
            console.error('Geolocation error:', error);
            if (btn) {
                btn.disabled = false;
                btn.textContent = '📍 Use Current Location';
            }
            
            let errorMessage = 'Unable to retrieve location. Please enter manually.';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage = 'Location access denied. Please enable location permissions in your browser settings.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage = 'Location information unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage = 'Location request timed out. Please try again.';
                    break;
            }
            if (typeof showNotification === 'function') {
                showNotification(errorMessage, 'error');
            } else {
                alert(errorMessage);
            }
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
};

function handleEmployeeSignup(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Ensure terms checkbox value is set correctly
    const termsCheckbox = form.querySelector('#employee-terms');
    if (termsCheckbox && termsCheckbox.checked) {
        formData.set('terms_accepted', 'true');
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';
    
    fetch('/api/signup/employee', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.message || 'Registration failed');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            setTimeout(() => {
                closeEmployeeSignupModal();
            }, 2000);
        } else {
            showNotification(data.message || 'Registration failed. Please check all fields.', 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Registration';
        }
    })
    .catch(error => {
        console.error('Signup error:', error);
        showNotification(error.message || 'An error occurred. Please try again.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Registration';
    });
}

function handleShopSignup(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    
    // Ensure terms checkbox value is set correctly
    const termsCheckbox = form.querySelector('#shop-terms');
    if (termsCheckbox && termsCheckbox.checked) {
        formData.set('terms_accepted', 'true');
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting...';
    
    fetch('/api/signup/shop', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.message || 'Registration failed');
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showNotification(data.message, 'success');
            setTimeout(() => {
                closeShopSignupModal();
            }, 2000);
        } else {
            showNotification(data.message || 'Registration failed. Please check all fields.', 'error');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Registration';
        }
    })
    .catch(error => {
        console.error('Signup error:', error);
        showNotification(error.message || 'An error occurred. Please try again.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = 'Submit Registration';
    });
}

/**
 * Setup file preview for upload inputs
 */
function setupFilePreview(inputId, previewId, label) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    
    if (!input || !preview) return;
    
    input.addEventListener('change', function() {
        const file = this.files[0];
        if (!file) {
            preview.innerHTML = '';
            return;
        }
        
        // Validate file size (16MB)
        const maxSize = 16 * 1024 * 1024; // 16MB in bytes
        if (file.size > maxSize) {
            preview.innerHTML = `
                <div class="p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p class="text-sm text-red-600 font-semibold">File too large!</p>
                    <p class="text-xs text-red-500">Maximum size is 16MB. Your file is ${(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
            `;
            this.value = '';
            return;
        }
        
        // Show file info
        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        const isImage = file.type.startsWith('image/');
        
        let previewHTML = `
            <div class="p-3 bg-green-50 border border-green-200 rounded-lg">
                <div class="flex items-center justify-between mb-2">
                    <div class="flex items-center space-x-2">
                        <svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <span class="text-sm font-semibold text-green-800">${label} Uploaded</span>
                    </div>
                    <button type="button" class="text-red-500 hover:text-red-700" onclick="clearFilePreview('${inputId}', '${previewId}')">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                        </svg>
                    </button>
                </div>
                <p class="text-xs text-gray-700 font-medium truncate">${file.name}</p>
                <p class="text-xs text-gray-500">${fileSize} MB</p>
        `;
        
        // Show image preview if it's an image
        if (isImage) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewHTML += `
                    <div class="mt-2">
                        <img src="${e.target.result}" alt="Preview" class="w-full h-32 object-cover rounded-lg border border-gray-200">
                    </div>
                `;
                previewHTML += '</div>';
                preview.innerHTML = previewHTML;
            };
            reader.readAsDataURL(file);
        } else {
            previewHTML += '</div>';
            preview.innerHTML = previewHTML;
        }
    });
}

/**
 * Clear file preview
 */
function clearFilePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    if (input) input.value = '';
    if (preview) preview.innerHTML = '';
}

// Export functions for use in other scripts
window.KwetuDeliveries = {
    showNotification,
    formatCurrency,
    updateCartCount,
    debounce,
    clearFilePreview
};

