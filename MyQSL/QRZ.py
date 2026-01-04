import re
import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from MyQSL.config import get_config

user_api = get_config("QRZ/UserAPI")
logbook_api = get_config("QRZ/LogbookAPI")

NS = {"qrz": "http://xmldata.qrz.com"}


class QRZClient:
    def __init__(self):
        self.session_key = None
        self.session_expiry = None
        self.username, self.password, self.apikey = self.load_credentials()

    def load_credentials(self):
        callsign = get_config(("QRZ/Credentials/Callsign"))
        password = get_config(("QRZ/Credentials/Password"))
        apikey = get_config(("QRZ/Credentials/APIKey"))

        return callsign.strip(), password.strip(), apikey.strip()

    def login(self):
        """Login to QRZ and store session key"""
        params = {"username": self.username, "password": self.password}
        r = requests.get(user_api, params=params, timeout=10)
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
        params = {"s": key, "callsign": callsign}
        r = requests.get(user_api, params=params, timeout=10)
        r.raise_for_status()

        root = ET.fromstring(r.text)
        call = root.find("qrz:Callsign", NS)
        if call is None:
            return None

        return {
            "image": call.findtext("qrz:image", namespaces=NS),
            "callsign": call.findtext("qrz:call", namespaces=NS),
            "class": call.findtext("qrz:class", namespaces=NS),
            "first_name": call.findtext("qrz:fname", namespaces=NS),
            "last_name": call.findtext("qrz:name", namespaces=NS),
            "email": call.findtext("qrz:email", namespaces=NS),
            "qslmgr": call.findtext("qrz:qslmgr", namespaces=NS),
            "country": call.findtext("qrz:country", namespaces=NS),
            "state": call.findtext("qrz:state", namespaces=NS),
            "grid": call.findtext("qrz:grid", namespaces=NS),
        }


    def __interface_lookup(self, payload):
        r = requests.post(
            logbook_api,
            auth=(self.username, self.password),
            data=payload,
            timeout=10
        )

        r.raise_for_status()

        text = html.unescape(r.text)

        # Optional sanity check
        if "RESULT=OK" not in text:
            return ""

        # Extract ADIF only
        match = re.search(r"ADIF=(.*)", text, re.S)
        if not match:
            return ""

        adif = match.group(1)

        return adif


    def get_qso_id(self, qso):
        callsign = self.username
        date = qso.get("Date")[:10]
        time = qso.get("Date")[11:15]

        options = {
            "CALL": qso.get("With"),
            "BETWEEN": date + "+" + date,
            "BAND": qso.get("Band").strip(),
            "MODE": qso.get("Mode").strip(),
        }

        option_string = ""
        for k, v in options.items():
            option_string = option_string + k + ":" + v + ","

        option_string = option_string[:-1]

        payload = {
            "KEY": self.apikey,
            "ACTION": "FETCH",
            "OPTION": option_string,
            "MAX": 5
        }

        adif = self.__interface_lookup(payload)

        for record in self.parse_adif_records(adif):
            if record.get("TIME_OFF") == time:
                return record.get("APP_QRZLOG_LOGID")

        return None

    def lookup_qso_history(self, callsign):
        callsign = callsign.strip().upper()

        payload = {
            "KEY": self.apikey,
            "ACTION": "FETCH",
            "OPTION": "CALL:"+callsign,
            "MAX": 5
        }

        adif = self.__interface_lookup(payload)

        return adif

    def delete_log_by_id(self, logbook_id):
        payload = {
            "KEY": self.apikey,
            "ACTION": "DELETE",
            "LOGIDS": logbook_id
        }

        r = requests.post(
            logbook_api,
            auth=(self.username, self.password),
            data=payload,
            timeout=10
        )

        r.raise_for_status()
        # QRZ returns a query string like: STATUS=OK&LOGID=12345
        response_text = r.text
        if "RESULT=OK" not in response_text:
            raise RuntimeError(f"QRZ rejected deletion: {response_text}")

        return response_text

    def parse_adif_records(self, adif_text):
        records = []

        # Split on <eor> (case-insensitive)
        for rec_text in re.split(r"<eor>", adif_text, flags=re.IGNORECASE):
            rec_text = rec_text.strip()
            if not rec_text:
                continue

            current = {}
            # match <FIELD:len>value
            for field, length, value in re.findall(r"<([^:>]+):(\d+)>([^<]+)", rec_text):
                current[field.upper()] = value[:int(length)]

            if current:
                records.append(current)

        return records

    def get_previous_qsos(self, callsign):
        raw = self.lookup_qso_history(callsign)
        return self.parse_adif_records(raw)

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
            self.adif_field("BAND", qso["Band"]),
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
        adif_data = self.build_adif_qso(qso)

        payload = {
            "KEY": self.apikey,
            "MYCALL": self.username,
            "ACTION": "INSERT",
            "ADIF": adif_data
        }

        r = requests.post(
            logbook_api,
            auth=(self.username, self.password),
            data=payload,
            timeout=10
        )

        r.raise_for_status()
        # QRZ returns a query string like: STATUS=OK&LOGID=12345
        response_text = r.text
        if "RESULT=OK" not in response_text:
            raise RuntimeError(f"QRZ rejected QSO: {response_text}")

        return response_text


def expand_class(qrz_info):
    if not qrz_info:
        return qrz_info

    country = qrz_info.get("country")
    if country != "United States":
        return qrz_info

    expanded_names = {
        "N": "Novice",
        "T": "Technician",
        "G": "General",
        "A": "Advanced",
        "E": "Extra"
    }

    for k, v in expanded_names.items():
        if k == qrz_info.get("class"):
            qrz_info["class"] = v
            break

    return qrz_info
