"""
Busca ofertas de trabajo relacionadas a Odoo usando APIs gratuitas.

Fuentes:
  - RemoteOK  → API pública, sin registro, trabajos remotos globales
  - Arbeitnow → API gratuita sin registro, empleos europeos
  - Adzuna    → API gratuita (requiere registro en developer.adzuna.com)
               Poner ADZUNA_APP_ID y ADZUNA_APP_KEY en .env para activarla.
"""

import os
import re
import time
import requests
from config import INDUSTRY_KEYWORDS, RESULTS_PER_SOURCE, HEADERS
from scrapers.email_finder import find_email
import database as db

ADZUNA_APP_ID  = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")

# Países de Adzuna disponibles (agrega o quita según interés)
ADZUNA_COUNTRIES = ["ar", "gb", "us", "au", "br", "ca", "de", "fr", "mx", "za"]

SPANISH_COUNTRIES = {
    "argentina", "mexico", "españa", "spain", "chile", "colombia",
    "peru", "venezuela", "uruguay", "ecuador", "ar", "mx", "es", "cl", "co",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_relevant(title: str, description: str = "", company: str = "") -> bool:
    text = f"{title} {description} {company}".lower()
    has_odoo     = "odoo" in text
    has_industry = any(kw in text for kw in INDUSTRY_KEYWORDS)
    return has_odoo  # industria es bonus, odoo es obligatorio

def _extract_domain(url: str) -> str:
    if not url:
        return ""
    m = re.search(r"https?://(?:www\.)?([^/?#]+)", str(url))
    return m.group(1) if m else ""

def _detect_language(country: str) -> str:
    return "es" if country.lower() in SPANISH_COUNTRIES else "en"

def _save_job(company, domain, country, job_title, job_url, source) -> bool:
    email = find_email(domain) if domain else None
    saved = db.upsert_prospect(
        company   = company,
        email     = email or f"__no_email__{re.sub(r'[^a-zA-Z0-9]', '_', company)}@placeholder",
        domain    = domain,
        country   = country,
        source    = source,
        job_title = job_title,
        job_url   = job_url,
        language  = _detect_language(country),
    )
    if saved:
        status = email if email else "(sin email aún)"
        print(f"    [+] {company} | {job_title} | {status}")
    return saved


# ─── RemoteOK ─────────────────────────────────────────────────────────────────

def scrape_remoteok() -> int:
    """API pública de RemoteOK — trabajos remotos globales."""
    print("\n[RemoteOK] Buscando trabajos Odoo...")
    added = 0
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers={**HEADERS, "Accept": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        jobs = resp.json()
    except Exception as e:
        print(f"  [!] Error RemoteOK: {e}")
        return 0

    for job in jobs:
        if not isinstance(job, dict):
            continue
        title    = job.get("position", "")
        company  = job.get("company", "")
        tags     = " ".join(job.get("tags", []))
        desc     = job.get("description", "")
        job_url  = job.get("url", "")
        location = job.get("location", "Remote")

        if not _is_relevant(title, f"{desc} {tags}", company):
            continue

        domain = _extract_domain(job.get("company_logo", ""))
        if not domain or "remoteok" in domain:
            domain = ""

        if _save_job(company, domain, location, title, job_url, "remoteok"):
            added += 1
        time.sleep(0.3)

    print(f"[RemoteOK] {added} prospects nuevos.\n")
    return added


# ─── Arbeitnow ────────────────────────────────────────────────────────────────

def scrape_arbeitnow() -> int:
    """API gratuita de Arbeitnow — empleos europeos + remotos."""
    print("\n[Arbeitnow] Buscando trabajos Odoo...")
    added = 0
    page  = 1

    while added < RESULTS_PER_SOURCE:
        try:
            resp = requests.get(
                "https://www.arbeitnow.com/api/job-board-api",
                params={"search": "odoo", "page": page},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  [!] Error Arbeitnow p{page}: {e}")
            break

        jobs = data.get("data", [])
        if not jobs:
            break

        for job in jobs:
            title   = job.get("title", "")
            company = job.get("company_name", "")
            desc    = job.get("description", "")
            job_url = job.get("url", "")
            country = "Europe"

            if not _is_relevant(title, desc, company):
                continue

            domain = _extract_domain(job.get("company_logo", ""))
            if not domain or "arbeitnow" in domain:
                domain = ""

            if _save_job(company, domain, country, title, job_url, "arbeitnow"):
                added += 1

        page += 1
        time.sleep(1)

    print(f"[Arbeitnow] {added} prospects nuevos.\n")
    return added


# ─── Adzuna ───────────────────────────────────────────────────────────────────

def scrape_adzuna() -> int:
    """API Adzuna — requiere ADZUNA_APP_ID y ADZUNA_APP_KEY en .env"""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        print("\n[Adzuna] Saltando — configura ADZUNA_APP_ID y ADZUNA_APP_KEY en .env")
        print("         Registro gratuito en: https://developer.adzuna.com/\n")
        return 0

    print(f"\n[Adzuna] Buscando en {len(ADZUNA_COUNTRIES)} países...")
    added = 0

    for country_code in ADZUNA_COUNTRIES:
        try:
            resp = requests.get(
                f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1",
                params={
                    "app_id":          ADZUNA_APP_ID,
                    "app_key":         ADZUNA_APP_KEY,
                    "what":            "odoo",
                    "results_per_page": 20,
                    "content-type":    "application/json",
                },
                timeout=15,
            )
            resp.raise_for_status()
            jobs = resp.json().get("results", [])
        except Exception as e:
            print(f"  [!] Adzuna {country_code}: {e}")
            continue

        for job in jobs:
            title   = job.get("title", "")
            company = job.get("company", {}).get("display_name", "")
            desc    = job.get("description", "")
            job_url = job.get("redirect_url", "")

            if not _is_relevant(title, desc, company):
                continue

            domain = ""
            if _save_job(company, domain, country_code.upper(), title, job_url, "adzuna"):
                added += 1

        time.sleep(1)

    print(f"[Adzuna] {added} prospects nuevos.\n")
    return added


# ─── Entry point ──────────────────────────────────────────────────────────────

def scrape_all_keywords() -> int:
    total  = scrape_remoteok()
    total += scrape_arbeitnow()
    total += scrape_adzuna()
    return total


def scrape(keyword: str = "odoo", location: str = "") -> int:
    return scrape_all_keywords()
