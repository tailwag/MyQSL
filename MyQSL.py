####################################################################
# MyQSL             - Devin Shoemaker 2025 - devin@shoemaker.info  #
#                                                                  #
# This is the main app file. It will spawn a flask webserver for   #
# you to interact with from your browser.                          #
####################################################################

import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from MyQSL.thumbnail import thumbnail_check
from MyQSL.config import get_config, build_freq_range, build_quick_freq, get_backdrop_images
from MyQSL.support import (
    qrz,
    db,
    format_mhz,
    qsl_status_text,
    qrz_status_text,
    get_status_texts,
    get_keys,
    card_path_from_adif,
    get_qrz_info,
    get_contact_history
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-secret")


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

    num_qsos = int(get_config("Settings/QSOHistory"))
    qsos = db.qso.get(num_qsos)

    qso_dicts = []

    for qso in qsos:
        row = dict(qso)
        row['qsl_status'], row['qrz_status'] = get_status_texts(qso.get('id'))
        qso_dicts.append(row)

    modes = db.stats.modes()
    bands = db.stats.bands()
    dates = db.stats.qsos_by_day(7)

    total_qsos = db.stats.total_qsos()
    cards_sent = db.stats.cards_sent()

    countries = db.stats.top_countries(6)
    states = db.stats.top_states(6)
    stations = db.stats.top_stations(6)

    colors = get_config("Settings/Colors").split(",")
    colors = [color.strip() for color in colors]

    return render_template(
        "index.html",
        colors=colors,
        modes=modes,
        bands=bands,
        dates=dates,
        qsolog=qso_dicts,
        total_qsos=total_qsos,
        cards_sent=cards_sent,
        countries=countries,
        states=states,
        stations=stations
    )


# delete a qso
@app.route("/delete/<qso_id>", methods=["GET", "POST"])
def delete_qso(qso_id):
    if request.method == "GET":
        qso = db.qso.get_by_id(qso_id)
        if qso is None:
            return ("Invalid QSO ID", 400)

        qsodata = json.loads(qso.get("payload_json"))

        return render_template(
            "delete.html",
            qso_id=qso_id,
            qso=qsodata,
        )

    elif request.method == "POST":
        post_qso = request.form.to_dict()

        if post_qso.get("qso_id") is not None:
            db.qso.delete(post_qso.get("qso_id"))
            db.job.delete_qso(post_qso.get("qso_id"))
            db.pota.delete(post_qso.get("qso_id"))

        if post_qso.get("__remove_qrz") == "on":
            logbook_id = qrz.get_qso_id(post_qso)

            if logbook_id is not None:
                qrz.delete_log_by_id(logbook_id)

        return redirect(url_for("index"))


# Lookup and QSL page
@app.route("/lookup/<callsign>", defaults={"stroke": None}, methods=["GET", "POST"])
@app.route("/lookup/<callsign>/<stroke>", methods=["GET", "POST"])
def lookup(callsign, stroke):
    callsign = callsign.upper()

    if stroke is not None:
        callsign = callsign + "/" + stroke

    qrz_info = get_qrz_info(callsign)
    qso_history = qrz.get_previous_qsos(callsign)

    if qso_history:
        for qso in qso_history:
            rawfreq = qso.get("FREQ")
            if rawfreq:
                qso["FREQ"] = format_mhz(rawfreq)

            card_path = card_path_from_adif(qso)

            if card_path is None:
                continue

            if os.path.isfile(card_path):
                qso["CARD_PATH"] = card_path


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
        qso_id=None,
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


# Lookup and QSL page
@app.route("/history/<callsign>", defaults={"stroke": None}, methods=["GET", "POST"])
@app.route("/history/<callsign>/<stroke>", methods=["GET", "POST"])
def history(callsign, stroke):
    callsign = callsign.upper()

    if stroke is not None:
        callsign = callsign + "/" + stroke

    qrz_info = get_qrz_info(callsign)
    qso_history = get_contact_history(callsign)

    return render_template(
        "history.html",
        qrz_info=qrz_info,
        callsign=callsign,
        qsos=qso_history
    )

@app.route("/edit/<qso_id>", methods=["GET"])
def edit_qso(qso_id):
    qso = db.qso.get_by_id(qso_id)
    if qso is None:
        return ("Invalid QSO ID", 400)

    qsodata = json.loads(qso.get("payload_json"))

    callsign = qsodata.get("With")
    qrz_info = expand_class(qrz.lookup(callsign))


    if qrz_info:
        q_call = qrz_info.get('callsign')
        q_country = qrz_info.get('country')
        q_state = qrz_info.get('state')

        if q_call is not None and q_country is not None:
            db.contact.tag.set(q_call, 'country', q_country)

            if q_state is not None:
                db.contact.tag.set(q_call, 'state', q_state)

    qso_history = qrz.get_previous_qsos(callsign)

    if qso_history:
        for qso in qso_history:
            rawfreq = qso.get("FREQ")
            if rawfreq:
                qso["FREQ"] = format_mhz(rawfreq)

    bands = get_config("Settings/Bands").split(",")
    quickband = get_config("Settings/QuickBand").split(",")
    quickmode = get_config("Settings/QuickMode").split(",")
    quickrsts = get_config("Settings/QuickRSTS").split(",")
    quickrstr = get_config("Settings/QuickRSTR").split(",")
    quickfreq = build_quick_freq(get_config("Settings/QuickFreq"))
    freqrange = build_freq_range(get_config("Settings/FreqRange"))

    return render_template(
        "lookup.html",
        qso_id=qso_id,
        qrz_info=qrz_info,
        bands=bands,
        quickband=quickband,
        quickmode=quickmode,
        quickrsts=quickrsts,
        quickrstr=quickrstr,
        quickfreq=quickfreq,
        freqrange=freqrange,
        qso_history=qso_history,
        qslInfo=qsodata
    )

@app.route("/qsl/choose", methods=["POST"])
def choose_qsl():
    qso = request.form.to_dict()

    thumbnail_check()
    backdrops = get_backdrop_images()

    old_qso = None
    old_qso_id = qso.get("__hidden_qso_id")

    if old_qso_id is not None:
        old_qso = json.loads(db.qso.get_by_id(old_qso_id).get("payload_json"))
        old_qso_qsl_status, old_qso_qrz_status = get_status_texts(old_qso_id)
        print(old_qso_id)
        print(old_qso_qsl_status)
        print(old_qso_qrz_status)
        if old_qso_qsl_status == "Sent":
            old_qso['qsl_sent'] = True

        if old_qso_qrz_status == "Logged":
            old_qso['qrz_logged'] = True

        if bool(get_config("Settings/EnablePota", False)):
            old_qso["pota_role"] = db.qso.tag.get(old_qso_id, 'pota_role')

            if old_qso.get('pota_role') is not None:
                parklist = db.qso.tag.get(old_qso_id, 'pota_parks')
                parkjson = json.loads(parklist)
                old_qso["pota_parks"] = ", ".join(parkjson)

    pota_enabled = bool(get_config("Settings/EnablePota", False))

    return render_template(
        "choose_qsl.html",
        qso=qso,
        old_qso=old_qso,
        backdrops=backdrops,
        pota_enabled=pota_enabled
    )


@app.route("/qsl/confirm", methods=["POST"])
def confirm_qsl():
    qso = request.form.to_dict()

    session["last_band"] = qso.get("Band")
    session["last_mode"] = qso.get("Mode")
    session["last_freq"] = qso.get("Freq")

    # extra values we need from the form, but must be
    # removed before the QSL card gets generated
    hidden_keys = get_keys(qso, 'hidden')

    # only used when updating an existing qso
    old_qso = get_keys(qso, 'oldqso')

    # deal with MyQSO / QRZ low band frequency discrepancy
    # I think most people would prefer 137KHz to be labeled as 
    # such, but QRZ expects 0.137MHz
    original_freq = qso.get('Freq')
    adjusted_freq = original_freq
    if hidden_keys['frequency_prefix'] == "KHz":
        adjusted_freq = str(float(adjusted_freq) / 1000.0)

    qso["Freq"] = original_freq + hidden_keys['frequency_prefix']

    # add qso to local database and get ID
    if hidden_keys.get("qso_id") is None:
        qso_id = db.qso.add(qso)
    else:
        qso_id = db.qso.edit(hidden_keys.get("qso_id"), qso)

    # if pota is enabled and qso is marked as pota, add to db
    if bool(get_config("Settings/EnablePota", False)):
        # editing pota data
        if old_qso and old_qso.get("pota_role") is not None:
            old_log_check = True
            new_log_check = bool(hidden_keys.get("log_pota"))

            if new_log_check == old_log_check:  # update existing log
                old_park_string = old_qso.get("pota_parks")
                new_park_string = hidden_keys.get("park_numbers")

                old_pota_role = old_qso.get("pota_role")
                new_pota_role = hidden_keys.get("pota_role")

                if new_park_string != old_park_string:
                    parks = new_park_string.split(",")
                    parks = [park.strip() for park in parks]
                    db.pota.set_parks(qso_id, parks)

                if new_pota_role != old_pota_role:
                    db.pota.set_role(qso_id, new_pota_role)

            else:  # remove from pota log
                db.pota.delete(qso_id)

        # new pota log
        elif hidden_keys.get("log_pota") == "yes":
            parks = []
            park_string = hidden_keys.get("park_numbers")
            role = hidden_keys.get("pota_role")

            db.pota.set_role(qso_id, role)

            if park_string is not None:
                parks = park_string.split(",")
                parks = [park.strip() for park in parks]
                db.pota.set_parks(qso_id, parks)

    # generate QSL card using selected background
    if hidden_keys.get("backdrop") != "none":
        db.job.add(qso_id, "QSL_GEN", {
            "backdrop": hidden_keys.get("backdrop"),
            "email": hidden_keys.get("email")
        })

    if hidden_keys.get('send_qsl') == "yes":
        db.job.add(qso_id, "QSL_SEND")

    # only fires when editing an existing QSO
    qso["Freq"] = adjusted_freq
    if hidden_keys.get('log_qso') == "yes":
        if old_qso is not None:
            log_id = qrz.get_qso_id(old_qso)
            qrz.delete_log_by_id(log_id)

        db.job.add(qso_id, "QRZ_LOG")

    flash("QSO processed successfully", "success")
    return redirect(url_for("index", callsign=qso["With"]))


@app.route("/API/v1", methods=["POST"])
def api():
    form = request.form.to_dict()

    if form.get("ACTION") == "get_status":
        item = form.get("ITEM")
        id = form.get("QSOID")

        if item not in ("QSL", "QRZ"):
            return ("Invalid item!", 400)

        if id is None:
            return ("Invalid QSO ID!", 400)

        if item == "QSL":
            return (
                qsl_status_text(
                    db.job.get_status(id, "QSL_GEN"),
                    db.job.get_status(id, "QSL_SEND")
                ),
                200
            )
        elif item == "QRZ":
            job_status = db.job.get_status(id, "QRZ_LOG")
            if job_status is None:
                return ("None", 200)

            return (qrz_status_text(job_status), 200)

    return ("Invalid request", 400)


if __name__ == "__main__":
    app.run(debug=True)
