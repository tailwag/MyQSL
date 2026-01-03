import os
import json
import sqlite3
from MyQSL.config import get_config

db_path = get_config("Settings/Database/DBPath")

def init_db(db_path=db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS qso_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        callsign TEXT NOT NULL,
        qso_date TEXT NOT NULL,
        time_on TEXT NOT NULL,
        band TEXT,
        mode TEXT,
        freq TEXT,
        rsts TEXT,
        rstr TEXT,
        qsl_requested INTEGER NOT NULL DEFAULT 0,
        qsl_generated INTEGER NOT NULL DEFAULT 0,
        qsl_sent INTEGER NOT NULL DEFAULT 0,
        qsl_backdrop TEXT,
        qsl_path TEXT,
        qsl_email TEXT,
        qrz_status TEXT NOT NULL DEFAULT 'Pending',
        qrz_error TEXT,
        payload_json TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        qsl_sent_at DATETIME,
        qrz_logged_at DATETIME
    );
    """)

    conn.commit()
    conn.close()


if not os.path.isfile(db_path):
    init_db()


def add_to_queue(qso):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print(qso)
    cur.execute(
        """
        INSERT INTO qso_queue (
            callsign, qso_date, time_on, band, mode,
            freq, rsts, rstr, qsl_email, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            qso["With"],
            qso["Date"][0:10],
            qso["Date"][10:],
            qso["Band"],
            qso["Mode"],
            qso["Freq"],
            qso["RSTS"],
            qso["RSTR"],
            qso.get("email"),
            json.dumps(qso),
        )
    )
    conn.commit()
    conn.close()


def fetch_qsos():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    ret = cur.execute(
        """
        SELECT * FROM qso_queue ORDER BY created_at DESC
        """
    ).fetchall()

    conn.close()
    return ret
