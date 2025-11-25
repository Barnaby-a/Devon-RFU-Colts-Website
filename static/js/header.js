let lastScrollY = window.scrollY;

window.addEventListener('scroll', function() {
    const header = document.getElementById('main-header');
    if (!header) return;

    const currentScrollY = window.scrollY;
    if (currentScrollY > lastScrollY) {
        // scrolling down
        header.classList.add('scrolled');
    } else {
        // scrolling up or no movement
        header.classList.remove('scrolled');
    }
    lastScrollY = currentScrollY;
});

document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".nav-buttons");
    const currentPath = window.location.pathname;

    navLinks.forEach(link => {
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });
});
