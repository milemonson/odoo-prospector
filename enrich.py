"""
Enriquece prospects sin email:
1. Busca el dominio de cada empresa en DuckDuckGo
2. Intenta encontrar el email de contacto en ese dominio
3. Actualiza la base de datos
"""

import re
import time

from ddgs import DDGS
from scrapers.email_finder import find_email
import database as db

SKIP = {"linkedin.com", "indeed.com", "glassdoor.com", "arbeitnow.com",
        "remoteok.com", "facebook.com", "twitter.com", "youtube.com",
        "wikipedia.org", "adzuna.com", "xing.com", "kununu.com"}

# Intenta múltiples queries para encontrar el dominio
def _search_domain(company: str) -> str:
    queries = [
        f'"{company}" site oficial contacto',
        f'"{company}" odoo erp',
        f"{company} official website",
    ]
    try:
        with DDGS() as ddgs:
            for query in queries:
                results = list(ddgs.text(query, max_results=5))
                for r in results:
                    url = r.get("href", "")
                    domain = _extract_domain(url)
                    if domain and not any(s in domain for s in SKIP):
                        return domain
                time.sleep(0.5)
    except Exception as e:
        print(f"    [!] DDG error: {e}")
    return ""


def _extract_domain(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"https?://(?:www\.)?([^/?#]+)", str(url))
    return m.group(1) if m else ""


def run(limit: int = 50):
    db.init_db()

    conn = db.get_conn()
    rows = conn.execute(
        """SELECT id, company, domain FROM prospects
           WHERE email LIKE '%@placeholder' AND contacted=0
           LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()

    if not rows:
        print("No hay prospects sin email para enriquecer.")
        return

    print(f"\n[Enrich] Buscando emails para {len(rows)} empresas...\n")
    enriched = 0

    for prospect_id, company, existing_domain in rows:
        print(f"  → {company}")

        domain = existing_domain or _search_domain(company)

        if not domain:
            print(f"    [-] Sin dominio encontrado")
            time.sleep(1)
            continue

        print(f"    dominio: {domain}")
        email = find_email(domain)

        if not email:
            print(f"    [-] Sin email en {domain}")
            time.sleep(1)
            continue

        conn = db.get_conn()
        existing = conn.execute(
            "SELECT id FROM prospects WHERE email=?", (email,)
        ).fetchone()

        if existing:
            print(f"    [-] {email} ya existe")
        else:
            conn.execute(
                "UPDATE prospects SET email=?, domain=? WHERE id=?",
                (email, domain, prospect_id)
            )
            conn.commit()
            print(f"    [✓] {email}")
            enriched += 1
        conn.close()

        time.sleep(2)

    print(f"\n[Enrich] Finalizado. {enriched} prospects enriquecidos con email.\n")
