#!/usr/bin/env python3
"""
InsuranceOS — Entry point
"""
import os
import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()

BANNER = """
[bold blue]InsuranceOS[/bold blue] [dim]v0.1[/dim]
[dim]Insurance Operating System — Operado por IA[/dim]
"""

MODULES = {
    "quote":      ("Cotação",      "Cotar seguros: auto, vida, saúde, residencial, empresarial"),
    "policy":     ("Apólices",     "Emissão, renovação, endosso e cancelamento"),
    "claim":      ("Sinistros",    "Registro e acompanhamento de sinistros"),
    "crm":        ("CRM",          "Gestão de leads, clientes e histórico"),
    "sales":      ("Vendas",       "Pipeline, follow-up, comissões e metas"),
    "compliance": ("Compliance",   "SUSEP, regulatório e auditoria"),
    "report":     ("Relatórios",   "Dashboard KPIs: conversão, prêmios, sinistralidade"),
    "atendimento":("Atendimento",  "Bot WhatsApp: triagem, cotação rápida, FAQ"),
}


def show_menu():
    console.print(Panel(BANNER, border_style="blue"))

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Módulo", style="bold")
    table.add_column("Função")

    for i, (key, (name, desc)) in enumerate(MODULES.items(), 1):
        table.add_row(str(i), name, desc)

    table.add_row("s", "Server", "Iniciar webhook WhatsApp")
    table.add_row("q", "Sair", "")

    console.print(table)
    return input("\nEscolha: ").strip().lower()


def run_module(module_key: str, query: str = None):
    try:
        mod = __import__(f"modules.{module_key}.agent", fromlist=["run"])
        if hasattr(mod, "run"):
            mod.run(query)
        else:
            console.print(f"[yellow]Módulo '{module_key}' não tem função run()[/yellow]")
    except ImportError as e:
        console.print(f"[red]Erro ao carregar módulo '{module_key}': {e}[/red]")


def main():
    parser = argparse.ArgumentParser(description="InsuranceOS CLI")
    parser.add_argument("module", nargs="?", help="Módulo a executar")
    parser.add_argument("query", nargs="?", help="Consulta/prompt")
    parser.add_argument("--server", action="store_true", help="Iniciar servidor webhook")
    args = parser.parse_args()

    if args.server:
        import uvicorn
        from server import app
        uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8080)))
        return

    if args.module:
        run_module(args.module, args.query)
        return

    # Menu interativo
    keys = list(MODULES.keys())
    while True:
        choice = show_menu()

        if choice == "q":
            break
        elif choice == "s":
            import uvicorn
            from server import app
            uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8080)))
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            module_key = keys[int(choice) - 1]
            query = input(f"[{MODULES[module_key][0]}] Digite sua consulta: ").strip()
            run_module(module_key, query)
        else:
            console.print("[red]Opção inválida[/red]")


if __name__ == "__main__":
    main()
