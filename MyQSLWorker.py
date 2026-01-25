import time
import json
import traceback

from MyQSL.CardGen import genCard
from MyQSL.O365_Send import sendMessage
from MyQSL.QRZ import QRZClient
from MyQSL.config import get_config
from MyQSL.dbhandler import Db

qrz = QRZClient()
db = Db(get_config("Settings/Database/DBPath"))

POLL_INTERVAL = 2  # seconds

def process_qsl_gen(job):
    qso = db.qso.get_by_id(job["qso_id"])
    payload = json.loads(job["payload_json"])
    qslinfo = json.loads(qso["payload_json"])

    backdrop = payload.get("backdrop")
    email = payload.get("email")

    if not backdrop or backdrop == "none":
        raise ValueError("Backdrop missing for QSL_GEN")

    payload["qsl_path"] = genCard(
        qslinfo,
        get_config("Settings/QSLCard/BackdropPath") + backdrop
    )

    db.job.set_status(job["id"], "done", payload_json=json.dumps(payload))    # enqueue SEND job


def process_qsl_send(job):
    qso_id = job["qso_id"]

    try:
        # Look for the completed QSL_GEN job for the same QSO
        gen_job = db.job.get_gen(qso_id)
        if not gen_job:
            # Card not ready yet, skip
            print(f"No generated card yet for QSO {qso_id}, will retry")
            return

        payload = json.loads(gen_job["payload_json"])
        qsl_path = payload.get("qsl_path")
        email = payload.get("email")

        if not qsl_path or not email:
            raise ValueError("Missing card path or email for sending")

        # Send the card
        sendMessage(
            email,
            get_config("Settings/QSLCard/EmailSubject"),
            get_config("Settings/QSLCard/EmailBody"),
            qsl_path
        )

        # Update job as done
        db.job.set_status(job["id"], "done")
        print(f"QSL_SEND completed for QSO {qso_id}")

    except Exception as e:
        db.job.set_status(job["id"], "failed", last_error=str(e))
        print(f"QSL_SEND failed for QSO {qso_id}: {str(e)}")


def process_qrz_log(job):
    qso = db.qso.get_by_id(job["qso_id"])
    payload = json.loads(qso["payload_json"])

    qrz.log_qso(payload)


JOB_HANDLERS = {
    "QSL_GEN": process_qsl_gen,
    "QSL_SEND": process_qsl_send,
    "QRZ_LOG": process_qrz_log,
}


def worker_loop():
    print("MyQSL worker started")

    while True:
        job = db.job.get_next()

        if not job:
            time.sleep(POLL_INTERVAL)
            continue

        try:
            handler = JOB_HANDLERS.get(job["job_type"])
            if not handler:
                raise ValueError(f"Unknown job type {job['job_type']}")

            handler(job)
            db.job.mark_done(job["id"])

        except Exception as e:
            traceback.print_exc()
            db.job.mark_failed(job["id"], str(e))


if __name__ == "__main__":
    worker_loop()
