"""
Busca emails de contacto a partir de un dominio.
1. Primero intenta Hunter.io API (si hay API key).
2. Fallback: scrapea la página /contact del dominio.
"""

import re
import requests
from config import HUNTER_API_KEY, HEADERS

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".ico", ".webp", ".woff"}
CONTACT_PATHS   = ["/contact", "/contacto", "/about", "/about-us", "/company", "/"]

# Dominios o patrones de email que nunca son contactos reales
BAD_DOMAINS = {
    "odoo.com", "example.com", "sentry.io", "w3.org",
    "zhihu.com", "gserviceaccount.com", "googlemail.com",
    "githubusercontent.com", "amazonaws.com", "shopify.com",
    "wixsite.com", "squarespace.com",
}
BAD_PREFIXES = {"noreply", "no-reply", "donotreply", "do-not-reply",
                "bounce", "mailer-daemon", "postmaster", "unsubscribe",
                "admin@odoo", "info@odoo", "design@odoo"}
BAD_PATTERN = re.compile(r"^[a-f0-9]{10,}@")   # hashes hexadecimales


def is_valid_email(email: str) -> bool:
    e = email.lower()
    # Extensiones de archivo como dominio
    if any(e.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    # Dominio bloqueado
    domain_part = e.split("@")[-1] if "@" in e else ""
    if any(bad in domain_part for bad in BAD_DOMAINS):
        return False
    # Prefijos de no-reply / bounces
    if any(e.startswith(p) for p in BAD_PREFIXES):
        return False
    # Hash hexadecimal como usuario
    if BAD_PATTERN.match(e):
        return False
    # Debe tener un TLD razonable (no .webp, .png, etc.)
    tld = domain_part.rsplit(".", 1)[-1] if "." in domain_part else ""
    if len(tld) > 6 or len(tld) < 2:
        return False
    return True


def find_email_hunter(domain: str) -> str | None:
    if not HUNTER_API_KEY or not domain:
        return None
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY},
            timeout=10,
        )
        data = resp.json().get("data", {})
        emails = data.get("emails", [])
        for e in emails:
            val = e.get("value", "")
            if is_valid_email(val):
                if e.get("type") == "generic":
                    return val
        for e in emails:
            val = e.get("value", "")
            if is_valid_email(val):
                return val
    except Exception:
        pass
    return None


def find_email_scrape(domain: str) -> str | None:
    if not domain:
        return None
    base = domain.rstrip("/")
    if not base.startswith("http"):
        base = "https://" + base

    for path in CONTACT_PATHS:
        try:
            resp = requests.get(base + path, headers=HEADERS, timeout=8, allow_redirects=True)
            found = EMAIL_RE.findall(resp.text)
            for email in found:
                if is_valid_email(email):
                    return email
        except Exception:
            continue
    return None


def find_email(domain: str) -> str | None:
    email = find_email_hunter(domain)
    if not email:
        email = find_email_scrape(domain)
    return email
