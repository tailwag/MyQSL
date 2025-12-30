import os
from CardGen import genCard
from QRZ import QRZClient
from O365_Send import sendMessage
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from O365 import Account

qrz=QRZClient()

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

# Lookup and QSL page
@app.route("/lookup/<callsign>", methods=["GET", "POST"])
def lookup(callsign):
    callsign = callsign.upper()

    qrz_info = qrz.lookup(callsign)
    qso_history = qrz.get_previous_qsos(callsign)

    qslInfo = {}

    qslInfo["With"] = callsign

    return render_template(
        "lookup.html",
        qrz_info=qrz_info,
        qso_history=qso_history,
        qslInfo=qslInfo
    )

@app.route("/generate_qsl", methods=["POST"])
def generate_qsl():
    # Get form data
    form_data = request.form.to_dict()
    callsign = form_data.get("With").upper()

    # Lookup email from QRZ
    qrz_info = qrz.lookup(callsign)
    email = qrz_info.get("email") if qrz_info else None

    # Generate QSL card (returns file path or URL to image)
    card_path = genCard(form_data)
    print("cardddddd: " + card_path)

    return render_template("preview.html",
                           card_path=card_path,
                           email=email,
                           form_data=form_data)

@app.route("/send_qsl", methods=["POST"])
def send_qsl():
    form_data = request.form.to_dict()

    send_qsl_card = form_data.get("send_qsl") == "yes"
    log_qso = form_data.get("log_qso") == "yes"

    email = form_data.get("email")
    card_path = form_data.get("card_path")  # or store path somewhere

    if send_qsl_card:
        sendMessage(
            email,
            "QSL card from KD8VCP",
            "It was a pleasure connecting with you earlier. Please find the attached card. 73!",
            card_path
        )

    if log_qso:
        qrz.log_qso(form_data)

    actions = []
    if send_qsl_card:
        actions.append("QSL sent")
    if log_qso:
        actions.append("QSO logged")

    flash(f"{' & '.join(actions)} for {form_data['With']}", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
