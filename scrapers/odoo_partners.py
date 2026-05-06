"""
Scrapea el directorio público de partners de Odoo.
URL: https://www.odoo.com/partners

Nota: si la página no devuelve resultados (JS rendering),
instalar: pip install selenium webdriver-manager
y descomentar la función _fetch_with_selenium().
"""

import time
import requests
from bs4 import BeautifulSoup
from config import HEADERS
from scrapers.email_finder import find_email
import database as db

BASE_URL = "https://www.odoo.com"
PARTNER_URL = "https://www.odoo.com/partners"

# Industrias objetivo — filtra partners que trabajen con estas industrias
TARGET_INDUSTRIES = ["retail", "manufacturing", "services", "distribution", "ecommerce"]


def _fetch_page(url: str, params: dict = None) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  [!] Error fetching {url}: {e}")
        return None


def _parse_partner_cards(soup: BeautifulSoup) -> list[dict]:
    partners = []
    # Odoo partner cards usan estas clases (pueden variar por versión del sitio)
    cards = soup.select("div.o_partner_card, article.o_website_partner, div[class*='partner']")

    for card in cards:
        name_el = card.select_one("h5, h4, .partner_name, strong")
        link_el = card.select_one("a[href*='/partners/']")
        country_el = card.select_one(".partner_country, [class*='country']")

        if not name_el:
            continue

        partners.append({
            "name": name_el.get_text(strip=True),
            "detail_url": BASE_URL + link_el["href"] if link_el and link_el.get("href", "").startswith("/") else "",
            "country": country_el.get_text(strip=True) if country_el else "Unknown",
        })

    return partners


def _get_partner_detail(detail_url: str) -> dict:
    """Extrae website y email de la página de detalle del partner."""
    info = {"website": "", "email": ""}
    if not detail_url:
        return info

    soup = _fetch_page(detail_url)
    if not soup:
        return info

    # Busca link externo (website del partner)
    for a in soup.select("a[href^='http']"):
        href = a["href"]
        if "odoo.com" not in href and "linkedin" not in href:
            info["website"] = href
            break

    # Busca email en la página
    import re
    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", soup.get_text())
    for e in emails:
        if "odoo.com" not in e and "sentry" not in e:
            info["email"] = e
            break

    return info


def scrape(max_pages: int = 5) -> int:
    """
    Scrapea el directorio de partners de Odoo.
    Retorna la cantidad de prospects nuevos agregados.
    """
    print("\n[Odoo Partners] Iniciando scraping...")
    added = 0

    for page in range(1, max_pages + 1):
        params = {"page": page} if page > 1 else {}
        soup = _fetch_page(PARTNER_URL, params)

        if not soup:
            break

        partners = _parse_partner_cards(soup)

        if not partners:
            print(f"  [!] Página {page}: sin resultados. El sitio puede requerir JS (ver nota en el archivo).")
            break

        print(f"  [+] Página {page}: {len(partners)} partners encontrados")

        for p in partners:
            detail = _get_partner_detail(p["detail_url"])
            domain = detail["website"]
            email  = detail["email"] or (find_email(domain) if domain else None)

            if not email:
                print(f"    [-] {p['name']}: sin email encontrado, guardando dominio")

            saved = db.upsert_prospect(
                company   = p["name"],
                email     = email or f"__no_email__{p['name'].replace(' ', '_')}@placeholder",
                domain    = domain,
                country   = p["country"],
                source    = "odoo_partners",
                language  = _detect_language(p["country"]),
            )
            if saved and email:
                added += 1
                print(f"    [+] {p['name']} ({p['country']}) — {email}")

            time.sleep(1)

        time.sleep(2)

    print(f"[Odoo Partners] Finalizado. {added} prospects nuevos agregados.\n")
    return added


def _detect_language(country: str) -> str:
    """Detecta si usar template en español o inglés según país."""
    spanish_countries = {
        "argentina", "mexico", "españa", "spain", "chile", "colombia",
        "peru", "venezuela", "uruguay", "ecuador", "bolivia", "paraguay",
        "costa rica", "panama", "guatemala", "honduras", "el salvador",
        "nicaragua", "cuba", "dominican republic", "puerto rico",
    }
    return "es" if country.lower() in spanish_countries else "en"
