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

// Position flash messages below the header and auto-hide them
document.addEventListener('DOMContentLoaded', () => {
    const flashesContainer = document.getElementById('flashes');
    const header = document.getElementById('main-header');
    if (!flashesContainer || !header) return;

    // place flashes just below the header
    const placeBelowHeader = () => {
        const rect = header.getBoundingClientRect();
        // account for page scroll
        const topOffset = rect.bottom + window.scrollY + 8;
        flashesContainer.style.top = `${topOffset}px`;
    };

    placeBelowHeader();
    // reposition on resize / scroll changes (debounced)
    let t;
    const debounce = (fn, wait=100) => {
        return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), wait); };
    };
    window.addEventListener('resize', debounce(placeBelowHeader, 80));
    window.addEventListener('scroll', debounce(placeBelowHeader, 80));

    // animate and auto-hide each flash after 5s
    const flashes = Array.from(flashesContainer.querySelectorAll('.flash'));
    flashes.forEach((f, i) => {
        // ensure clickability
        f.classList.add('show');

        // auto-hide after 5 seconds
        const hideAfter = 5000; // ms
        setTimeout(() => {
            f.classList.remove('show');
            f.classList.add('hide');
            // remove from DOM after transition
            setTimeout(() => { try { f.remove(); } catch(e){} }, 300);
        }, hideAfter + (i * 150));
    });
});
