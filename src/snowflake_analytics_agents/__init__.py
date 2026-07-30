"""
Snowflake Analytics Agents - Suite for writing, reviewing, correcting, and documenting analytics code.
"""

__version__ = "0.1.0"
__author__ = "Analytics Team"

from .agents import CorrectorAgent, DocumenterAgent, ReviewerAgent, WriterAgent
from .config import load_config
from .credentials import (
    AWSSecretsManagerProvider,
    CredentialManager,
    CredentialProvider,
    CredentialSet,
    EnvironmentCredentialProvider,
    get_credential_manager,
)
from .dashboard import ChartConfig, DashboardConfig, FilterConfig
from .dashboard_agents import DashboardBuilderAgent, DashboardTesterAgent
from .dashboard_export_agent import DashboardExportAgent
from .export import ColumnFilter, ExportConfig, FilterOperator
from .snowflake_client import SnowflakeClient

__all__ = [
    "AWSSecretsManagerProvider",
    "ChartConfig",
    "ColumnFilter",
    "CorrectorAgent",
    "CredentialManager",
    "CredentialProvider",
    "CredentialSet",
    "DashboardBuilderAgent",
    "DashboardConfig",
    "DashboardExportAgent",
    "DashboardTesterAgent",
    "DocumenterAgent",
    "EnvironmentCredentialProvider",
    "ExportConfig",
    "FilterConfig",
    "FilterOperator",
    "ReviewerAgent",
    "SnowflakeClient",
    "WriterAgent",
    "get_credential_manager",
    "load_config",
]
