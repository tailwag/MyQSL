import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session

from MyQSL.QRZ import QRZClient
from MyQSL.CardGen import genCard
from MyQSL.O365_Send import sendMessage
from MyQSL.thumbnail import thumbnail_check
from MyQSL.config import get_config

qrz = QRZClient()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-secret")


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        callsign = request.form.get("callsign", "").upper()
        if callsign:
            # Redirect to /lookup/<callsign>
            return redirect(url_for("lookup", callsign=callsign))
    return render_template("index.html")  # static page


def format_mhz(freq_str: str) -> str:
    if "." not in freq_str:
        return freq_str + ".000MHz"

    whole, frac = freq_str.split(".", 1)

    if len(frac) <= 3:
        return f"{whole}.{frac.ljust(3, '0')}" + "MHz"

    return freq_str + "MHz"


def build_quick_freqs(quickfreq_xml):
    out = {}

    for mode, bands in quickfreq_xml.items():
        out[mode] = {}

        for band_tag, freq in bands.items():
            band = band_tag.replace("Band", "")

            out[mode][band] = f"{freq}MHz"

    return out


# Lookup and QSL page
@app.route("/lookup/<callsign>", methods=["GET", "POST"])
def lookup(callsign):
    callsign = callsign.upper()

    qrz_info = qrz.lookup(callsign)
    qso_history = qrz.get_previous_qsos(callsign)

    if qso_history:
        for qso in qso_history:
            rawfreq = qso.get("FREQ")
            if rawfreq:
                qso["FREQ"] = format_mhz(rawfreq)

    expandedClass = None
    state = None

    if qrz_info:
        country = qrz_info.get("country", "")
        if country == "United States":
            state = qrz_info.get("state")

            originalClass = qrz_info.get("class")

            if originalClass == "N":
                expandedClass = "Novice"
            elif originalClass == "T":
                expandedClass = "Technician"
            elif originalClass == "G":
                expandedClass = "General"
            elif originalClass == "A":
                expandedClass = "Advanced"
            elif originalClass == "E":
                expandedClass = "Extra"

    qslInfo = {
        "With": callsign,
        "Band": session.get("last_band", ""),
        "Mode": session.get("last_mode", ""),
        "Freq": session.get("last_freq", "")
    }

    qslInfo["With"] = callsign

    quickband = get_config("Settings/QuickBand").split(",")
    quickmode = get_config("Settings/QuickMode").split(",")
    quickrsts = get_config("Settings/QuickRSTS").split(",")
    quickrstr = get_config("Settings/QuickRSTR").split(",")
    quickfreq = build_quick_freqs(get_config("Settings/QuickFreq"))

    return render_template(
        "lookup.html",
        qrz_info=qrz_info,
        state=state,
        expandedClass=expandedClass,
        quickband=quickband,
        quickmode=quickmode,
        quickrsts=quickrsts,
        quickrstr=quickrstr,
        quickfreq=quickfreq,
        qso_history=qso_history,
        qslInfo=qslInfo
    )


def get_backdrop_images():
    thumbnail_check()

    return sorted(
        f for f in os.listdir(get_config("Settings/QSLCard/ThumbnailPath"))
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
    )


@app.route("/qsl/choose", methods=["POST"])
def choose_qsl():
    qso = request.form.to_dict()

    backdrops = get_backdrop_images()

    return render_template(
        "choose_qsl.html",
        qso=qso,
        backdrops=backdrops
    )


@app.route("/qsl/confirm", methods=["POST"])
def confirm_qsl():
    qso = request.form.to_dict()

    session["last_band"] = qso.get("Band")
    session["last_mode"] = qso.get("Mode")
    session["last_freq"] = qso.get("Freq")

    email = qso.get('__hidden_email')
    backdrop = qso.get('__hidden_backdrop')
    sendqsl = qso.get('__hidden_send_qsl')
    logqso = qso.get('__hidden_log_qso')

    hiddenKeys = []
    for k, v in qso.items():
        if k[0:9] == "__hidden_":
            hiddenKeys.append(k)

    for i in hiddenKeys:
        del qso[i]

    card_path = None
    if backdrop and backdrop != "none":
        card_path = genCard(qso, get_config("Settings/QSLCard/BackdropPath") + backdrop)

    if sendqsl == "yes" and card_path:

        sendMessage(
            email,
            get_config("Settings/QSLCard/EmailSubject"),
            get_config("Settings/QSLCard/EmailBody"),
            card_path
        )

    if logqso == "yes":
        qrz.log_qso(qso)

    flash("QSO processed successfully", "success")
    return redirect(url_for("index", callsign=qso["With"]))

if __name__ == "__main__":
    app.run(debug=True)
