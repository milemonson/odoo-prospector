"""
Gecons – Bot de prospección Odoo
=================================
Uso:
  python main.py scrape              # Scrapea todas las fuentes
  python main.py scrape --jobs       # Solo job boards
  python main.py scrape --partners   # Solo directorio Odoo
  python main.py email               # Envía emails a pendientes
  python main.py email --dry-run     # Simula envío (no manda nada)
  python main.py email --limit 10    # Envía máximo 10 emails
  python main.py list                # Lista prospects pendientes
  python main.py status              # Muestra estadísticas
"""

import argparse
import sys
import database as db


def cmd_scrape(args):
    db.init_db()
    total = 0

    run_jobs     = args.jobs     or (not args.jobs and not args.partners)
    run_partners = args.partners or (not args.jobs and not args.partners)

    if run_jobs:
        from scrapers import job_boards
        total += job_boards.scrape_all_keywords()

    if run_partners:
        from scrapers import odoo_partners
        total += odoo_partners.scrape(max_pages=args.pages)

    print(f"\nTotal prospects nuevos agregados: {total}")


def cmd_email(args):
    db.init_db()
    from email_sender import run_campaign

    limit = args.limit or 30
    prospects = db.get_pending_prospects(limit=limit)

    if not prospects:
        print("No hay prospects pendientes de contactar.")
        return

    print(f"Prospects pendientes: {len(prospects)}")
    run_campaign(prospects, dry_run=args.dry_run)


def cmd_list(args):
    db.init_db()
    prospects = db.get_pending_prospects(limit=100)

    if not prospects:
        print("No hay prospects pendientes.")
        return

    print(f"\n{'ID':<5} {'Empresa':<35} {'Email':<35} {'País':<20} {'Fuente'}")
    print("-" * 110)
    for row in prospects:
        pid, company, email, country, lang, job_title = row
        email_display = email if "@placeholder" not in email else "(sin email)"
        print(f"{pid:<5} {company[:33]:<35} {email_display[:33]:<35} {(country or '')[:18]:<20} {job_title or ''}")


def cmd_status(args):
    db.init_db()
    s = db.stats()

    print("\n========== GECONS PROSPECTOR – STATUS ==========")
    print(f"  Total prospects:     {s['total']}")
    print(f"  Contactados:         {s['contacted']}")
    print(f"  Pendientes:          {s['pending']}")
    print("\n  Por fuente:")
    for source, count in s["by_source"]:
        print(f"    {source:<20} {count}")
    print("=================================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="Gecons – Bot de prospección Odoo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # --- scrape ---
    p_scrape = sub.add_parser("scrape", help="Scrapea fuentes de leads")
    p_scrape.add_argument("--jobs",     action="store_true", help="Solo job boards")
    p_scrape.add_argument("--partners", action="store_true", help="Solo directorio Odoo")
    p_scrape.add_argument("--pages",    type=int, default=5,  help="Páginas del directorio Odoo (default: 5)")

    # --- email ---
    p_email = sub.add_parser("email", help="Envía emails a prospects pendientes")
    p_email.add_argument("--dry-run", action="store_true", help="Simula el envío sin mandar")
    p_email.add_argument("--limit",   type=int,            help="Máximo de emails a enviar")

    # --- enrich ---
    p_enrich = sub.add_parser("enrich", help="Busca emails para prospects sin contacto")
    p_enrich.add_argument("--limit", type=int, default=50, help="Máximo de empresas a procesar")

    # --- list ---
    sub.add_parser("list", help="Lista prospects pendientes")

    # --- status ---
    sub.add_parser("status", help="Muestra estadísticas")

    # --- test ---
    sub.add_parser("test", help="Prueba la conexión SMTP sin mandar emails")

    args = parser.parse_args()

    if args.command == "test":
        from email_sender import test_connection
        test_connection()
    elif args.command == "enrich":
        from enrich import run
        run(limit=args.limit)
    elif args.command == "scrape":
        cmd_scrape(args)
    elif args.command == "email":
        cmd_email(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
