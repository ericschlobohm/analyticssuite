from __future__ import annotations

import logging
from typing import Any

try:
    import snowflake.connector
except ImportError:
    raise ImportError(
        "snowflake-connector-python is required. Install with: pip install snowflake-connector-python"
    )

from .config import SnowflakeConfig
from .credentials import get_credential_manager

logger = logging.getLogger(__name__)


class SnowflakeClient:
    """Client for connecting to and querying Snowflake."""

    def __init__(self, config: SnowflakeConfig):
        """
        Initialize Snowflake client.

        Args:
            config: SnowflakeConfig object with connection details
        """
        self.config = config
        self.connection = None
        self._connect()

    @classmethod
    def from_aws_secrets(
        cls, secret_id: str, region: str = "us-east-1", credential_provider: str = "aws"
    ) -> SnowflakeClient:
        """
        Create a Snowflake client using credentials from AWS Secrets Manager.

        Args:
            secret_id: The AWS Secrets Manager secret ID
                      (e.g., 'snowflake/prod/build-user')
            region: AWS region where the secret is stored
            credential_provider: Name of the credential provider to use

        Returns:
            SnowflakeClient instance

        Example:
            client = SnowflakeClient.from_aws_secrets(
                secret_id='snowflake/prod/build-user',
                region='us-east-1'
            )
        """
        logger.info(f"Initializing SnowflakeClient from AWS Secrets: {secret_id}")

        # Get credential manager and add AWS provider if needed
        cred_manager = get_credential_manager()
        if credential_provider == "aws" and "aws" not in cred_manager.providers:
            cred_manager.add_aws_provider(region=region)

        # Retrieve credentials
        creds = cred_manager.get_credentials(secret_id, provider=credential_provider)

        # Create SnowflakeConfig from credentials
        config = SnowflakeConfig(
            account=creds.account,
            user=creds.user,
            password=creds.password,
            database=creds.database or "DEFAULT",
            warehouse=creds.warehouse or "COMPUTE_WH",
            schema=creds.schema or "PUBLIC",
            role=creds.role or "ANALYST",
            region=creds.region or "us-east-1",
        )

        # Create and return client
        return cls(config)

    def _connect(self) -> None:
        """Establish connection to Snowflake."""
        try:
            self.connection = snowflake.connector.connect(**self.config.to_dict())
            logger.info(
                f"Connected to Snowflake account: {self.config.account}/"
                f"{self.config.database}.{self.config.schema}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise

    def execute_query(self, query: str, params: dict[str, Any] | None = None) -> list[tuple]:
        """
        Execute a SQL query against Snowflake.

        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            List of result tuples
        """
        if not self.connection:
            raise RuntimeError("Not connected to Snowflake")

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}")
            raise

    def get_columns(self, table: str) -> list[dict[str, Any]]:
        """
        Get column information for a table.

        Args:
            table: Table name (format: database.schema.table or schema.table)

        Returns:
            List of column dictionaries with name, type, and nullable
        """
        query = f"DESCRIBE TABLE {table}"
        results = self.execute_query(query)
        columns = []
        for row in results:
            columns.append(
                {
                    "name": row[0],
                    "type": row[1],
                    "nullable": row[4] == "Y" if len(row) > 4 else True,
                }
            )
        return columns

    def test_connection(self) -> bool:
        """
        Test the Snowflake connection.

        Returns:
            True if connection is successful
        """
        try:
            result = self.execute_query("SELECT 1")
            return len(result) > 0
        except Exception as e:  # noqa: BLE001 - report health-check failures as False
            logger.error(f"Connection test failed: {e}")
            return False

    def close(self) -> None:
        """Close the Snowflake connection."""
        if self.connection:
            self.connection.close()
            logger.info("Closed Snowflake connection")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
