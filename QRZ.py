import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

NS = {"qrz": "http://xmldata.qrz.com"}

class QRZClient:
    def __init__(self, config_path="config/qrz_config.xml"):
        self.config_path = config_path
        self.session_key = None
        self.session_expiry = None
        self.username, self.password, self.apikey = self.load_credentials()

    def load_credentials(self):
        tree = ET.parse(self.config_path)
        root = tree.getroot()

        creds = root.find("Credentials")
        if creds is None:
            raise RuntimeError("Missing <Credentials> block in QRZ config")

        callsign = creds.findtext("Callsign")
        password = creds.findtext("Password")
        apikey   = creds.findtext("APIKey")

        if not callsign or not password:
            raise RuntimeError("QRZ credentials incomplete")

        return callsign.strip(), password.strip(), apikey.strip()

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

    def adif_field(self, name, value):
        """Return an ADIF field with correct length."""
        value = str(value)
        return f"<{name}:{len(value)}>{value}"

    def build_adif_qso(self, qso):
        """Build a valid ADIF string from the QSO dictionary."""
        # Convert date/time to UTC if needed
        date_str = qso["Date"]  # e.g. '2025-12-29 2226 UTC'

        # Remove the ' UTC' suffix if present
        if date_str.endswith(" UTC"):
            date_str = date_str[:-4]

        # Parse as naive datetime
        dt_naive = datetime.strptime(date_str, "%Y-%m-%d %H%M")

        # Convert to UTC-aware datetime
        dt_utc = dt_naive.replace(tzinfo=timezone.utc)

        qso_date = dt_utc.strftime("%Y%m%d")
        time_on = dt_utc.strftime("%H%M")

        adif_lines = [
            "<ADIF_VER:5>3.1.0",
            "<PROGRAMID:6>MyQSL",
            "<PROGRAMVERSION:3>1.0",
            "<EOH>",
            self.adif_field("CALL", qso["With"]),
            self.adif_field("QSO_DATE", qso_date),
            self.adif_field("TIME_ON", time_on),
            self.adif_field("BAND", qso["Band"].upper()),
            self.adif_field("MODE", qso["Mode"].upper()),
            self.adif_field("STATION_CALLSIGN", self.username),
            self.adif_field("OPERATOR", self.username),
            self.adif_field("RST_SENT", qso.get("RSTS", "")),
            self.adif_field("RST_RCVD", qso.get("RSTR", "")),
            self.adif_field("FREQ", qso.get("Freq", "").replace("MHz", "")),
            "<EOR>"
        ]
        return "\n".join(adif_lines)

    def log_qso(self, qso):
        url = "https://logbook.qrz.com/api"

        adif_data = self.build_adif_qso(qso)

        payload = {
            "KEY": self.apikey,
            "MYCALL": self.username,
            "ACTION": "INSERT",
            "ADIF": adif_data
        }

        r = requests.post(
            url,
            auth=(self.username, self.password),
            data=payload,
            timeout=10
        )

        r.raise_for_status()
        # QRZ returns a query string like: STATUS=OK&LOGID=12345
        response_text = r.text
        if "RESULT=OK" not in response_text:
            raise RuntimeError(f"QRZ rejected QSO: {response_text}")

        print("QRZ log successful:", response_text)
        return response_text
