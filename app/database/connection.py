"""Asyncpg connection pool factory.

Supports three auth modes (evaluated in priority order):
  1. AWS Secrets Manager  — AWS_SECRET_NAME is set; credentials fetched from
                            Secrets Manager and rebuilt into a DSN.
  2. RDS IAM token auth   — RDS_IAM_AUTH=true; boto3 generates a 15-min token
                            per-connection, no password in DATABASE_URL.
  3. Standard DSN         — password embedded in DATABASE_URL.
"""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse

import asyncpg

logger = logging.getLogger(__name__)


async def create_pool(dsn: str) -> asyncpg.Pool:
    """Create and return an asyncpg connection pool.

    Auth mode is chosen automatically from Settings (see module docstring).
    """
    from app.core.config import get_settings
    settings = get_settings()

    if settings.aws_secret_name:
        return await _create_secrets_manager_pool(settings.aws_secret_name, settings.aws_region)

    if settings.rds_iam_auth:
        return await _create_iam_pool(dsn, settings.aws_region)

    return await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)


async def _create_secrets_manager_pool(secret_name: str, region: str) -> asyncpg.Pool:
    """Fetch DB credentials from AWS Secrets Manager and build a pool.

    Expected secret value (JSON):
      {"username": "...", "password": "...", "host": "...",
       "port": 5432, "dbname": "..."}
    """
    import boto3
    from botocore.exceptions import ClientError

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region)

    try:
        resp = client.get_secret_value(SecretId=secret_name)
    except ClientError as exc:
        logger.error("Failed to retrieve secret '%s': %s", secret_name, exc)
        raise

    secret = json.loads(resp["SecretString"])
    host = secret["host"]
    port = int(secret.get("port", 5432))
    user = secret["username"]
    password = secret["password"]
    database = secret.get("dbname", "postgres")

    logger.info("Connecting via Secrets Manager secret '%s': %s@%s/%s", secret_name, user, host, database)
    pool = await asyncpg.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        ssl="require",
        min_size=2,
        max_size=10,
    )
    logger.info("Pool created from Secrets Manager credentials")
    return pool


async def _create_iam_pool(dsn: str, region: str) -> asyncpg.Pool:
    """Build a pool that refreshes IAM tokens automatically."""
    import boto3

    parsed = urlparse(dsn)
    hostname = parsed.hostname
    port = parsed.port or 5432
    username = parsed.username
    database = (parsed.path or "/postgres").lstrip("/")

    rds_client = boto3.client("rds", region_name=region)

    def _get_token() -> str:
        """Called by asyncpg each time it opens a fresh connection."""
        token = rds_client.generate_db_auth_token(
            DBHostname=hostname,
            Port=port,
            DBUsername=username,
        )
        logger.debug("Generated RDS IAM auth token for %s@%s", username, hostname)
        return token

    pool = await asyncpg.create_pool(
        host=hostname,
        port=port,
        user=username,
        password=_get_token,
        database=database,
        ssl="require",
        min_size=2,
        max_size=10,
    )
    logger.info("Connected to RDS via IAM auth: %s@%s/%s", username, hostname, database)
    return pool
