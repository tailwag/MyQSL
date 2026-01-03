####################################################################
# MyQSL             - Devin Shoemaker 2025 - devin@shoemaker.info  #
#                                                                  #
# This is the main app file. It will spawn a flask webserver for   #
# you to interact with from your browser.                          #
####################################################################

import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session

from MyQSL.CardGen import genCard
from MyQSL.O365_Send import sendMessage
from MyQSL.thumbnail import thumbnail_check
from MyQSL.QRZ import QRZClient, expand_class
from MyQSL.config import get_config, build_freq_range, build_quick_freq, get_backdrop_images

qrz = QRZClient()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-secret")


######################################################################
# Support functions                                                  #
######################################################################
def format_mhz(freq_str: str) -> str:
    if "." not in freq_str:
        return freq_str + ".000MHz"

    whole, frac = freq_str.split(".", 1)

    if len(frac) <= 3:
        return f"{whole}.{frac.ljust(3, '0')}" + "MHz"

    return freq_str + "MHz"


######################################################################
# Flask routes                                                       #
######################################################################
# Landing page
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        callsign = request.form.get("callsign", "").upper()
        if callsign:
            return redirect(url_for("lookup", callsign=callsign))
    return render_template("index.html")


# Lookup and QSL page
@app.route("/lookup/<callsign>", methods=["GET", "POST"])
def lookup(callsign):
    callsign = callsign.upper()

    qrz_info = expand_class(qrz.lookup(callsign))
    qso_history = qrz.get_previous_qsos(callsign)

    if qso_history:
        for qso in qso_history:
            rawfreq = qso.get("FREQ")
            if rawfreq:
                qso["FREQ"] = format_mhz(rawfreq)


    qslInfo = {
        "With": callsign,
        "Band": session.get("last_band", ""),
        "Mode": session.get("last_mode", ""),
        "Freq": session.get("last_freq", "")
    }

    qslInfo["With"] = callsign

    bands = get_config("Settings/Bands").split(",")
    quickband = get_config("Settings/QuickBand").split(",")
    quickmode = get_config("Settings/QuickMode").split(",")
    quickrsts = get_config("Settings/QuickRSTS").split(",")
    quickrstr = get_config("Settings/QuickRSTR").split(",")
    quickfreq = build_quick_freq(get_config("Settings/QuickFreq"))
    freqrange = build_freq_range(get_config("Settings/FreqRange"))

    return render_template(
        "lookup.html",
        qrz_info=qrz_info,
        bands=bands,
        quickband=quickband,
        quickmode=quickmode,
        quickrsts=quickrsts,
        quickrstr=quickrstr,
        quickfreq=quickfreq,
        freqrange=freqrange,
        qso_history=qso_history,
        qslInfo=qslInfo
    )


@app.route("/qsl/choose", methods=["POST"])
def choose_qsl():
    qso = request.form.to_dict()

    thumbnail_check()
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

    # extra values we need from the form, but must be
    # removed before the QSL card gets generated
    hiddenKeys = {}
    for k, v in qso.items():
        if k[0:9] == "__hidden_":
            hiddenKeys[k[9:]] = v

    for i in hiddenKeys:
        del qso['__hidden_' + i]

    # deal with MyQSO / QRZ low band frequency discrepancy
    # I think most people would prefer 137KHz to be labeled as 
    # such, but QRZ expects 0.137MHz
    original_freq = qso.get('Freq')
    adjusted_freq = original_freq
    if hiddenKeys['frequency_prefix'] == "KHz":
        adjusted_freq = str(float(adjusted_freq) / 1000.0)

    qso["Freq"] = original_freq + hiddenKeys['frequency_prefix']

    # generate QSL card using selected background
    card_path = None
    if hiddenKeys['backdrop'] and hiddenKeys['backdrop'] != "none":
        card_path = genCard(qso, get_config("Settings/QSLCard/BackdropPath") + hiddenKeys['backdrop'])

    if hiddenKeys.get('send_qsl') == "yes" and card_path:
        sendMessage(
            hiddenKeys['email'],
            get_config("Settings/QSLCard/EmailSubject"),
            get_config("Settings/QSLCard/EmailBody"),
            card_path
        )

    qso["Freq"] = adjusted_freq
    if hiddenKeys.get('log_qso') == "yes":
        qrz.log_qso(qso)

    flash("QSO processed successfully", "success")
    return redirect(url_for("index", callsign=qso["With"]))

if __name__ == "__main__":
    app.run(debug=True)
