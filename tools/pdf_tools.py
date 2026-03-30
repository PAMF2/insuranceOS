"""
InsuranceOS v0.3 — PDF Generator
Gera propostas e relatórios em PDF.
"""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("insuranceos.pdf")

OUTPUT_DIR = Path("output")


def _ensure_output():
    OUTPUT_DIR.mkdir(exist_ok=True)


def gerar_proposta_auto(
    cliente_nome: str,
    cliente_telefone: str,
    veiculo_modelo: str,
    veiculo_ano: int,
    cotacoes: list[dict],
    corretor_nome: str = "Corretor InsuranceOS",
) -> str:
    """Generate auto insurance proposal PDF. Returns file path."""
    _ensure_output()

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        filename = OUTPUT_DIR / f"proposta_auto_{cliente_telefone}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        doc = SimpleDocTemplate(str(filename), pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)

        styles = getSampleStyleSheet()
        elements = []

        # Colors
        DARK_BLUE = colors.HexColor("#1a3a5c")
        LIGHT_BLUE = colors.HexColor("#e8f0fe")
        GREEN = colors.HexColor("#2e7d32")

        # Header
        title_style = ParagraphStyle("title", parent=styles["Title"],
                                     textColor=DARK_BLUE, fontSize=20, spaceAfter=6)
        sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                                   textColor=colors.grey, fontSize=10, spaceAfter=20)

        elements.append(Paragraph("InsuranceOS", title_style))
        elements.append(Paragraph("Proposta de Seguro Auto", sub_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=DARK_BLUE))
        elements.append(Spacer(1, 0.5*cm))

        # Client info
        elements.append(Paragraph("Dados do Cliente", styles["Heading2"]))
        data_cliente = [
            ["Nome:", cliente_nome],
            ["Contato:", cliente_telefone],
            ["Veículo:", f"{veiculo_modelo} ({veiculo_ano})"],
            ["Data da proposta:", datetime.now().strftime("%d/%m/%Y %H:%M")],
            ["Validade:", "7 dias"],
        ]
        t = Table(data_cliente, colWidths=[4*cm, 12*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BLUE),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 0.5*cm))

        # Quotes table
        elements.append(Paragraph("Comparativo de Cotações", styles["Heading2"]))

        header = ["Seguradora", "Cobertura", "Franquia", "Prêmio Mensal", "Prêmio Anual"]
        rows = [header]
        for c in cotacoes[:5]:
            rows.append([
                c.get("seguradora", ""),
                c.get("cobertura", "compreensiva"),
                c.get("franquia", "normal"),
                f"R$ {c.get('premio_mensal', 0):,.2f}",
                f"R$ {c.get('premio_anual', 0):,.2f}",
            ])

        t2 = Table(rows, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 3*cm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BLUE]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 6),
            # Highlight best price
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#e8f5e9")),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
        ]))
        elements.append(t2)
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph("* Melhor opção destacada em verde", styles["Normal"]))
        elements.append(Spacer(1, 1*cm))

        # Footer
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        footer_style = ParagraphStyle("footer", parent=styles["Normal"],
                                      textColor=colors.grey, fontSize=8, spaceBefore=6)
        elements.append(Paragraph(
            f"Corretor: {corretor_nome} | InsuranceOS | "
            f"Valores sujeitos a vistoria e análise de risco | "
            f"SUSEP — Registro do Corretor",
            footer_style
        ))

        doc.build(elements)
        logger.info(f"PDF gerado: {filename}")
        return str(filename)

    except ImportError:
        logger.error("reportlab não instalado — pip install reportlab")
        return ""
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return ""


def gerar_relatorio_kpis(dados: dict) -> str:
    """Generate KPI report PDF."""
    _ensure_output()
    # Simplified version — full implementation in v0.4 HTML dashboard
    filename = OUTPUT_DIR / f"relatorio_kpis_{datetime.now().strftime('%Y%m%d')}.pdf"

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(str(filename), pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph("InsuranceOS — Relatório KPIs", styles["Title"]))
        elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
        elements.append(Spacer(1, 1*cm))

        rows = [["Métrica", "Valor"]]
        for k, v in dados.items():
            rows.append([str(k), str(v)])

        t = Table(rows)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(t)
        doc.build(elements)
        return str(filename)

    except Exception as e:
        logger.error(f"KPI PDF error: {e}")
        return ""
