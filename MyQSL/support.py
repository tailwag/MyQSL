from MyQSL.QRZ import QRZClient, expand_class
from MyQSL.config import get_config
from MyQSL.dbhandler import Db

qrz = QRZClient()
db = Db(get_config("Settings/Database/DBPath"))

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
