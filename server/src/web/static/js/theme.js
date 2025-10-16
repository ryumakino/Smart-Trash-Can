class ThemeManager {
    static init() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.setTheme(savedTheme);
        
        // Adicionar botão de toggle de tema se não existir
        if (!document.querySelector('[onclick="toggleTheme()"]')) {
            this.createThemeToggle();
        }
    }
    
    static setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Atualizar ícone do botão
        const themeButton = document.querySelector('[onclick="toggleTheme()"]');
        if (themeButton) {
            const icon = themeButton.querySelector('i');
            if (icon) {
                icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
        }
    }
    
    static createThemeToggle() {
        const navActions = document.querySelector('.nav-actions');
        if (navActions) {
            const themeButton = document.createElement('button');
            themeButton.className = 'btn-icon';
            themeButton.onclick = toggleTheme;
            themeButton.title = 'Alternar Tema';
            themeButton.innerHTML = '<i class="fas fa-moon"></i>';
            navActions.appendChild(themeButton);
        }
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    ThemeManager.setTheme(newTheme);
    
    // Animação de transição suave
    document.documentElement.style.transition = 'all 0.3s ease';
    setTimeout(() => {
        document.documentElement.style.transition = '';
    }, 300);
}

// Inicializar gerenciador de tema
ThemeManager.init();