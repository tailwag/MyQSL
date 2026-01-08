import os
import json
import sqlite3
from MyQSL.config import get_config

db_path = get_config("Settings/Database/DBPath")

def init_db(db_path=db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS qsos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        callsign TEXT NOT NULL,
        qso_date TEXT NOT NULL,
        time_on TEXT NOT NULL,
        band TEXT,
        mode TEXT,
        freq TEXT,
        rsts TEXT,
        rstr TEXT,
        payload_json TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        qso_id INTEGER NOT NULL,
        job_type TEXT NOT NULL, -- 'QSL_GEN', 'QSL_SEND', 'QRZ_LOG'
        status TEXT NOT NULL DEFAULT 'pending', -- pending, running, done, failed
        attempts INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 5,
        last_error TEXT,
        payload_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,

        FOREIGN KEY (qso_id) REFERENCES qsos(id)
    );
    CREATE TABLE IF NOT EXISTS qso_meta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        qso_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME,

        FOREIGN KEY (qso_id) REFERENCES qsos(id)
    );
    CREATE TABLE IF NOT EXISTS system_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        last_error TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME
    );
    """)

    conn.commit()
    conn.close()



def add_qso(qso):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO qsos (
            callsign, qso_date, time_on, band, mode,
            freq, rsts, rstr, payload_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            qso["With"],
            qso["Date"][:10],
            qso["Date"][11:],
            qso.get("Band"),
            qso.get("Mode"),
            qso.get("Freq"),
            qso.get("RSTS"),
            qso.get("RSTR"),
            json.dumps(qso),
        )
    )

    qso_id = cur.lastrowid
    conn.commit()
    conn.close()
    return qso_id


def del_qso(qso_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM qsos WHERE id = ?
        """,
        (
            qso_id,
        )
    )

    conn.commit()
    conn.close()


def update_qso(qso_id, qso):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE qsos SET
            callsign=?, qso_date=?, time_on=?, band=?,
            mode=?, freq=?, rsts=?, rstr=?, payload_json=?
        WHERE id IS ?
        """,
        (
            qso["With"],
            qso["Date"][:10],
            qso["Date"][11:],
            qso.get("Band"),
            qso.get("Mode"),
            qso.get("Freq"),
            qso.get("RSTS"),
            qso.get("RSTR"),
            json.dumps(qso),
            qso_id,
        )
    )

    conn.commit()
    conn.close()
    return qso_id


def add_job(qso_id, job_type, payload=None):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO jobs (
            qso_id, job_type, payload_json
        )
        VALUES (?, ?, ?)
        """,
        (
            qso_id,
            job_type,
            json.dumps(payload) if payload else None
        )
    )

    conn.commit()
    conn.close()


def fetch_qsos():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    history = get_config("Settings/QSOHistory")

    rows = cur.execute(
        "SELECT * FROM qsos ORDER BY created_at DESC LIMIT ?",
        (history,)
    ).fetchall()

    rows = [dict(row) for row in rows]

    conn.close()
    return rows


def fetch_next_job():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    job = cur.execute(
        """
        SELECT * FROM jobs
        WHERE status = 'pending'
        ORDER BY created_at
        LIMIT 1
        """
    ).fetchone()

    if not job:
        conn.close()
        return None

    cur.execute(
        """
        UPDATE jobs
        SET status='running', attempts=attempts+1, updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND status='pending'
        """,
        (job["id"],)
    )

    if cur.rowcount == 0:
        conn.close()
        return None

    conn.commit()
    conn.close()
    return dict(job)


def get_qso_by_id(qso_id):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute(
        "SELECT * FROM qsos WHERE id=?",
        (qso_id,)
    ).fetchone()

    conn.close()
    return dict(row)


def mark_job_done(job_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status='done', updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (job_id,)
    )

    conn.commit()
    conn.close()


def mark_job_failed(job_id, error):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE jobs
        SET status='failed',
            last_error=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (error[:500], job_id)
    )

    conn.commit()
    conn.close()


def update_job_status(job_id, status, last_error=None, payload_json=None):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        UPDATE jobs
        SET status=?, last_error=?, payload_json=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (status, last_error, payload_json, job_id))
    conn.commit()
    conn.close()


def get_job_status(qso_id, job_type):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    row = cur.execute(
        "SELECT status FROM jobs WHERE qso_id=? AND job_type=? ORDER BY created_at DESC",
        (qso_id, job_type)
    ).fetchone()

    return row["status"] if row else None


def get_gen_job(qso_id):
    gen_job = None
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM jobs
        WHERE qso_id=? AND job_type='QSL_GEN' AND status='done'
        ORDER BY created_at DESC
        LIMIT 1
    """, (qso_id,))
    gen_job = cur.fetchone()
    conn.close()
    return gen_job

def new_meta_tag(qso_id, key, value):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO qso_meta (qso_id, key, value)
        VALUES (?, ?, ?)
        """,
        (
            qso_id,
            key,
            value
        )
    )
    conn.commit()
    conn.close()


def edit_meta_tag(qso_id, key, value):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute (
        """
        UPDATE qso_meta SET value=?
        WHERE qso_id=? AND key=?
        """,
        (
            value,
            qso_id, 
            key
        )
    )

    conn.commit()
    conn.close()


def get_meta_tag(qso_id, key):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT value FROM qso_meta WHERE qso_id IS ? AND key IS ?
        """,
        (
            qso_id,
            key
        )
    )
    result = cur.fetchone()

    conn.close()
    if result is None:
        return None

    return result[0]


def del_meta_tag(qso_id, key):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM qso_meta WHERE qso_id IS ? AND key IS ?
        """,
        (
            qso_id,
            key,
        )
    )

    conn.commit()
    conn.close()


def pota_mark_qso(qso_id, role):
    new_meta_tag(qso_id, 'pota_role', role)


def pota_edit_role(qso_id, role):
    if qso_id is not None and role is not None:
        edit_meta_tag(qso_id, 'pota_role', role.strip())


def pota_del_qso(qso_id):
    if qso_id is not None:
        for key in ['is_pota', 'pota_role', 'pota_parks']:
            del_meta_tag(qso_id, key)


def pota_add_parks(qso_id, parks):
    if qso_id is not None and parks is not None:
        parks_string = json.dumps(parks)
        new_meta_tag(qso_id, 'pota_parks', parks_string)


def pota_edit_parks(qso_id, parks):
    if qso_id is not None and parks is not None:
        parks_string = json.dumps(parks)
        edit_meta_tag(qso_id, 'pota_parks', parks_string)


init_db()
