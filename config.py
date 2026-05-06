import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS   = os.getenv("EMAIL_ADDRESS", "adminstracion@geconsas.com")
EMAIL_PASSWORD  = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER     = os.getenv("SMTP_SERVER", "mail.geconsas.com")
SMTP_PORT       = int(os.getenv("SMTP_PORT", "587"))
SENDER_NAME     = os.getenv("SENDER_NAME", "Gecons")

EMAILS_PER_DAY         = int(os.getenv("EMAILS_PER_DAY", "30"))
DELAY_BETWEEN_EMAILS   = int(os.getenv("DELAY_BETWEEN_EMAILS", "90"))

HUNTER_API_KEY     = os.getenv("HUNTER_API_KEY", "")
SEARCH_HOURS_OLD   = int(os.getenv("SEARCH_HOURS_OLD", "72"))
RESULTS_PER_SOURCE = int(os.getenv("RESULTS_PER_SOURCE", "50"))

KEYWORDS = [
    "odoo", "odoo developer", "odoo consultant", "odoo implementation",
    "odoo erp", "implementacion odoo", "consultor odoo",
]

INDUSTRY_KEYWORDS = [
    "retail", "pyme", "sme", "manufactura", "logistica",
    "ecommerce", "e-commerce", "partner", "distribuidor",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
