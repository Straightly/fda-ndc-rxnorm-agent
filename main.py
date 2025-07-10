#!/usr/bin/env python3
"""
FDA NDC to RxNorm Matching Agent
Main entry point for the application
"""

import click
import uvicorn
from loguru import logger
from pathlib import Path

from src.agent import FDA_NDC_RxNorm_Agent
from src.api import app
from src.config import settings


@click.group()
@click.option('--log-level', default='INFO', help='Logging level')
def cli(log_level):
    """FDA NDC to RxNorm Matching Agent"""
    logger.remove()
    logger.add(lambda msg: click.echo(msg, nl=False), level=log_level)
    logger.info(f"Starting FDA NDC to RxNorm Agent with log level: {log_level}")


@cli.command()
@click.option('--force', is_flag=True, help='Force re-download even if data exists')
def download_ndc(force):
    """Download FDA NDC data"""
    agent = FDA_NDC_RxNorm_Agent()
    agent.download_ndc_data(force=force)


@cli.command()
@click.option('--batch-size', default=1000, help='Batch size for processing')
@click.option('--max-workers', default=4, help='Maximum number of workers')
def match_rxnorm(batch_size, max_workers):
    """Match NDC codes to RxNorm concepts"""
    agent = FDA_NDC_RxNorm_Agent()
    agent.match_ndc_to_rxnorm(batch_size=batch_size, max_workers=max_workers)


@cli.command()
@click.option('--force-download', is_flag=True, help='Force re-download NDC data')
@click.option('--batch-size', default=1000, help='Batch size for processing')
@click.option('--max-workers', default=4, help='Maximum number of workers')
def run_pipeline(force_download, batch_size, max_workers):
    """Run complete pipeline: download NDC data and match to RxNorm"""
    agent = FDA_NDC_RxNorm_Agent()
    agent.run_complete_pipeline(
        force_download=force_download,
        batch_size=batch_size,
        max_workers=max_workers
    )


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve_api(host, port, reload):
    """Start the API server"""
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


@cli.command()
def status():
    """Show current status of the agent"""
    agent = FDA_NDC_RxNorm_Agent()
    status_info = agent.get_status()
    
    click.echo("=== FDA NDC to RxNorm Agent Status ===")
    click.echo(f"NDC Data Downloaded: {status_info['ndc_downloaded']}")
    click.echo(f"Total NDC Records: {status_info['total_ndc_records']}")
    click.echo(f"RxNorm Matches: {status_info['rxnorm_matches']}")
    click.echo(f"Match Rate: {status_info['match_rate']:.2f}%")
    click.echo(f"Database Status: {status_info['database_status']}")


if __name__ == '__main__':
    cli() 