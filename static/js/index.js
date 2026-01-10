function isTerminalStatus(text) {
    return (
        text === null ||
        text === "" ||
        text === "None" ||
        text === "Sent" ||
        text === "Logged"
    );
}
async function fetchStatus(cell) {
    if (isTerminalStatus(cell.innerText)) cell.dataset.active = 0;
    if (cell.dataset.active !== "1") return;

    const qsoId = cell.dataset.qsoId;
    const item = cell.dataset.item;

    const form = new FormData();
    form.append("ACTION", "get_status");
    form.append("ITEM", item);
    form.append("QSOID", qsoId);

    try {
        const res = await fetch("/API/v1", {
            method: "POST",
            body: form
        });

        if (!res.ok) {
            cell.textContent = "Error";
            return;
        }

        const text = (await res.text()).trim();
        cell.textContent = text || "-";

        if (isTerminalStatus(text)) {
            cell.dataset.active = "0";
        }
    } catch (err) {
        cell.textContent = "Offline";
    }
}

function refreshStatuses() {
    document.querySelectorAll(".status-cell").forEach(fetchStatus);
}

// initial load
refreshStatuses();

// poll every .5 seconds
setInterval(refreshStatuses, 500);

setTimeout(() => {
    document.querySelectorAll('.alert').forEach(alert => {
        alert.classList.remove('show')

        alert.addEventListener('transitionend', () => {
            alert.remove()
        }, { once: true })
    })
}, 5000)

