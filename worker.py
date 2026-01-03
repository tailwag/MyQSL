
import time
import json
import traceback

from MyQSL.dbhandler import (
    fetch_next_job,
    mark_job_done,
    mark_job_failed,
    get_qso_by_id,
    update_job_status,
    get_gen_job
)
from MyQSL.CardGen import genCard
from MyQSL.O365_Send import sendMessage
from MyQSL.QRZ import QRZClient
from MyQSL.config import get_config

qrz = QRZClient()

POLL_INTERVAL = 2  # seconds


def process_qsl_gen(job):
    qso = get_qso_by_id(job["qso_id"])
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

    update_job_status(job["id"], "done", payload_json=json.dumps(payload))    # enqueue SEND job


def process_qsl_send(job):
    qso_id = job["qso_id"]

    try:
        # Look for the completed QSL_GEN job for the same QSO
        gen_job = get_gen_job(qso_id)
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
        update_job_status(job["id"], "done")
        print(f"QSL_SEND completed for QSO {qso_id}")

    except Exception as e:
        update_job_status(job["id"], "failed", last_error=str(e))
        print(f"QSL_SEND failed for QSO {qso_id}: {e}")


def process_qrz_log(job):
    qso = get_qso_by_id(job["qso_id"])
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
        job = fetch_next_job()

        if not job:
            time.sleep(POLL_INTERVAL)
            continue

        try:
            handler = JOB_HANDLERS.get(job["job_type"])
            if not handler:
                raise ValueError(f"Unknown job type {job['job_type']}")

            handler(job)
            mark_job_done(job["id"])

        except Exception as e:
            traceback.print_exc()
            mark_job_failed(job["id"], str(e))


if __name__ == "__main__":
    worker_loop()
