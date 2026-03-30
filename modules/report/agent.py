"""
InsuranceOS v0.4 — Agente de Relatórios / Dashboard HTML
KPIs: leads, conversão, prêmios emitidos, sinistralidade.
Gera dashboard HTML e relatório PDF.
"""
import logging
import asyncio
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("insuranceos.report")

OUTPUT_DIR = Path("output")


async def run_async(user_phone: str, text: str) -> str:
    return await generate_dashboard_text()


async def generate_dashboard_text() -> str:
    """Generate KPI summary from Google Sheets data."""
    try:
        from tools.crm_sheets import _get_sheet

        leads_ws  = _get_sheet("Leads")
        pol_ws    = _get_sheet("Apolices")
        sin_ws    = _get_sheet("Sinistros")

        leads     = leads_ws.get_all_records()
        apolices  = pol_ws.get_all_records()
        sinistros = sin_ws.get_all_records()

        total_leads   = len(leads)
        novos         = sum(1 for l in leads if l.get("status") == "novo")
        qualificados  = sum(1 for l in leads if l.get("status") == "qualificado")
        convertidos   = sum(1 for l in leads if l.get("status") == "convertido")
        perdidos      = sum(1 for l in leads if l.get("status") == "perdido")
        conversao_pct = f"{(convertidos/total_leads*100):.1f}%" if total_leads else "0%"

        total_apolices = len(apolices)
        ativas = sum(1 for a in apolices if a.get("status") == "ativa")
        premio_total = sum(float(a.get("premio_total") or 0) for a in apolices)

        total_sin    = len(sinistros)
        abertos      = sum(1 for s in sinistros if s.get("status") == "aberto")
        valor_sin    = sum(float(s.get("valor_estimado") or 0) for s in sinistros)
        sinistralidade = (valor_sin / premio_total * 100) if premio_total else 0

        # Breakdown por ramo
        ramos = {}
        for a in apolices:
            r = a.get("ramo", "outros")
            ramos[r] = ramos.get(r, 0) + 1

        ramos_str = " | ".join(f"{r}: {n}" for r, n in sorted(ramos.items(), key=lambda x: -x[1]))

        return (
            f"*Dashboard InsuranceOS* 📊\n"
            f"_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n"
            f"*Leads*\n"
            f"• Total: {total_leads} (Novos: {novos} | Qualif.: {qualificados} | Conv.: {convertidos} | Perd.: {perdidos})\n"
            f"• Taxa de conversão: {conversao_pct}\n\n"
            f"*Apólices*\n"
            f"• Total: {total_apolices} | Ativas: {ativas}\n"
            f"• Prêmios emitidos: R$ {premio_total:,.2f}\n"
            f"• Por ramo: {ramos_str or 'N/A'}\n\n"
            f"*Sinistros*\n"
            f"• Total: {total_sin} | Abertos: {abertos}\n"
            f"• Valor estimado: R$ {valor_sin:,.2f}\n"
            f"• Sinistralidade: {sinistralidade:.1f}%\n"
        )

    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        return (
            "*Dashboard InsuranceOS* 📊\n\n"
            "Não foi possível carregar os dados. "
            "Verifique as configurações do Google Sheets."
        )


def generate_html_dashboard() -> str:
    """Generate full HTML dashboard. Returns file path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    filename = OUTPUT_DIR / f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    try:
        data = asyncio.run(_fetch_kpi_data())
    except Exception:
        data = _empty_kpis()

    html = _build_html(data)
    filename.write_text(html, encoding="utf-8")
    logger.info(f"Dashboard HTML gerado: {filename}")
    return str(filename)


async def _fetch_kpi_data() -> dict:
    try:
        from tools.crm_sheets import _get_sheet
        leads     = _get_sheet("Leads").get_all_records()
        apolices  = _get_sheet("Apolices").get_all_records()
        sinistros = _get_sheet("Sinistros").get_all_records()

        total_leads  = len(leads)
        convertidos  = sum(1 for l in leads if l.get("status") == "convertido")
        novos        = sum(1 for l in leads if l.get("status") == "novo")
        premio       = sum(float(a.get("premio_total") or 0) for a in apolices)
        sin_abertos  = sum(1 for s in sinistros if s.get("status") == "aberto")
        sin_valor    = sum(float(s.get("valor_estimado") or 0) for s in sinistros)
        conv_rate    = (convertidos / total_leads * 100) if total_leads else 0
        sinistralidade = (sin_valor / premio * 100) if premio else 0

        ramos = {}
        for a in apolices:
            r = a.get("ramo", "outros").title()
            ramos[r] = ramos.get(r, 0) + 1

        return {
            "total_leads": total_leads,
            "novos": novos,
            "convertidos": convertidos,
            "taxa_conversao": round(conv_rate, 1),
            "total_apolices": len(apolices),
            "premio_total": premio,
            "sinistros_abertos": sin_abertos,
            "sinistralidade": round(sinistralidade, 1),
            "por_ramo": ramos,
        }
    except Exception:
        return _empty_kpis()


def _empty_kpis() -> dict:
    return {
        "total_leads": 0, "novos": 0, "convertidos": 0,
        "taxa_conversao": 0, "total_apolices": 0, "premio_total": 0,
        "sinistros_abertos": 0, "sinistralidade": 0, "por_ramo": {},
    }


def _build_html(d: dict) -> str:
    ramo_bars = ""
    total_ramos = sum(d["por_ramo"].values()) or 1
    colors = ["#1a73e8", "#34a853", "#fbbc05", "#ea4335", "#9c27b0", "#00bcd4"]
    for i, (ramo, n) in enumerate(sorted(d["por_ramo"].items(), key=lambda x: -x[1])[:6]):
        pct = n / total_ramos * 100
        color = colors[i % len(colors)]
        ramo_bars += f"""
        <div class="ramo-row">
            <span class="ramo-label">{ramo}</span>
            <div class="ramo-bar-wrap">
                <div class="ramo-bar" style="width:{pct:.1f}%;background:{color}"></div>
            </div>
            <span class="ramo-n">{n}</span>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>InsuranceOS — Dashboard</title>
