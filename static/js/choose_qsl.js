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
H
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

function toggleParkEntryVisibility() {
    boxChecked = document.getElementById("logPota").checked;
    parkInput  = document.getElementById("parkNumbers");
    hunterRadio    = document.getElementById("hunterRadio");
    activatorRadio = document.getElementById("activatorRadio");

    parkInput.disabled = !boxChecked;
    hunterRadio.disabled = !boxChecked;
    activatorRadio.disabled = !boxChecked;
}
document.getElementById("logPota").addEventListener("change", toggleParkEntryVisibility);

toggleParkEntryVisibility();
