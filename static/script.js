// Sidebar toggle functionality
const menuBtn = document.getElementById('menuBtn');
const sidebar = document.getElementById('sidebar');
const overlay = document.getElementById('overlay');
const closeBtn = document.getElementById('closeBtn');

// Open sidebar
function openSidebar() {
    sidebar.classList.add('active');
    overlay.classList.add('active');
    menuBtn.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close sidebar
function closeSidebar() {
    sidebar.classList.remove('active');
    overlay.classList.remove('active');
    menuBtn.classList.remove('active');
    document.body.style.overflow = '';
}

// Event listeners
if (menuBtn) {
    menuBtn.addEventListener('click', openSidebar);
}

if (closeBtn) {
    closeBtn.addEventListener('click', closeSidebar);
}

if (overlay) {
    overlay.addEventListener('click', closeSidebar);
}

// Close sidebar on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && sidebar.classList.contains('active')) {
        closeSidebar();
    }
});

// Authentication check function
async function checkUserAuth() {
    try {
        const response = await fetch('/api/user');
        if (response.ok) {
            const user = await response.json();
            return user;
        }
    } catch (error) {
        return null;
    }
    return null;
}

// Update navigation based on auth status
async function updateNavigation() {
    const user = await checkUserAuth();
    const loginLink = document.getElementById('loginLink');
    const registerLink = document.getElementById('registerLink');
    const logoutLink = document.getElementById('logoutLink');
    const adminLink = document.getElementById('adminLink');
    const profileLink = document.getElementById('profileLink');
    
    if (user) {
        if (loginLink) loginLink.style.display = 'none';
        if (registerLink) registerLink.style.display = 'none';
        if (logoutLink) logoutLink.style.display = 'block';
        if (profileLink) profileLink.style.display = 'block';
        
        if (user.role === 'admin' && adminLink) {
            adminLink.style.display = 'block';
        }
        
        if (logoutLink) {
            logoutLink.addEventListener('click', async (e) => {
                e.preventDefault();
                try {
                    await fetch('/api/logout', { method: 'POST' });
                    window.location.href = 'index.html';
                } catch (error) {
                    window.location.href = 'index.html';
                }
            });
        }
    } else {
        if (loginLink) loginLink.style.display = 'block';
        if (registerLink) registerLink.style.display = 'block';
        if (logoutLink) logoutLink.style.display = 'none';
        if (adminLink) adminLink.style.display = 'none';
        if (profileLink) profileLink.style.display = 'none';
    }
}

// Call on page load if navigation elements exist
if (document.getElementById('loginLink') || document.getElementById('logoutLink')) {
    updateNavigation();
}

// Registration form handling
const registrationForm = document.getElementById('registrationForm');
const successMessage = document.getElementById('successMessage');
const errorMessage = document.getElementById('errorMessage');

if (registrationForm) {
    registrationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(registrationForm);
        const role = formData.get('role') || 'user';
        
        const data = {
            email: formData.get('email'),
            password: formData.get('password'),
            fullName: formData.get('fullName'),
            phone: formData.get('phone'),
            role: role
        };
        
        // Add company data if case_holder
        if (role === 'case_holder') {
            data.companyName = formData.get('companyName') || '';
            data.companyDescription = formData.get('companyDescription') || '';
            data.legalAddress = formData.get('legalAddress') || '';
            data.officialWebsite = formData.get('officialWebsite') || '';
        }
        
        // Validate form
        if (!formData.get('terms')) {
            if (errorMessage) {
                errorMessage.textContent = 'Пожалуйста, согласитесь с условиями использования';
                errorMessage.style.display = 'block';
            } else {
                alert('Пожалуйста, согласитесь с условиями использования');
            }
            return;
        }

        if (!data.password) {
            if (errorMessage) {
                errorMessage.textContent = 'Пожалуйста, введите пароль';
                errorMessage.style.display = 'block';
            } else {
                alert('Пожалуйста, введите пароль');
            }
            return;
        }
        
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                if (successMessage) {
                    successMessage.style.display = 'block';
                }
                if (errorMessage) {
                    errorMessage.style.display = 'none';
                }
                registrationForm.reset();
                
                // Redirect based on role
                setTimeout(() => {
                    if (result.user.role === 'admin') {
                        window.location.href = 'admin.html';
                    } else {
                        window.location.href = 'index.html';
                    }
                }, 1500);
            } else {
                if (errorMessage) {
                    errorMessage.textContent = result.error || 'Ошибка регистрации';
                    errorMessage.style.display = 'block';
                } else {
                    alert(result.error || 'Ошибка регистрации');
                }
                if (successMessage) {
                    successMessage.style.display = 'none';
                }
            }
        } catch (error) {
            if (errorMessage) {
                errorMessage.textContent = 'Ошибка соединения с сервером';
                errorMessage.style.display = 'block';
            } else {
                alert('Ошибка соединения с сервером');
            }
            if (successMessage) {
                successMessage.style.display = 'none';
            }
        }
    });
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#' && href !== '#!') {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    });
});

// Add animation on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe feature cards
document.querySelectorAll('.feature-card').forEach(card => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(20px)';
    card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    observer.observe(card);
});

