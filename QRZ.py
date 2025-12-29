import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

NS = {"qrz": "http://xmldata.qrz.com"}

class QRZClient:
    def __init__(self, config_path="config/qrz_config.xml"):
        self.config_path = config_path
        self.session_key = None
        self.session_expiry = None
        self.username, self.password = self.load_credentials()

    def load_credentials(self):
        tree = ET.parse(self.config_path)
        root = tree.getroot()

        creds = root.find("Credentials")
        if creds is None:
            raise RuntimeError("Missing <Credentials> block in QRZ config")

        callsign = creds.findtext("Callsign")
        password = creds.findtext("Password")

        if not callsign or not password:
            raise RuntimeError("QRZ credentials incomplete")

        return callsign.strip(), password.strip()

    def login(self):
        """Login to QRZ and store session key"""
        url = "https://xmldata.qrz.com/xml/current/"
        params = {"username": self.username, "password": self.password}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()

        root = ET.fromstring(r.text)
        session = root.find("qrz:Session", NS)
        if session is None:
            raise RuntimeError(f"No session element in QRZ response:\n{r.text}")

        key = session.findtext("qrz:Key", namespaces=NS)
        error = session.findtext("qrz:Error", namespaces=NS)
        if error:
            raise RuntimeError(f"QRZ login error: {error}")

        self.session_key = key
        # Optional: set a conservative expiry 1 hour from now
        self.session_expiry = datetime.utcnow() + timedelta(hours=1)
        return key

    def get_session_key(self):
        """Return a valid session key, login if expired"""
        if self.session_key is None or datetime.utcnow() >= self.session_expiry:
            return self.login()
        return self.session_key

    def lookup(self, callsign):
        key = self.get_session_key()
        url = "https://xmldata.qrz.com/xml/current/"
        params = {"s": key, "callsign": callsign}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()

        root = ET.fromstring(r.text)
        call = root.find("qrz:Callsign", NS)
        if call is None:
            return None

        return {
            "callsign": call.findtext("qrz:call", namespaces=NS),
            "first_name": call.findtext("qrz:fname", namespaces=NS),
            "last_name": call.findtext("qrz:name", namespaces=NS),
            "email": call.findtext("qrz:email", namespaces=NS),
            "qslmgr": call.findtext("qrz:qslmgr", namespaces=NS),
            "country": call.findtext("qrz:country", namespaces=NS),
        }

