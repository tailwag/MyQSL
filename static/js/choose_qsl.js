document.addEventListener("DOMContentLoaded", () => {
    const emailInput = document.getElementById("emailInput");
    const sendQsl = document.getElementById("sendQsl");
    const noCard = document.getElementById("noCard");
    const backdropRadios = document.querySelectorAll(".backdrop-radio");

    const firstImage = backdropRadios.length ? backdropRadios[0] : null;

    function hasEmail() {
        return emailInput.value.trim().length > 0;
    }

    function isImageSelected() {
        return [...backdropRadios].some(r => r.checked);
    }

    function applyRules() {
        if (!hasEmail()) {
            // NO EMAIL CASE
            noCard.checked = true;
            sendQsl.checked = false;
            sendQsl.disabled = true;
            return;
        }

        if (noCard.checked) {
            // Email exists, but no card selected
            sendQsl.checked = false;
            sendQsl.disabled = true;
            return;
        }

        // Email exists + card selected
        sendQsl.disabled = false;
        sendQsl.checked = true;
    }

    // --- Event wiring ---

    // When user types email
    emailInput.addEventListener("input", () => {
        if (hasEmail() && !isImageSelected() && firstImage) {
            firstImage.checked = true;
        }
        applyRules();
    });

    // When selecting "no card"
    noCard.addEventListener("change", applyRules);

    // When selecting any card image
    backdropRadios.forEach(radio =>
        radio.addEventListener("change", () => {
            if (radio.checked) {
                noCard.checked = false;
            }
            applyRules();
        })
    );

    // --- Initial state on page load ---
    if (hasEmail()) {
        if (firstImage) firstImage.checked = true;
    } else {
        noCard.checked = true;
    }

    applyRules();
});
(function () {
    const toggleBtn = document.getElementById("themeToggle");
    const body = document.body;

    const savedTheme = localStorage.getItem("theme");

    if (savedTheme) {
        body.setAttribute("data-bs-theme", savedTheme);
    }

    function updateLabel() {
        const theme = body.getAttribute("data-bs-theme");
        toggleBtn.textContent = theme === "dark" ? "☀️ Light" : "🌙 Dark";
    }

    toggleBtn.addEventListener("click", () => {
        const current = body.getAttribute("data-bs-theme");
        const next = current === "dark" ? "light" : "dark";
        body.setAttribute("data-bs-theme", next);
        localStorage.setItem("theme", next);
        updateLabel();
    });

    updateLabel();
})();
