import os
from MyQSL.QRZ import QRZClient
from MyQSL.config import get_config
from MyQSL.dbhandler import Db

qrz = QRZClient()
db = Db(get_config("Settings/Database/DBPath"))

######################################################################
# Support functions                                                  #
######################################################################
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


def get_status_texts(qso_id):
    qsl_gen_status  = db.job.get_status(qso_id, "QSL_GEN")
    qsl_send_status = db.job.get_status(qso_id, "QSL_SEND")
    qrz_log_status  = db.job.get_status(qso_id, "QRZ_LOG")

    qsl_status = qsl_status_text(qsl_gen_status, qsl_send_status)
    qrz_status = qrz_status_text(qrz_log_status)

    return qsl_status, qrz_status


def get_keys(main_dict, prefix):
    new_dict = None
    full_prefix = "__" + prefix + "_"
    prefix_length = len(full_prefix)  # __ and _ is 3
    for k, v in main_dict.items():
        if k[0:prefix_length] == full_prefix:
            if new_dict is None:
                new_dict = {}

            new_dict[k[prefix_length:]] = v

    if new_dict is not None:
        for i in new_dict:
            del main_dict[full_prefix + i]

    return new_dict


def card_path_from_adif(qso):
    # CALL
    # QSO_DATE 20260101
    # TIME_ON
    call = qso.get("CALL")
    date = qso.get("QSO_DATE")
    time = qso.get("TIME_ON")

    if call is None or date is None or time is None:
        return None

    date = str(date)
    time = str(time)
    date = date[:4] + "-" + date[4:6] + "-" + date[6:8]

    card_name = "qslcard_" + call + "_" + date + "_" + time + "_UTC.jpg"

    return 'static/img/' + card_name


def get_qrz_info(callsign):
    qrz_info = expand_class(qrz.lookup(callsign))

    if qrz_info:
        q_call = qrz_info.get('callsign')
        q_country = qrz_info.get('country')
        q_state = qrz_info.get('state')

        if q_call is not None and q_country is not None:
            db.contact.tag.set(q_call, 'country', q_country)

            if q_state is not None:
                db.contact.tag.set(q_call, 'state', q_state)

    return qrz_info

def qsl_card_filename(qso):
    date = f"{qso['qso_date'][:4]}-{qso['qso_date'][4:6]}-{qso['qso_date'][6:]}"
    time = qso["time_on"]
    callsign = qso["callsign"].upper()

    return f"qslcard_{callsign}_{date}_{time}_UTC.jpg"

def attach_qsl_card(qso):
    qsl_img_dir = get_config("Settings/QSLCard/CardOutput")
    filename = qsl_card_filename(qso)
    full_path = os.path.join(qsl_img_dir, filename)

    if os.path.isfile(full_path):
        qso["qsl_card"] = {
            "exists": True,
            "filename": filename,
            "url": f"/static/img/{filename}",
        }
    else:
        qso["qsl_card"] = {
            "exists": False,
            "filename": filename,
            "url": None,
        }

def normalize_qrz_qso(qso):
    return {
        "source": "qrz",
        "callsign": qso.get("CALL"),
        "qso_date": qso.get("QSO_DATE"),          # YYYYMMDD
        "time_on": qso.get("TIME_ON"),            # HHMM
        "band": qso.get("BAND"),
        "mode": qso.get("MODE"),
        "freq": normalize_freq(qso.get("FREQ")),
        "rsts": qso.get("RST_SENT"),
        "rstr": qso.get("RST_RCVD"),
        "raw": qso,
    }

def normalize_local_qso(qso):
    return {
        "source": "local",
        "id": qso.get("id"),
        "callsign": qso.get("callsign"),
        "qso_date": qso.get("qso_date").replace("-", ""),  # YYYYMMDD
        "time_on": qso.get("time_on").split()[0],          # HHMM
        "band": qso.get("band"),
        "mode": qso.get("mode"),
        "freq": normalize_freq(qso.get("freq")),
        "rsts": qso.get("rsts"),
        "rstr": qso.get("rstr"),
        "created_at": qso.get("created_at"),
        "raw": qso,
    }

def qso_key(qso):
    return (
        qso["callsign"],
        qso["qso_date"],
        qso["time_on"],
        qso["band"],
        qso["mode"],
        qso["freq"],
    )

def normalize_freq(freq):
    if freq is None:
        return None

    freq = str(freq).lower().replace("mhz", "").strip()
    try:
        return round(float(freq), 3)
    except ValueError:
        return None


def get_contact_history(callsign):
    qrz_history = qrz.get_previous_qsos(callsign)
    local_history = db.contact.get_history(callsign)

    normalized_qrz = [normalize_qrz_qso(q) for q in qrz_history]
    normalized_local = [normalize_local_qso(q) for q in local_history]

    qrz_map = {qso_key(q): q for q in normalized_qrz}
    local_map = {qso_key(q): q for q in normalized_local}

    all_keys = set(qrz_map) | set(local_map)
    merged_history = []

    for key in sorted(all_keys):
        qrz_qso = qrz_map.get(key)
        local_qso = local_map.get(key)

        merged_history.append({
            "key": key,
            "callsign": key[0],
            "qso_date": key[1],
            "time_on": key[2],
            "band": key[3],
            "mode": key[4],
            "freq": key[5],

            "qrz": qrz_qso,
            "local": local_qso,

            "flags": {
                "in_qrz": qrz_qso is not None,
                "in_local": local_qso is not None,
                "qrz_only": qrz_qso is not None and local_qso is None,
                "local_only": local_qso is not None and qrz_qso is None,
                "matched": qrz_qso is not None and local_qso is not None,
            }
        })

    for qso in merged_history:
        attach_qsl_card(qso)

    return merged_history











