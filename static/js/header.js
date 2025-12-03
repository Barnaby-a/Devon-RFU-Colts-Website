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

// Cookie consent banner behaviour
document.addEventListener('DOMContentLoaded', () => {
    const consentEl = document.getElementById('cookie-consent');
    if (!consentEl) return;

    const accepted = (() => {
        try { return localStorage.getItem('cookie_consent') === 'accepted'; } catch(e){ return false; }
    })();

    const show = () => { consentEl.style.display = 'flex'; };
    const hide = () => { consentEl.style.display = 'none'; };

    if (!accepted) show();

    const acceptBtn = document.getElementById('cookie-accept');
    if (acceptBtn) {
        acceptBtn.addEventListener('click', () => {
            try { localStorage.setItem('cookie_consent', 'accepted'); } catch(e){}
            // also set a cookie for server-side checks if needed (30 days)
            try { document.cookie = 'cookie_consent=accepted;path=/;max-age=' + (30*24*60*60); } catch(e){}
            hide();
        });
    }
});

// Reset handler for visible reset button on the Cookie Policy page
document.addEventListener('DOMContentLoaded', () => {
    const resetBtn = document.getElementById('cookie-reset');
    if (!resetBtn) return;
    resetBtn.addEventListener('click', (e) => {
        e.preventDefault();
        try { localStorage.removeItem('cookie_consent'); } catch(e){}
        try { document.cookie = 'cookie_consent=; path=/; max-age=0'; } catch(e){}
        // show the consent banner again
        const consentEl = document.getElementById('cookie-consent');
        if (consentEl) {
            consentEl.style.display = 'flex';
        }
        // scroll to bottom so mobile users can see the banner
        try { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); } catch(e){}
    });
});

// Cookie preferences: save/load toggles on cookie policy page
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('cookie-prefs-form');
    if (!form) return;

    const analyticsEl = document.getElementById('pref-analytics');
    const marketingEl = document.getElementById('pref-marketing');
    const saveBtn = document.getElementById('cookie-save');
    const savedMsg = document.getElementById('cookie-prefs-saved');

    const loadPrefs = () => {
        try {
            const raw = localStorage.getItem('cookie_preferences');
            if (!raw) return;
            const prefs = JSON.parse(raw);
            analyticsEl.checked = !!prefs.analytics;
            marketingEl.checked = !!prefs.marketing;
        } catch(e) {
            // ignore parse errors
        }
    };

    const applyCookiesForPrefs = (prefs) => {
        try {
            if (prefs.analytics) {
                document.cookie = 'analytics_consent=enabled; path=/; max-age=' + (30*24*60*60);
            } else {
                document.cookie = 'analytics_consent=; path=/; max-age=0';
            }
            if (prefs.marketing) {
                document.cookie = 'marketing_consent=enabled; path=/; max-age=' + (30*24*60*60);
            } else {
                document.cookie = 'marketing_consent=; path=/; max-age=0';
            }
        } catch(e) {}
    };

    loadPrefs();

    form.addEventListener('submit', (ev) => {
        ev.preventDefault();
        const prefs = { analytics: !!analyticsEl.checked, marketing: !!marketingEl.checked };
        try { localStorage.setItem('cookie_preferences', JSON.stringify(prefs)); } catch(e){}
        applyCookiesForPrefs(prefs);
        // also ensure cookie_consent is set so the banner doesn't reappear
        try { localStorage.setItem('cookie_consent', 'accepted'); } catch(e){}
        try { document.cookie = 'cookie_consent=accepted;path=/;max-age=' + (30*24*60*60); } catch(e){}
        // show a small saved message briefly
        if (savedMsg) {
            savedMsg.style.display = 'inline-block';
            setTimeout(() => { savedMsg.style.display = 'none'; }, 2500);
        }
    });
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
