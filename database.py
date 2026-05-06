import sqlite3
from datetime import datetime

DB_PATH = "prospects.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS prospects (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                company      TEXT,
                email        TEXT UNIQUE,
                domain       TEXT,
                country      TEXT,
                source       TEXT,
                job_title    TEXT,
                job_url      TEXT,
                language     TEXT DEFAULT 'es',
                contacted    INTEGER DEFAULT 0,
                contact_date TEXT,
                notes        TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS email_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                prospect_id  INTEGER,
                sent_at      TEXT,
                subject      TEXT,
                status       TEXT,
                FOREIGN KEY(prospect_id) REFERENCES prospects(id)
            );
        """)


def upsert_prospect(company, email, domain, country, source, job_title="", job_url="", language="es"):
    """Inserta un prospect. Ignora si el email ya existe."""
    with get_conn() as conn:
        try:
            conn.execute(
                """INSERT INTO prospects (company, email, domain, country, source, job_title, job_url, language)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (company, email, domain, country, source, job_title, job_url, language),
            )
            return True
        except sqlite3.IntegrityError:
            return False


def get_pending_prospects(limit=30):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, company, email, country, language, job_title
               FROM prospects
               WHERE contacted=0
                 AND email NOT LIKE '%@placeholder'
                 AND email NOT LIKE 'noreply%'
                 AND email NOT LIKE 'no-reply%'
                 AND email NOT LIKE '%@odoo.com'
                 AND email NOT LIKE '%@example.com'
                 AND email NOT LIKE '%gserviceaccount%'
                 AND email NOT LIKE '%zhihu%'
               LIMIT ?""",
            (limit,),
        ).fetchall()
    return rows


def mark_contacted(prospect_id, subject, status="sent"):
    with get_conn() as conn:
        conn.execute(
            "UPDATE prospects SET contacted=1, contact_date=? WHERE id=?",
            (datetime.now().isoformat(), prospect_id),
        )
        conn.execute(
            "INSERT INTO email_log (prospect_id, sent_at, subject, status) VALUES (?, ?, ?, ?)",
            (prospect_id, datetime.now().isoformat(), subject, status),
        )


def stats():
    with get_conn() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
        contacted = conn.execute("SELECT COUNT(*) FROM prospects WHERE contacted=1").fetchone()[0]
        pending   = total - contacted
        by_source = conn.execute(
            "SELECT source, COUNT(*) FROM prospects GROUP BY source"
        ).fetchall()
    return {"total": total, "contacted": contacted, "pending": pending, "by_source": by_source}
