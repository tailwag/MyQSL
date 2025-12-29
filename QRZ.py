
import requests
import xml.etree.ElementTree as ET

NS = {"qrz": "http://xmldata.qrz.com"}

def load_qrz_credentials(path="qrz_credentials.xml"):
    tree = ET.parse(path)
    root = tree.getroot()

    creds = root.find("Credentials")
    if creds is None:
        raise RuntimeError("Missing <Credentials> block")

    callsign = creds.findtext("Callsign")
    password = creds.findtext("Password")

    if not callsign or not password:
        raise RuntimeError("QRZ credentials incomplete")

    return callsign.strip(), password.strip()

def qrz_login(username, password):
    url = "https://xmldata.qrz.com/xml/current/"
    params = {
        "username": username,
        "password": password
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()

    root = ET.fromstring(r.text)

    session = root.find("qrz:Session", NS)
    if session is None:
        # Helpful debug if this ever breaks again
        raise RuntimeError(f"No session element\n{r.text}")

    key = session.findtext("qrz:Key", default=None, namespaces=NS)
    error = session.findtext("qrz:Error", default=None, namespaces=NS)

    if error:
        raise RuntimeError(f"QRZ login error: {error}")

    return key


def qrz_lookup(session_key, callsign):
    url = "https://xmldata.qrz.com/xml/current/"
    params = {
        "s": session_key,
        "callsign": callsign
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()

    root = ET.fromstring(r.text)

    call = root.find("qrz:Callsign", NS)
    if call is None:
        return None

    return {
        "callsign": call.findtext("qrz:call", namespaces=NS),
        "fname": call.findtext("qrz:fname", namespaces=NS),
        "lname": call.findtext("qrz:name", namespaces=NS),
        "email": call.findtext("qrz:email", namespaces=NS),
        "qslmgr": call.findtext("qrz:qslmgr", namespaces=NS),
        "country": call.findtext("qrz:country", namespaces=NS),
    }


if __name__ == "__main__":
    user, pw = load_qrz_credentials()
    session_key = qrz_login(user, pw)
    data = qrz_lookup(session_key, "KD8VCP")
    print(data)
