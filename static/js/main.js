/**
 * Hermes - Main JavaScript
 * Sistema de eventos e interações
 */

(function() {
    'use strict';
    
    // ===== MOBILE MENU TOGGLE =====
    const navToggle = document.querySelector('.nav-toggle');
    const navMobile = document.querySelector('.nav-mobile');
    
    if (navToggle && navMobile) {
        navToggle.addEventListener('click', function() {
            const isExpanded = navToggle.getAttribute('aria-expanded') === 'true';
            
            navToggle.setAttribute('aria-expanded', !isExpanded);
            navMobile.setAttribute('aria-hidden', isExpanded);
            navMobile.classList.toggle('active');
            
            // Animar ícone hambúrguer
            const icon = navToggle.querySelector('.nav-toggle-icon');
            icon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(90deg)';
        });
    }
    
    // ===== AUTO-CLOSE ALERTS =====
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(function(alert) {
        // Botão de fechar
        const closeBtn = alert.querySelector('.alert-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                closeAlert(alert);
            });
        }
        
        // Auto-close após 5 segundos
        setTimeout(function() {
            closeAlert(alert);
        }, 5000);
    });
    
    function closeAlert(alert) {
        alert.style.opacity = '0';
        alert.style.transform = 'translateY(-10px)';
        setTimeout(function() {
            alert.remove();
        }, 300);
    }
    
    // ===== CONFIRM DELETE =====
    const deleteLinks = document.querySelectorAll('[data-confirm-delete]');
    
    deleteLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const message = link.getAttribute('data-confirm-message') || 
                          'Tem certeza que deseja excluir?';
            
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // ===== FORM VALIDATION ENHANCEMENT =====
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const inputs = form.querySelectorAll('[required]');
            let isValid = true;
            
            inputs.forEach(function(input) {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add('error');
                    
                    // Remover classe de erro ao digitar
                    input.addEventListener('input', function() {
                        input.classList.remove('error');
                    }, { once: true });
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('Por favor, preencha todos os campos obrigatórios.');
            }
        });
    });
    
    // ===== SMOOTH SCROLL =====
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href === '#') return;
            
            e.preventDefault();
            const target = document.querySelector(href);
            
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // ===== THEME TOGGLE (opcional) =====
    function initThemeToggle() {
        const themeToggle = document.querySelector('[data-theme-toggle]');
        if (!themeToggle) return;
        
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);
        
        themeToggle.addEventListener('click', function() {
            const theme = document.documentElement.getAttribute('data-theme');
            const newTheme = theme === 'light' ? 'dark' : 'light';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }
    
    initThemeToggle();
    
    // ===== FILE INPUT ENHANCEMENT =====
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            const fileName = this.files[0]?.name || 'Nenhum arquivo selecionado';
            const label = this.nextElementSibling;
            
            if (label && label.classList.contains('file-label')) {
                label.textContent = fileName;
            }
        });
    });
    
    // ===== INIT =====
    console.log('✅ Hermes JS carregado');
})();