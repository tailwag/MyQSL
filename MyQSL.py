####################################################################
# MyQSL             - Devin Shoemaker 2025 - devin@shoemaker.info  #
#                                                                  #
# This is the main app file. It will spawn a flask webserver for   #
# you to interact with from your browser.                          #
####################################################################

import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session

from MyQSL.CardGen import genCard
from MyQSL.O365_Send import sendMessage
from MyQSL.thumbnail import thumbnail_check
from MyQSL.QRZ import QRZClient, expand_class
from MyQSL.dbhandler import (
    add_qso,
    del_qso,
    update_qso,
    add_job,
    fetch_qsos,
    get_qso_by_id,
    get_job_status,
    pota_mark_qso,
    pota_add_parks,
    get_meta_tag,
    pota_edit_role,
    pota_edit_parks,
    pota_del_qso
)
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


def qsl_status_text(qsl_gen_status, qsl_send_status):
    if qsl_gen_status is None:
        return "None"

    if qsl_gen_status == "failed":
        return "Couldn't Generate Card"

    if qsl_gen_status in ("pending", "running"):
        return "Creating"

    if qsl_gen_status == "done":
        if qsl_send_status is None:
            return "Created"
        if qsl_send_status == "failed":
            return "Send Failed!"
        if qsl_send_status in ("pending", "running"):
            return "Sending…"
        if qsl_send_status == "done":
            return "Sent"

    return "Unknown"


def qrz_status_text(qrz_log_status):
    if qrz_log_status is None:
        return "None"

    if qrz_log_status == "failed":
        return "Failed"

    if qrz_log_status in ("pending", "running"):
        return "Uploading"

    if qrz_log_status == "done":
        return "Logged"


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

    qsos = fetch_qsos()

    qso_dicts = []

    for qso in qsos:
        qsl_gen_status = get_job_status(qso["id"], "QSL_GEN")
        qsl_send_status = get_job_status(qso["id"], "QSL_SEND")
        qrz_log_status = get_job_status(qso["id"], "QRZ_LOG")

        row = dict(qso)

        row["qsl_status"] = qsl_status_text(qsl_gen_status, qsl_send_status)
        row["qrz_status"] = qrz_status_text(qrz_log_status)

        qso_dicts.append(row) 

    return render_template(
        "index.html",
        qsolog=qso_dicts
    )


# delete a qso
@app.route("/delete/<qso_id>", methods=["GET", "POST"])
def delete_qso(qso_id):
    if request.method == "GET":
        qso = get_qso_by_id(qso_id)
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
            del_qso(post_qso.get("qso_id"))
            pota_del_qso(post_qso.get("qso_id"))

        if post_qso.get("__remove_qrz") == "on":
            print("remove qrz")
            logbook_id = qrz.get_qso_id(post_qso)

            if logbook_id is not None:
                print(logbook_id)
                qrz.delete_log_by_id(logbook_id)

        return redirect(url_for("index"))


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

@app.route("/edit/<qso_id>", methods=["GET"])
def edit_qso(qso_id):
    qso = get_qso_by_id(qso_id)
    if qso is None:
        return ("Invalid QSO ID", 400)

    qsodata = json.loads(qso.get("payload_json"))

    callsign = qsodata.get("With")
    qrz_info = expand_class(qrz.lookup(callsign))
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
        old_qso_dict = json.loads(get_qso_by_id(old_qso_id).get("payload_json"))

        if bool(get_config("Settings/EnablePota")):
            old_qso_dict["is_pota"] = bool(get_meta_tag(old_qso_id, 'is_pota'))

            if old_qso_dict.get("is_pota") is True:
                parklist = get_meta_tag(old_qso_id, 'pota_parks')
                parkjson = json.loads(parklist)
                old_qso_dict["pota_parks"] = ", ".join(parkjson)
                old_qso_dict["pota_role"] = get_meta_tag(old_qso_id, 'pota_parks')

        old_qso = old_qso_dict

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
    hidden_keys = {}
    for k, v in qso.items():
        if k[0:9] == "__hidden_":
            hidden_keys[k[9:]] = v

    for i in hidden_keys:
        del qso['__hidden_' + i]

    # only used when updating an existing qso
    old_qso = None
    if hidden_keys.get("qso_id") is not None:
        old_qso = {}
        for k, v in qso.items():
            if k[0:9] == "__oldqso_":
                old_qso[k[9:]] = v

        for i in old_qso:
            del qso['__oldqso_' + i]


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
        qso_id = add_qso(qso)
    else:
        qso_id = update_qso(hidden_keys.get("qso_id"), qso)

    # if pota is enabled and qso is marked as pota, add to db
    if bool(get_config("Settings/EnablePota", False)):
        if bool(hidden_keys.get("old_is_pota")) == True:
            print("test")
            print(bool("yes"))
            print("log checkbox")
            print(hidden_keys.get("old_is_pota"))
            print(hidden_keys.get("log_pota"))
            print("parks string")
            print(hidden_keys.get("old_pota_parks"))
            print(hidden_keys.get("park_numbers"))
            print("radio buttons")
            print(hidden_keys.get("old_pota_role"))
            print(hidden_keys.get("hunter_activator"))

            oldLogCheck = hidden_keys.get("old_is_pota")
            newLogCheck = bool(hidden_keys.get("log_pota"))

            if newLogCheck == oldLogCheck: # update existing log
                oldParkString = hidden_keys.get("old_pota_parks")
                newParkString = hidden_keys.get("park_numbers")
                oldPotaRole = hidden_keys.get("old_pota_role")
                newPotaRole = hidden_keys.get("hunter_activator")

                if newParkString != oldParkString:
                    pota_edit_parks(qso_id, newParkString)
                if newPotaRole != oldPotaRole:
                    pota_edit_role(qso_id, newPotaRole)

            else: # remove from pota log
                pota_del_qso(qso_id)

        if hidden_keys.get("log_pota") == "yes":
            parks = []
            park_string = hidden_keys.get("park_numbers")
            role = hidden_keys.get("hunter_activator")

            pota_mark_qso(qso_id, role)

            if park_string is not None:
                parks = park_string.split(",")
                parks = [park.strip() for park in parks]
                pota_add_parks(qso_id, parks)

    # generate QSL card using selected background
    if hidden_keys.get("backdrop") != "none":
        add_job(qso_id, "QSL_GEN", {
            "backdrop": hidden_keys.get("backdrop"),
            "email": hidden_keys.get("email")
        })

    if hidden_keys.get('send_qsl') == "yes":
        add_job(qso_id, "QSL_SEND")

    # only fires when editing an existing QSO
    qso["Freq"] = adjusted_freq
    if hidden_keys.get('log_qso') == "yes":
        if old_qso is not None:
            log_id = qrz.get_qso_id(old_qso)
            qrz.delete_log_by_id(log_id)

        add_job(qso_id, "QRZ_LOG")

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
                    get_job_status(id, "QSL_GEN"),
                    get_job_status(id, "QSL_SEND")
                ),
                200
            )
        elif item == "QRZ":
            job_status = get_job_status(id, "QRZ_LOG")
            if job_status is None:
                return ("None", 200)

            return (qrz_status_text(job_status), 200)

    return ("Invalid request", 400)


if __name__ == "__main__":
    app.run(debug=True)
