var frequencyAdjusted = false;

// Auto-populate date in UTC if empty
function setUTCDate() {
    const now = new Date();
    const utc = now.toISOString().replace("T", " ").substring(0,16).replace(":", "") + " UTC";
    const field = document.getElementById("dateField");
    if (!field.value) field.value = utc;
}

function setBand(band) {
    const select = document.getElementById('bandSelect');
    select.value = band;

    select.dispatchEvent(new Event('change'));
}

// Mode buttons
function setMode(mode) {
    document.getElementById("modeField").value = mode;
    setQuickFreq();
}

// RST buttons
function setRSTS(RST) {
    document.getElementById("rsts").value = RST;
}

// RST buttons
function setRSTR(RST) {
    document.getElementById("rstr").value = RST;
}

// Auto-set FT8 frequency if band is selected
function setQuickFreq() {
    if (frequencyAdjusted === false || isFreqInBand() === false) {
        const band = document.getElementById("bandSelect").value;
        const mode = document.getElementById("modeField").value;
        const freq = quickFreqs[mode]?.[band];
        if (freq) {
            document.getElementById("freqField").value = freq;
            setFreqPrecision();
        }
        frequencyAdjusted = false;
    }
}

function getAbsFreq() {
    const freq = document.getElementById("freqField").value;
    const prefix = document.getElementById("fpLabel").innerText;

    var absFrq = parseFloat(freq) * 1000.0;
    if (prefix === "MHz")
        absFrq = absFrq * 1000.0;

    return absFrq;
}

function setFreqPrecision() {
    const freq = parseFloat(document.getElementById("freqField").value);

    var frmtFreq = freq.toFixed(3);

    console.log(frmtFreq);
    if (freq > parseFloat(frmtFreq)) {
        frmtFreq = freq;
        console.log("hi");
    }

    document.getElementById("freqField").value = frmtFreq;
}

function isFreqInBand() {
    const absFrq = getAbsFreq();
    const currentBand = document.getElementById("bandSelect").value;

    const min = parseFloat(freqRange[currentBand][0]) * 1000000.0;
    const max = parseFloat(freqRange[currentBand][1]) * 1000000.0;

    if (absFrq >= min && absFrq <= max)
        return true;

    return false;
}

function setBandFromFreq() {
    const absFrq = getAbsFreq();

    for (const [k, v] of Object.entries(freqRange)) {
        min = parseFloat(v[0]) * 1000000.0;
        max = parseFloat(v[1]) * 1000000.0;

        if (absFrq >= min && absFrq <= max) {
            document.getElementById("bandSelect").value = k;
            setFreqLabel();
            setFreqPrecision();
            break;
        }
    }
}

function setFreqLabel() {
    const band = document.getElementById("bandSelect").value;
    const freq = document.getElementById("freqField").value;
    const prefix = document.getElementById("fpLabel").innerText;
    var absFrq = getAbsFreq();

    newPrefix = "MHz";

    if (band === "630m" || band === "2200m") {
        newPrefix = "KHz";
    }
    else {
        absFrq = absFrq / 1000.0;
    }

    document.getElementById("fpValue").value = newPrefix;
    document.getElementById("fpLabel").innerText = newPrefix;
    document.getElementById("freqField").value = absFrq / 1000.0;
}

document.getElementById("bandSelect").addEventListener("change", setQuickFreq);
document.getElementById("bandSelect").addEventListener("change", setFreqLabel);
document.getElementById("bandSelect").addEventListener("change", setFreqPrecision);
document.getElementById("freqField").addEventListener("change", setBandFromFreq);
document.getElementById("freqField").addEventListener("change", setFreqPrecision);
document.getElementById("freqField").addEventListener("change", function() { frequencyAdjusted = true; })
document.getElementById('callsign-form').addEventListener('submit', function(e) {
    e.preventDefault();  // prevent actual form submission
    const callsign = document.getElementById('callsign-input').value.trim().toUpperCase();
    if (callsign) {
        // Redirect to /lookup/<callsign>
        window.location.href = '/lookup/' + encodeURIComponent(callsign);
    }
});

setUTCDate();
setFreqLabel();
setFreqPrecision();
