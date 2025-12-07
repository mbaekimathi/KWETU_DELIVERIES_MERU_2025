/**
 * Dashboard JavaScript
 * Handles dropdowns and interactive elements
 */

/**
 * Initialize Sidebar
 */
function initSidebar() {
    const sidebar = document.getElementById('dashboard-sidebar');
    const sidebarToggleBtn = document.getElementById('sidebar-toggle-btn');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    
    if (!sidebar) return;
    
    // Set active navigation item based on current URL
    setActiveNavItem();
    
    // Toggle sidebar
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleSidebar();
        });
    }
    
    // Close sidebar when clicking overlay
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            closeSidebar();
        });
    }
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(e) {
        if (window.innerWidth < 1024) {
            if (sidebar && sidebar.classList.contains('active')) {
                if (!sidebar.contains(e.target) && 
                    !sidebarToggleBtn?.contains(e.target)) {
                    closeSidebar();
                }
            }
        }
    });
    
    // Handle window resize
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function() {
            const sidebarToggleIcon = document.getElementById('sidebar-toggle-icon');
            const mainWrapper = document.querySelector('.dashboard-main-wrapper');
            const isActive = sidebar.classList.contains('active');
            const isDesktop = window.innerWidth >= 1024;
            
            if (isDesktop) {
                // Desktop: maintain current state, update wrapper class
                if (sidebarOverlay) {
                    sidebarOverlay.classList.remove('active');
                }
                if (mainWrapper) {
                    if (isActive) {
                        mainWrapper.classList.add('has-sidebar');
                    } else {
                        mainWrapper.classList.remove('has-sidebar');
                    }
                }
                // Update icon based on state
                if (sidebarToggleIcon) {
                    if (isActive) {
                        sidebarToggleIcon.classList.remove('fa-bars');
                        sidebarToggleIcon.classList.add('fa-times');
                    } else {
                        sidebarToggleIcon.classList.remove('fa-times');
                        sidebarToggleIcon.classList.add('fa-bars');
                    }
                }
                // Restore body scroll on desktop
                document.body.style.overflow = '';
            } else {
                // Mobile: maintain current state
                if (mainWrapper) {
                    mainWrapper.classList.remove('has-sidebar');
                }
                if (isActive && sidebarOverlay) {
                    sidebarOverlay.classList.add('active');
                } else if (sidebarOverlay) {
                    sidebarOverlay.classList.remove('active');
                }
                // Update icon
                if (sidebarToggleIcon) {
                    if (isActive) {
                        sidebarToggleIcon.classList.remove('fa-bars');
                        sidebarToggleIcon.classList.add('fa-times');
                    } else {
                        sidebarToggleIcon.classList.remove('fa-times');
                        sidebarToggleIcon.classList.add('fa-bars');
                    }
                }
            }
        }, 100);
    });
    
    // Initialize based on screen size - start with sidebar open on desktop, closed on mobile
    const sidebarToggleIcon = document.getElementById('sidebar-toggle-icon');
    const mainWrapper = document.querySelector('.dashboard-main-wrapper');
    
    // Check if sidebar state is stored in localStorage
    const storedSidebarState = localStorage.getItem('sidebarState');
    const isDesktop = window.innerWidth >= 1024;
    
    if (isDesktop) {
        // Desktop: check stored state or default to open
        const shouldBeOpen = storedSidebarState === null ? true : storedSidebarState === 'open';
        
        if (shouldBeOpen) {
            sidebar.classList.add('active');
            if (mainWrapper) {
                mainWrapper.classList.add('has-sidebar');
            }
            if (sidebarToggleIcon) {
                sidebarToggleIcon.classList.remove('fa-bars');
                sidebarToggleIcon.classList.add('fa-times');
            }
            localStorage.setItem('sidebarState', 'open');
        } else {
            sidebar.classList.remove('active');
            if (mainWrapper) {
                mainWrapper.classList.remove('has-sidebar');
            }
            if (sidebarToggleIcon) {
                sidebarToggleIcon.classList.remove('fa-times');
                sidebarToggleIcon.classList.add('fa-bars');
            }
            localStorage.setItem('sidebarState', 'closed');
        }
    } else {
        // Mobile: start with sidebar closed
        sidebar.classList.remove('active');
        if (mainWrapper) {
            mainWrapper.classList.remove('has-sidebar');
        }
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('active');
        }
        if (sidebarToggleIcon) {
            sidebarToggleIcon.classList.remove('fa-times');
            sidebarToggleIcon.classList.add('fa-bars');
        }
    }
}

/**
 * Toggle Sidebar
 */
function toggleSidebar() {
    const sidebar = document.getElementById('dashboard-sidebar');
    const sidebarToggleIcon = document.getElementById('sidebar-toggle-icon');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const mainWrapper = document.querySelector('.dashboard-main-wrapper');
    const isDesktop = window.innerWidth >= 1024;
    
    if (!sidebar) return;
    
    const isActive = sidebar.classList.contains('active');
    
    if (isActive) {
        // Close sidebar
        sidebar.classList.remove('active');
        if (mainWrapper) {
            mainWrapper.classList.remove('has-sidebar');
        }
        if (sidebarOverlay) {
            sidebarOverlay.classList.remove('active');
        }
        if (sidebarToggleIcon) {
            sidebarToggleIcon.classList.remove('fa-times');
            sidebarToggleIcon.classList.add('fa-bars');
        }
        // Restore body scroll
        document.body.style.overflow = '';
        
        // Save state for desktop
        if (isDesktop) {
            localStorage.setItem('sidebarState', 'closed');
        }
    } else {
        // Open sidebar
        sidebar.classList.add('active');
        if (mainWrapper && isDesktop) {
            mainWrapper.classList.add('has-sidebar');
        }
        if (sidebarOverlay) {
            // Only show overlay on mobile
            if (!isDesktop) {
                sidebarOverlay.classList.add('active');
            }
        }
        if (sidebarToggleIcon) {
            sidebarToggleIcon.classList.remove('fa-bars');
            sidebarToggleIcon.classList.add('fa-times');
        }
        // Prevent body scroll on mobile
        if (!isDesktop) {
            document.body.style.overflow = 'hidden';
        }
        
        // Save state for desktop
        if (isDesktop) {
            localStorage.setItem('sidebarState', 'open');
        }
    }
}

