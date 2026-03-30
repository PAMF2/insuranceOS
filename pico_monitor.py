"""
InsuranceOS v0.2 — PicoClaw Monitor
Monitoramento em tempo real:
- Apólices prestes a vencer (30/15/7 dias)
- Follow-up de leads frios (sem resposta em 3+ dias)
- Health check dos serviços
- Alertas via Telegram
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PicoClaw] %(levelname)s — %(message)s"
)
logger = logging.getLogger("insuranceos.pico")

# Check intervals
CHECK_INTERVAL_RENEWALS = int(os.getenv("PICO_RENEWAL_INTERVAL_H", "6")) * 3600  # 6h
CHECK_INTERVAL_LEADS    = int(os.getenv("PICO_LEADS_INTERVAL_H",   "12")) * 3600  # 12h
CHECK_INTERVAL_HEALTH   = int(os.getenv("PICO_HEALTH_INTERVAL_S",  "60"))         # 60s

RENEWAL_ALERT_DAYS = [30, 15, 7, 3]  # Alert when N days to expiry


# ── Renewal Monitor ────────────────────────────────────────────────────────────

async def check_renewals():
    """Alert on policies expiring soon."""
    logger.info("Verificando renovações...")
    try:
        from tools.crm_sheets import _get_sheet
        from tools.notifications import alert_policy_renewal, send_telegram_alert

        ws = _get_sheet("Apolices")
        policies = ws.get_all_records()
        today = date.today()
        alerts_sent = 0

        for p in policies:
            if p.get("status", "").lower() != "ativa":
                continue

            fim_str = p.get("fim_vigencia", "")
            if not fim_str:
                continue

            try:
                # Try common date formats
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                    try:
                        fim = datetime.strptime(str(fim_str), fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    continue

                days_left = (fim - today).days

                if days_left in RENEWAL_ALERT_DAYS:
                    cliente_id = p.get("cliente_id", "")
                    ramo = p.get("ramo", "seguro")
                    apolice_num = p.get("numero_apolice", p.get("id", ""))

                    await alert_policy_renewal(cliente_id, f"{ramo} — {apolice_num}", str(fim))
                    logger.info(f"Alerta renovação: {apolice_num} vence em {days_left} dias")
                    alerts_sent += 1

            except Exception as e:
                logger.warning(f"Erro ao processar apólice {p.get('id')}: {e}")

        logger.info(f"Renovações: {alerts_sent} alertas enviados")
        return alerts_sent

    except Exception as e:
        logger.error(f"check_renewals error: {e}")
        return 0


# ── Cold Lead Follow-up ────────────────────────────────────────────────────────

async def check_cold_leads():
    """Send follow-up to leads with no activity for 3+ days."""
    logger.info("Verificando leads frios...")
    try:
        from tools.crm_sheets import _get_sheet
        from modules.sales.agent import send_follow_up

        ws = _get_sheet("Leads")
        leads = ws.get_all_records()
        today = datetime.now()
        followups = 0

        for lead in leads:
            status = lead.get("status", "novo")
            if status in ("convertido", "perdido", "inativo"):
                continue

            updated_str = lead.get("atualizado_em", "")
            if not updated_str:
                continue

            try:
                updated = datetime.fromisoformat(updated_str)
                days_inactive = (today - updated).days

                # Follow-up at 3 days for "novo", 7 days for "qualificado"
                trigger_days = 3 if status == "novo" else 7
                if days_inactive >= trigger_days:
                    telefone = lead.get("telefone", "")
                    if not telefone:
                        continue

                    template = "sem_resposta_3d"
                    context = {
                        "nome": lead.get("nome") or "cliente",
                        "ramo": lead.get("ramo_interesse") or "seguros",
                    }
                    sent = await send_follow_up(telefone, template, context)
                    if sent:
                        followups += 1
                        logger.info(f"Follow-up enviado: {telefone} ({days_inactive} dias inativo)")

            except Exception as e:
                logger.warning(f"Erro no lead {lead.get('id')}: {e}")

        logger.info(f"Follow-up: {followups} mensagens enviadas")
        return followups

    except Exception as e:
        logger.error(f"check_cold_leads error: {e}")
        return 0


# ── Health Check ───────────────────────────────────────────────────────────────

async def health_check() -> dict:
    """Check all services health."""
    import httpx
    results = {}

    # Webhook server
    webhook_url = f"http://localhost:{os.getenv('PORT', '8080')}/health"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(webhook_url)
            results["webhook"] = "ok" if r.status_code == 200 else f"status={r.status_code}"
    except Exception as e:
        results["webhook"] = f"down ({e})"

    # ADK server
    adk_url = f"{os.getenv('ADK_API_BASE', 'http://localhost:8000')}/health"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(adk_url)
            results["adk"] = "ok" if r.status_code == 200 else f"status={r.status_code}"
    except Exception as e:
        results["adk"] = f"down ({e})"

    # Google Sheets
    try:
        from tools.crm_sheets import _get_client
        _get_client()
        results["sheets"] = "ok"
    except Exception as e:
        results["sheets"] = f"error ({e})"

    return results


async def health_monitor_loop():
    """Continuously monitor health and alert on degradation."""
    from tools.notifications import send_telegram_alert
    prev_status = {}

    while True:
        try:
            status = await health_check()
            for service, state in status.items():
                prev = prev_status.get(service)
                if prev != state:
                    if state != "ok" and prev == "ok":
                        await send_telegram_alert(
                            f"⚠️ *InsuranceOS Alert*\nServiço `{service}` degradado: `{state}`"
                        )
                    elif state == "ok" and prev and prev != "ok":
                        await send_telegram_alert(
                            f"✅ *InsuranceOS*\nServiço `{service}` restaurado"
                        )
                    prev_status[service] = state

            logger.debug(f"Health: {status}")
        except Exception as e:
            logger.error(f"Health monitor error: {e}")

        await asyncio.sleep(CHECK_INTERVAL_HEALTH)


# ── Main Monitor Loop ──────────────────────────────────────────────────────────

async def run_monitor():
    """Run all monitoring tasks concurrently."""
    from rich.console import Console
    console = Console()
    console.print("[bold blue]PicoClaw Monitor — InsuranceOS v0.2[/bold blue]")
    console.print(f"  Renovações: a cada {CHECK_INTERVAL_RENEWALS//3600}h")
    console.print(f"  Lead follow-up: a cada {CHECK_INTERVAL_LEADS//3600}h")
    console.print(f"  Health check: a cada {CHECK_INTERVAL_HEALTH}s\n")

    async def renewal_loop():
        while True:
            await check_renewals()
            await asyncio.sleep(CHECK_INTERVAL_RENEWALS)

    async def leads_loop():
        while True:
            await check_cold_leads()
            await asyncio.sleep(CHECK_INTERVAL_LEADS)

    await asyncio.gather(
        renewal_loop(),
        leads_loop(),
        health_monitor_loop(),
    )


if __name__ == "__main__":
    asyncio.run(run_monitor())
