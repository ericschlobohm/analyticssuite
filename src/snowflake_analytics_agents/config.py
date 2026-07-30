from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class SnowflakeConfig:
    """Snowflake connection configuration."""

    account: str
    user: str
    password: str
    database: str
    warehouse: str
    schema: str = "PUBLIC"
    role: str | None = None
    region: str | None = None
    session_parameters: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to connection dictionary for snowflake-connector-python."""
        conn_dict = {
            "account": self.account,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "warehouse": self.warehouse,
            "schema": self.schema,
        }
        if self.role:
            conn_dict["role"] = self.role
        if self.region:
            conn_dict["region"] = self.region
        if self.session_parameters:
            conn_dict["session_parameters"] = self.session_parameters
        return conn_dict


@dataclass
class AgentConfig:
    """Configuration for agent behavior."""

    timeout: int = 300
    max_retries: int = 3
    debug: bool = False
    log_level: str = "INFO"


@dataclass
class Config:
    """Top-level configuration container."""

    snowflake: SnowflakeConfig
    agents: AgentConfig
    extra: dict[str, Any]


def load_config(
    env_file: Path | None = None,
    config_file: Path | None = None,
) -> Config:
    """
    Load configuration from multiple sources with priority:
    1. Environment variables
    2. YAML config file
    3. .env file
    4. Defaults

    Args:
        env_file: Path to .env file (defaults to .env in current dir)
        config_file: Path to YAML config file

    Returns:
        Config object with all settings
    """
    # Load .env file
    if env_file is None:
        env_file = Path(".env")
    if env_file.exists():
        load_dotenv(env_file)

    # Load YAML config if provided
    yaml_config = {}
    if config_file and Path(config_file).exists():
        with open(config_file) as f:
            yaml_config = yaml.safe_load(f) or {}

    # Get Snowflake config from environment or YAML
    snowflake_yaml = yaml_config.get("snowflake", {})
    snowflake = SnowflakeConfig(
        account=os.getenv("SNOWFLAKE_ACCOUNT") or snowflake_yaml.get("account", ""),
        user=os.getenv("SNOWFLAKE_USER") or snowflake_yaml.get("user", ""),
        password=os.getenv("SNOWFLAKE_PASSWORD") or snowflake_yaml.get("password", ""),
        database=os.getenv("SNOWFLAKE_DATABASE") or snowflake_yaml.get("database", ""),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE") or snowflake_yaml.get("warehouse", ""),
        schema=os.getenv("SNOWFLAKE_SCHEMA") or snowflake_yaml.get("schema", "PUBLIC"),
        role=os.getenv("SNOWFLAKE_ROLE") or snowflake_yaml.get("role"),
        region=os.getenv("SNOWFLAKE_REGION") or snowflake_yaml.get("region"),
    )

    # Get Agent config from environment or YAML
    agents_yaml = yaml_config.get("agents", {})
    agents = AgentConfig(
        timeout=int(os.getenv("AGENT_TIMEOUT", agents_yaml.get("timeout", 300))),
        max_retries=int(os.getenv("AGENT_MAX_RETRIES", agents_yaml.get("max_retries", 3))),
        debug=os.getenv("DEBUG", str(agents_yaml.get("debug", "false"))).lower() == "true",
        log_level=os.getenv("LOG_LEVEL", agents_yaml.get("log_level", "INFO")),
    )

    # Extra configuration
    extra = yaml_config.get("extra", {})

    return Config(
        snowflake=snowflake,
        agents=agents,
        extra=extra,
    )