/**
 * Open Sidebar
 */
function openSidebar() {
    const sidebar = document.getElementById('dashboard-sidebar');
    const sidebarToggleIcon = document.getElementById('sidebar-toggle-icon');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const mainWrapper = document.querySelector('.dashboard-main-wrapper');
    const isDesktop = window.innerWidth >= 1024;
    
    if (sidebar && !sidebar.classList.contains('active')) {
        sidebar.classList.add('active');
        if (mainWrapper && isDesktop) {
            mainWrapper.classList.add('has-sidebar');
        }
        if (sidebarToggleIcon) {
            sidebarToggleIcon.classList.remove('fa-bars');
            sidebarToggleIcon.classList.add('fa-times');
        }
    }
    
    if (sidebarOverlay) {
        if (!isDesktop) {
            sidebarOverlay.classList.add('active');
        }
    }
    
    // Prevent body scroll on mobile
    if (!isDesktop) {
        document.body.style.overflow = 'hidden';
    }
}

/**
 * Close Sidebar
 */
function closeSidebar() {
    const sidebar = document.getElementById('dashboard-sidebar');
    const sidebarToggleIcon = document.getElementById('sidebar-toggle-icon');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const mainWrapper = document.querySelector('.dashboard-main-wrapper');
    
    if (sidebar && sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        if (mainWrapper) {
            mainWrapper.classList.remove('has-sidebar');
        }
        if (sidebarToggleIcon) {
            sidebarToggleIcon.classList.remove('fa-times');
            sidebarToggleIcon.classList.add('fa-bars');
        }
    }
    
    if (sidebarOverlay) {
        sidebarOverlay.classList.remove('active');
    }
    
    // Restore body scroll
    document.body.style.overflow = '';
}

/**
 * Set Active Navigation Item
 */
function setActiveNavItem() {
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll('.sidebar-nav-item');
    
    navItems.forEach(item => {
        const itemPath = new URL(item.href).pathname;
        
        // Remove active class from all items
        item.classList.remove('active');
        
        // Check if current path matches or starts with item path
        if (currentPath === itemPath || 
            (itemPath !== '/dashboard' && currentPath.startsWith(itemPath))) {
            item.classList.add('active');
        }
    });
    
    // Special case for dashboard home
    if (currentPath.match(/^\/dashboard\/(admin|manager|cashier|sales|rider|customercare|technician|it-support|employee)$/)) {
        const dashboardNav = document.getElementById('nav-dashboard');
        if (dashboardNav) {
            dashboardNav.classList.add('active');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initSidebar();
    initProfileDropdown();
    initNotifications();
});

/**
 * Initialize Profile Dropdown
 */
function initProfileDropdown() {
    const dropdownBtn = document.getElementById('profile-dropdown-btn');
    const dropdownMenu = document.getElementById('profile-dropdown-menu');
    
    if (!dropdownBtn || !dropdownMenu) return;
    
    // Toggle dropdown
    dropdownBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        const isActive = dropdownMenu.classList.contains('active');
        
        // Close all other dropdowns
        document.querySelectorAll('.profile-dropdown-menu.active').forEach(menu => {
            if (menu !== dropdownMenu) {
                menu.classList.remove('active');
            }
        });
        document.querySelectorAll('.profile-menu-trigger.active').forEach(btn => {
            if (btn !== dropdownBtn) {
                btn.classList.remove('active');
            }
        });
        
        // Toggle current dropdown
        dropdownMenu.classList.toggle('active');
        dropdownBtn.classList.toggle('active');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
            dropdownMenu.classList.remove('active');
            dropdownBtn.classList.remove('active');
        }
    });
    
    // Close dropdown when clicking on a link
    const dropdownItems = dropdownMenu.querySelectorAll('.dropdown-menu-item');
    dropdownItems.forEach(item => {
        item.addEventListener('click', function() {
            // Don't close immediately for logout to allow navigation
            if (this.classList.contains('logout-item')) {
                return;
            }
            setTimeout(() => {
                dropdownMenu.classList.remove('active');
                dropdownBtn.classList.remove('active');
            }, 100);
        });
    });
}

/**
 * Initialize Notifications
 */
function initNotifications() {
    const notificationsBtn = document.getElementById('notifications-btn');
    
    if (notificationsBtn) {
        notificationsBtn.addEventListener('click', function() {
            // TODO: Implement notifications dropdown
            console.log('Notifications clicked');
        });
    }
}

/**
 * Show Dashboard Notification
 */
function showDashboardNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `dashboard-notification dashboard-notification-${type}`;
    notification.textContent = message;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

/**
 * Format Role Name for Display
 */
function formatRoleName(role) {
    return role.replace('KWETU_', '').replace(/_/g, ' ').toLowerCase()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}
