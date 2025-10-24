#!/usr/bin/env python3
"""
Bank Statement Analyzer CLI
"""
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from parsers import get_parser, list_supported_banks
from ai import FinancialAnalyzer, EXAMPLE_QUERIES
from config import JSON_DIR, RAW_DIR, VALIDATED_DIR

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    🏦 Bank Statement Analyzer - Analyze Thai bank statements with local AI

    Parse PDF statements from 5 Thai banks and analyze with Ollama AI.
    """
    pass


@cli.command()
@click.option('--bank', '-b', required=True, type=click.Choice(['scb', 'tmb', 'bbl', 'kbank', 'ktb']),
              help='Bank code')
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Input PDF file')
@click.option('--output', '-o', 'output_file', type=click.Path(),
              help='Output JSON file (default: auto-generated)')
@click.option('--validate/--no-validate', default=True,
              help='Validate output data')
def parse(bank: str, input_file: str, output_file: Optional[str], validate: bool):
    """
    Parse a bank statement PDF file.

    Example:
        python main.py parse --bank scb --input statement.pdf
    """
    console.print(f"[bold blue]Parsing {bank.upper()} statement...[/bold blue]")

    try:
        # Get parser
        parser = get_parser(bank)

        # Parse PDF
        with console.status("[bold green]Extracting data from PDF..."):
            data = parser.parse_pdf(input_file)

        console.print("[green]✓[/green] PDF parsed successfully")

        # Auto-generate output filename if not provided
        if not output_file:
            input_path = Path(input_file)
            output_file = JSON_DIR / f"{input_path.stem}_{bank}.json"

        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        console.print(f"[green]✓[/green] Saved to: {output_path}")

        # Show summary
        summary = data.get('summary', {})
        metadata = data.get('metadata', {})

        table = Table(title="Statement Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Bank", metadata.get('bank', 'N/A'))
        table.add_row("Account", metadata.get('account_number', 'N/A'))
        table.add_row("Period", f"{metadata.get('statement_period', {}).get('start_date', 'N/A')} to {metadata.get('statement_period', {}).get('end_date', 'N/A')}")
        table.add_row("Total Transactions", str(summary.get('total_transactions', 0)))
        table.add_row("Total Debit", f"{summary.get('total_debit', 0):,.2f} THB")
        table.add_row("Total Credit", f"{summary.get('total_credit', 0):,.2f} THB")
        table.add_row("Net Change", f"{summary.get('net_change', 0):,.2f} THB")

        console.print(table)

        # Show validation
        validation = data.get('validation', {})
        status = validation.get('status', 'unknown')

        if status == 'valid':
            console.print(Panel("[bold green]✓ Validation: PASSED[/bold green]", style="green"))
        else:
            console.print(Panel("[bold red]✗ Validation: FAILED[/bold red]", style="red"))

            errors = validation.get('errors', [])
            if errors:
                console.print("[red]Errors:[/red]")
                for error in errors[:5]:
                    console.print(f"  • {error}")

        warnings = validation.get('warnings', [])
        if warnings:
            console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
            for warning in warnings[:3]:
                console.print(f"  • {warning}")
            if len(warnings) > 3:
                console.print(f"  ... and {len(warnings) - 3} more")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.option('--input', '-i', 'input_file', required=True, type=click.Path(exists=True),
              help='Input JSON file')
@click.option('--query', '-q', help='Analysis query')
@click.option('--template', '-t', type=click.Choice([
    'summary', 'spending_analysis', 'savings_advice', 'anomaly_detection',
    'budget_recommendation', 'category_breakdown', 'merchant_analysis', 'financial_health'
]), help='Use predefined query template')
@click.option('--interactive', '-I', is_flag=True, help='Interactive mode')
def analyze(input_file: str, query: Optional[str], template: Optional[str], interactive: bool):
    """
    Analyze statement with AI.

    Example:
        python main.py analyze --input output.json --query "สรุปรายจ่าย"
        python main.py analyze --input output.json --template summary
        python main.py analyze --input output.json --interactive
    """
    console.print("[bold blue]Loading statement data...[/bold blue]")

    try:
        # Load JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        console.print("[green]✓[/green] Data loaded")

        # Initialize analyzer
        analyzer = FinancialAnalyzer()

        # Check if Ollama is available
        if not analyzer.is_available():
            console.print("[bold red]Error:[/bold red] Cannot connect to Ollama")
            console.print("Make sure Ollama is running: ollama serve")
            sys.exit(1)

        # Interactive mode
        if interactive:
            console.print("\n[bold cyan]Interactive Analysis Mode[/bold cyan]")
            console.print("Type your questions (type 'exit' to quit)\n")

            console.print("[dim]Example queries:[/dim]")
            for i, example in enumerate(EXAMPLE_QUERIES[:5], 1):
                console.print(f"[dim]  {i}. {example}[/dim]")
            console.print()

            analyzer.interactive_query(data)
            return

        # Template mode
        if template:
            console.print(f"[bold blue]Running template: {template}[/bold blue]\n")

            with console.status("[bold green]Analyzing with AI..."):
                if template == 'summary':
                    result = analyzer.quick_summary(data)
                elif template == 'spending_analysis':
                    result = analyzer.spending_analysis(data)
                elif template == 'savings_advice':
                    result = analyzer.savings_advice(data)
                elif template == 'anomaly_detection':
                    result = analyzer.detect_anomalies(data)
                elif template == 'budget_recommendation':
                    result = analyzer.budget_recommendation(data)
                elif template == 'category_breakdown':
                    result = analyzer.category_breakdown(data)
                elif template == 'merchant_analysis':
                    result = analyzer.merchant_analysis(data)
                elif template == 'financial_health':
                    result = analyzer.financial_health_score(data)

            console.print(Panel(result, title="Analysis Result", border_style="green"))
            return

        # Query mode
        if query:
            console.print(f"[bold blue]Query:[/bold blue] {query}\n")

            with console.status("[bold green]Analyzing with AI..."):
                result = analyzer.analyze(data, query)

            console.print(Panel(result, title="Analysis Result", border_style="green"))
            return

        # No mode specified
        console.print("[yellow]Please specify --query, --template, or --interactive[/yellow]")
        console.print("\nAvailable templates:")
        for tmpl in ['summary', 'spending_analysis', 'savings_advice', 'anomaly_detection',
                     'budget_recommendation', 'category_breakdown', 'merchant_analysis', 'financial_health']:
            console.print(f"  • {tmpl}")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
def info():
    """
    Show system information and supported banks.
    """
    console.print(Panel.fit(
        "[bold cyan]🏦 Bank Statement Analyzer[/bold cyan]\n"
        "Analyze Thai bank statements with local AI",
        border_style="cyan"
    ))

    # Supported banks
    table = Table(title="Supported Banks", show_header=True)
    table.add_column("Code", style="cyan")
    table.add_column("Bank Name", style="green")

    banks = {
        'scb': 'ธนาคารไทยพาณิชย์ (SCB)',
        'tmb': 'ธนาคารทหารไทยธนชาต (TMB)',
        'bbl': 'ธนาคารกรุงเทพ (BBL)',
        'kbank': 'ธนาคารกสิกรไทย (KBANK)',
        'ktb': 'ธนาคารกรุงไทย (KTB)',
    }

    for code, name in banks.items():
        table.add_row(code, name)

    console.print(table)

    # Check AI availability
    console.print("\n[bold]AI Status:[/bold]")
    analyzer = FinancialAnalyzer()
    if analyzer.is_available():
        models = analyzer.client.list_models()
        console.print("[green]✓[/green] Ollama is running")
        if models:
            console.print(f"[green]✓[/green] Available models: {', '.join(models)}")
    else:
        console.print("[red]✗[/red] Ollama is not available")
        console.print("[dim]  Run: ollama serve[/dim]")


@cli.command()
@click.option('--bank', '-b', required=True, type=click.Choice(['scb', 'tmb', 'bbl', 'kbank', 'ktb']),
              help='Bank code')
@click.option('--input-dir', '-i', 'input_dir', required=True, type=click.Path(exists=True),
              help='Input directory with PDF files')
@click.option('--output-dir', '-o', 'output_dir', type=click.Path(),
              help='Output directory for JSON files')
def batch(bank: str, input_dir: str, output_dir: Optional[str]):
    """
    Batch process multiple PDF files.

    Example:
        python main.py batch --bank scb --input-dir ./pdfs/ --output-dir ./json/
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else JSON_DIR
    output_path.mkdir(parents=True, exist_ok=True)

    # Find all PDF files
    pdf_files = list(input_path.glob("*.pdf"))

    if not pdf_files:
        console.print(f"[yellow]No PDF files found in {input_dir}[/yellow]")
        return

    console.print(f"[bold blue]Processing {len(pdf_files)} PDF files...[/bold blue]\n")

    parser = get_parser(bank)
    success_count = 0
    error_count = 0

    for pdf_file in pdf_files:
        try:
            console.print(f"Processing: {pdf_file.name}... ", end="")

            data = parser.parse_pdf(str(pdf_file))

            output_file = output_path / f"{pdf_file.stem}_{bank}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            console.print("[green]✓[/green]")
            success_count += 1

        except Exception as e:
            console.print(f"[red]✗[/red] {str(e)}")
            error_count += 1

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"[green]✓ Success: {success_count}[/green]")
    if error_count > 0:
        console.print(f"[red]✗ Failed: {error_count}[/red]")


if __name__ == '__main__':
    cli()
