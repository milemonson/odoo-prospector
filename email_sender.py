"""
Envía emails HTML personalizados via SMTP.
Respeta el límite diario y el delay entre envíos.
"""

import os
import ssl
import uuid
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid
from datetime import datetime

from config import (
    EMAIL_ADDRESS, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT,
    SENDER_NAME, EMAILS_PER_DAY, DELAY_BETWEEN_EMAILS,
)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Nombre de persona real en el FROM — reduce spam score
SENDER_FULL_NAME = "Milena de Gecons"


def _load_template(language: str) -> str:
    lang = language if language in ("es", "en") else "es"
    path = os.path.join(TEMPLATES_DIR, f"email_{lang}.html")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _plain_text(language: str, company: str, job_title: str = "") -> str:
    """Versión texto plano del email — obligatorio para evitar spam."""
    if language == "es":
        job_ctx = f"Vi que están buscando '{job_title}', lo que me indica que Odoo es clave en su operación.\n\n" if job_title else ""
        return f"""Hola, equipo de {company}:

Me comunico desde Gecons, consultora especializada en Odoo ERP.

{job_ctx}Trabajamos con empresas de retail, manufactura, logística y pymes ofreciendo:

- Implementación y parametrización de Odoo
- Módulos e integraciones a medida (APIs, marketplaces, couriers)
- Migraciones entre versiones
- Reportes financieros y dashboards
- Soporte y mantenimiento continuo

¿Tienen algún proyecto Odoo en curso o planificado? Me encantaría conocer sus necesidades.

Más información: https://geconsas.com

Saludos,
Milena
Gecons – Consultoría & Soluciones Informáticas
administracion@geconsas.com | geconsas.com

---
Si no desea recibir más emails, responda con BAJA en el asunto.
"""
    else:
        job_ctx = f"I noticed you're looking for '{job_title}', which tells me Odoo is central to your operations.\n\n" if job_title else ""
        return f"""Hello {company} team,

I'm reaching out from Gecons, a consulting firm specializing in Odoo ERP.

{job_ctx}We work with retail, manufacturing, logistics, and SME companies, offering:

- Odoo implementation and configuration
- Custom modules and integrations (APIs, marketplaces, couriers)
- Version migrations
- Financial reports and dashboards
- Ongoing support and maintenance

Do you have an Odoo project underway or planned? I'd love to learn about your needs.

More info: https://geconsas.com

Best regards,
Milena
Gecons – Consulting & IT Solutions
administracion@geconsas.com | geconsas.com

---
To unsubscribe, reply with UNSUBSCRIBE in the subject line.
"""


def _build_html(language: str, company: str, job_title: str = "") -> tuple[str, str]:
    html = _load_template(language)

    name_greeting = f", equipo de {company}" if language == "es" else f", {company} team"
    html = html.replace("{name_greeting}", name_greeting)

    if job_title:
        if language == "es":
            ctx = (
                f"Vi que {company} está buscando talento relacionado a <strong>{job_title}</strong>, "
                "lo que me indica que Odoo es parte central de su operación."
            )
        else:
            ctx = (
                f"I noticed {company} is looking for someone with <strong>{job_title}</strong> expertise, "
                "which tells me Odoo is a core part of your operations."
            )
    else:
        ctx = ""
    html = html.replace("{job_context}", ctx)

    # Asuntos más conversacionales — menor score de spam
    if language == "es":
        subject = f"Consulta sobre Odoo – {company}"
    else:
        subject = f"Quick question about Odoo at {company}"

    return subject, html


def _build_message(to_email: str, company: str, language: str, job_title: str) -> MIMEMultipart:
    subject, html_body = _build_html(language, company, job_title)
    text_body = _plain_text(language, company, job_title)

    msg = MIMEMultipart("alternative")
    msg["Subject"]         = subject
    msg["From"]            = f"{SENDER_FULL_NAME} <{EMAIL_ADDRESS}>"
    msg["To"]              = to_email
    msg["Reply-To"]        = EMAIL_ADDRESS
    msg["Date"]            = formatdate(localtime=True)
    msg["Message-ID"]      = make_msgid(domain="geconsas.com")
    msg["X-Mailer"]        = "Python"
    # Header de baja — requerido por CAN-SPAM y reduce spam score
    msg["List-Unsubscribe"] = f"<mailto:{EMAIL_ADDRESS}?subject=BAJA>"
    msg["BCC"]              = EMAIL_ADDRESS   # copia oculta a tu propio buzón

    # Texto plano PRIMERO — los filtros de spam lo valoran
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html",  "utf-8"))

    return msg


def _get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def send_email(to_email: str, company: str, language: str = "es", job_title: str = "") -> bool:
    if not EMAIL_PASSWORD:
        print("  [!] EMAIL_PASSWORD no configurado en .env")
        return False

    msg = _build_message(to_email, company, language, job_title)
    ctx = _get_ssl_context()

    try:
        recipients = [to_email, EMAIL_ADDRESS]
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx, timeout=15) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, recipients, msg.as_string())
        print(f"  [✓] Enviado → {to_email} ({company})")
        return True
    except smtplib.SMTPAuthenticationError:
        print("  [!] Error de autenticación SMTP. Verificar EMAIL_PASSWORD en .env")
        return False
    except Exception as e:
        print(f"  [!] Error enviando a {to_email}: {e}")
        return False


def test_connection() -> bool:
    ctx = _get_ssl_context()
    print(f"\nProbando conexión SMTP...")
    print(f"  Servidor : {SMTP_SERVER}:{SMTP_PORT}")
    print(f"  Usuario  : {EMAIL_ADDRESS}")
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=ctx, timeout=15) as server:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        else:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
                server.ehlo()
                server.starttls(context=ctx)
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("  [✓] Conexión y autenticación exitosa!\n")
        return True
    except smtplib.SMTPAuthenticationError:
        print("  [!] Credenciales incorrectas\n")
        return False
    except Exception as e:
        print(f"  [!] Error de conexión: {e}\n")
        return False


def run_campaign(prospects: list, dry_run: bool = False) -> int:
    import database as db
    from scrapers.email_finder import is_valid_email

    sent  = 0
    limit = EMAILS_PER_DAY

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Iniciando campaña — límite: {limit} emails/día\n")

    for row in prospects[:limit]:
        prospect_id, company, email, country, language, job_title = row

        if "@placeholder" in email or not is_valid_email(email):
            print(f"  [-] Saltando {company}: email inválido ({email})")
            continue

        subject, _ = _build_html(language or "es", company, job_title or "")

        if dry_run:
            print(f"  [DRY] {email} | {company} | {subject}")
            sent += 1
            continue

        success = send_email(email, company, language or "es", job_title or "")

        if success:
            db.mark_contacted(prospect_id, subject, status="sent")
            sent += 1
        else:
            db.mark_contacted(prospect_id, subject, status="error")

        if sent < limit:
            print(f"  ... esperando {DELAY_BETWEEN_EMAILS}s")
            time.sleep(DELAY_BETWEEN_EMAILS)

    print(f"\nCampaña finalizada. {sent} emails {'simulados' if dry_run else 'enviados'}.\n")
    return sent
