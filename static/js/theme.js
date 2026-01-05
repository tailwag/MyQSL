(() => {
    const toggle = document.getElementById("themeToggle");
    const icon = document.getElementById("themeIcon");
    const body = document.body;

    function applyTheme(theme) {
        body.setAttribute("data-bs-theme", theme);
        localStorage.setItem("theme", theme);

        if (theme === "dark") {
            toggle.checked = true;
            icon.className = "bi bi-sun";
        } else {
            toggle.checked = false;
            icon.className = "bi bi-moon-stars";
        }
    }

    // Init
    const saved = localStorage.getItem("theme") || "light";
    applyTheme(saved);

    // Toggle
    toggle.addEventListener("change", () => {
        applyTheme(toggle.checked ? "dark" : "light");
    });

    // Clicking icon also toggles
    icon.addEventListener("click", () => {
        applyTheme(body.getAttribute("data-bs-theme") === "dark" ? "light" : "dark");
    });
})();
