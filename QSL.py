from CardGen import genCard
from qrz_client import QRZClient
from flask import Flask, render_template, request, jsonify, redirect, url_for

qrz=QRZClient()

app = Flask(__name__)


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
    qslInfo = {}

    qslInfo["With"] = callsign

    return render_template(
        "lookup.html",
        qrz_info=qrz_info,
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

    return render_template("preview.html",
                           card_path=card_path,
                           email=email,
                           form_data=form_data)

@app.route("/send_qsl", methods=["POST"])
def send_qsl():
    form_data = request.form.to_dict()
    email = form_data.get("email")
    card_path = form_data.get("card_path")  # or store path somewhere

    # O365 account setup
    credentials = ("client_id", "client_secret")
    account = Account(credentials, auth_flow_type='credentials')
    if not account.is_authenticated:
        account.authenticate()

    m = account.new_message()
    m.to.add(email)
    m.subject = f"QSL Card for {form_data.get('callsign')}"
    m.body = "Here is your QSL card."
    m.attachments.add(card_path)
    m.send()

    return f"QSL card sent to {email}!"

if __name__ == "__main__":
    app.run(debug=True)
