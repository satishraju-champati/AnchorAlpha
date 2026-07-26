"""
Loads all API keys from AWS Secrets Manager at container startup.
Secret names are injected as env vars by the ECS task definition.
"""

import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)


def _get_secret(client, secret_name: str) -> dict:
    raw = client.get_secret_value(SecretId=secret_name)["SecretString"]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Plain string secret (e.g. FMP key stored as bare string by CloudFormation)
        return {"_value": raw.strip()}


def load_secrets() -> dict:
    client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

    claude = _get_secret(client, os.environ["CLAUDE_SECRET_NAME"])
    alpaca_paper = _get_secret(client, os.environ["ALPACA_PAPER_SECRET_NAME"])
    alphavantage = _get_secret(client, os.environ["ALPHAVANTAGE_SECRET_NAME"])
    fmp = _get_secret(client, os.environ["FMP_SECRET_NAME"])

    secrets = {
        "claude_key": claude["CLAUDE_API_KEY"],
        "alpaca_paper_key": alpaca_paper["ALPACA_KEY"],
        "alpaca_paper_secret": alpaca_paper["ALPACA_SECRET"],
        "alphavantage_key": alphavantage["ALPHAVANTAGE_API_KEY"],
        "fmp_key": fmp.get("_value") or fmp.get("FMP_API_KEY") or list(fmp.values())[0],
    }

    # Optional: live Alpaca keys — only present once user is ready to go live
    live_secret_name = os.environ.get("ALPACA_LIVE_SECRET_NAME")
    if live_secret_name:
        try:
            alpaca_live = _get_secret(client, live_secret_name)
            secrets["alpaca_live_key"] = alpaca_live["ALPACA_KEY"]
            secrets["alpaca_live_secret"] = alpaca_live["ALPACA_SECRET"]
            logger.info("Live Alpaca keys loaded")
        except Exception as e:
            logger.warning(f"Could not load live Alpaca keys from {live_secret_name}: {e}")

    logger.info("All secrets loaded from Secrets Manager")
    return secrets