<style>
  :root {{
    --blue: #1a3a5c; --accent: #1a73e8; --green: #34a853;
    --yellow: #fbbc05; --red: #ea4335; --bg: #f8fafc; --card: #ffffff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: var(--bg); color: #1a1a2e; }}
  header {{ background: var(--blue); color: white; padding: 20px 32px;
            display: flex; justify-content: space-between; align-items: center; }}
  header h1 {{ font-size: 1.5rem; font-weight: 700; }}
  header span {{ font-size: 0.85rem; opacity: 0.7; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
           gap: 16px; padding: 24px 32px; }}
  .card {{ background: var(--card); border-radius: 12px; padding: 20px;
           box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .card .label {{ font-size: 0.78rem; text-transform: uppercase;
                  letter-spacing: .05em; color: #666; margin-bottom: 8px; }}
  .card .value {{ font-size: 2rem; font-weight: 700; color: var(--blue); }}
  .card .sub {{ font-size: 0.82rem; color: #888; margin-top: 4px; }}
  .card.green .value {{ color: var(--green); }}
  .card.yellow .value {{ color: var(--yellow); }}
  .card.red .value {{ color: var(--red); }}
  .section {{ padding: 0 32px 32px; }}
  .section h2 {{ font-size: 1.1rem; font-weight: 600; color: var(--blue);
                 margin-bottom: 16px; padding-bottom: 8px;
                 border-bottom: 2px solid var(--accent); }}
  .ramo-row {{ display: flex; align-items: center; margin-bottom: 10px; gap: 12px; }}
  .ramo-label {{ width: 120px; font-size: 0.88rem; }}
  .ramo-bar-wrap {{ flex: 1; background: #eee; border-radius: 4px; height: 16px; overflow: hidden; }}
  .ramo-bar {{ height: 100%; border-radius: 4px; transition: width .5s; }}
  .ramo-n {{ width: 30px; text-align: right; font-size: 0.85rem; font-weight: 600; }}
  footer {{ text-align: center; padding: 20px; color: #aaa; font-size: 0.8rem; }}
</style>
</head>
<body>
<header>
  <h1>InsuranceOS — Dashboard</h1>
  <span>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
</header>

<div class="grid">
  <div class="card">
    <div class="label">Total Leads</div>
    <div class="value">{d['total_leads']}</div>
    <div class="sub">Novos: {d['novos']}</div>
  </div>
  <div class="card green">
    <div class="label">Conversão</div>
    <div class="value">{d['taxa_conversao']}%</div>
    <div class="sub">Convertidos: {d['convertidos']}</div>
  </div>
  <div class="card">
    <div class="label">Apólices Ativas</div>
    <div class="value">{d['total_apolices']}</div>
    <div class="sub">&nbsp;</div>
  </div>
  <div class="card green">
    <div class="label">Prêmios Emitidos</div>
    <div class="value">R$ {d['premio_total']:,.0f}</div>
    <div class="sub">&nbsp;</div>
  </div>
  <div class="card {'red' if d['sinistros_abertos'] > 0 else ''}">
    <div class="label">Sinistros Abertos</div>
    <div class="value">{d['sinistros_abertos']}</div>
    <div class="sub">&nbsp;</div>
  </div>
  <div class="card {'yellow' if d['sinistralidade'] > 50 else ''}">
    <div class="label">Sinistralidade</div>
    <div class="value">{d['sinistralidade']}%</div>
    <div class="sub">Referência: &lt; 60%</div>
  </div>
</div>

<div class="section">
  <h2>Apólices por Ramo</h2>
  {ramo_bars if ramo_bars else '<p style="color:#aaa">Sem dados de apólices</p>'}
</div>

<footer>InsuranceOS v0.4 — Powered by AI</footer>
</body>
</html>"""


def run(query: str = None):
    from rich.console import Console
    console = Console()
    console.print("[bold blue]Relatórios — InsuranceOS[/bold blue]\n")

    if query and "html" in query.lower():
        path = generate_html_dashboard()
        console.print(f"Dashboard HTML gerado: [green]{path}[/green]")
    else:
        response = asyncio.run(generate_dashboard_text())
        console.print(response)
