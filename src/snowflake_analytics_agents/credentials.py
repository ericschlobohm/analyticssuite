from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

try:
    import boto3
except ImportError:
    boto3 = None

logger = logging.getLogger(__name__)


@dataclass
class CredentialSet:
    """A set of Snowflake credentials."""

    user: str
    password: str
    account: str
    database: str | None = None
    warehouse: str | None = None
    schema: str | None = None
    role: str | None = None
    region: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for Snowflake connection."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class CredentialProvider(ABC):
    """Abstract base class for credential providers."""

    @abstractmethod
    def get_credentials(self, credential_id: str) -> CredentialSet:
        """
        Retrieve credentials by ID.

        Args:
            credential_id: Identifier for the credential set to retrieve

        Returns:
            CredentialSet containing the credentials

        Raises:
            Exception if credentials cannot be retrieved
        """


class EnvironmentCredentialProvider(CredentialProvider):
    """Retrieve credentials from environment variables."""

    def get_credentials(self, credential_id: str = "default") -> CredentialSet:
        """
        Retrieve credentials from environment variables.

        Expected env vars:
        - SNOWFLAKE_USER
        - SNOWFLAKE_PASSWORD
        - SNOWFLAKE_ACCOUNT
        - SNOWFLAKE_DATABASE
        - SNOWFLAKE_WAREHOUSE
        - SNOWFLAKE_SCHEMA
        - SNOWFLAKE_ROLE
        - SNOWFLAKE_REGION
        """
        import os

        return CredentialSet(
            user=os.getenv("SNOWFLAKE_USER", ""),
            password=os.getenv("SNOWFLAKE_PASSWORD", ""),
            account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE"),
            region=os.getenv("SNOWFLAKE_REGION"),
        )


class AWSSecretsManagerProvider(CredentialProvider):
    """Retrieve credentials from AWS Secrets Manager."""

    def __init__(self, region_name: str = "us-east-1"):
        """
        Initialize the AWS Secrets Manager provider.

        Args:
            region_name: AWS region where secrets are stored
        """
        self.region_name = region_name
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the AWS Secrets Manager client."""
        try:
            if boto3 is None:
                raise ImportError
            self.client = boto3.client("secretsmanager", region_name=self.region_name)
            logger.info(f"AWS Secrets Manager client initialized for region {self.region_name}")
        except ImportError:
            logger.error("boto3 is not installed. Install with: pip install boto3")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager client: {e}")
            raise

    def get_credentials(self, credential_id: str) -> CredentialSet:
        """
        Retrieve credentials from AWS Secrets Manager.

        Args:
            credential_id: The secret name in AWS Secrets Manager
                         (e.g., "snowflake/prod/build-user")

        Returns:
            CredentialSet containing the credentials

        Raises:
            Exception if secret cannot be retrieved
        """
        if not self.client:
            raise RuntimeError("AWS Secrets Manager client not initialized")

        try:
            logger.info(f"Retrieving credentials from AWS Secrets Manager: {credential_id}")
            response = self.client.get_secret_value(SecretId=credential_id)

            # Secrets can be stored as JSON string or plain text
            secret_data = response.get("SecretString")

            if not secret_data:
                raise ValueError(f"Secret {credential_id} not found or is empty")

            try:
                # Try to parse as JSON
                secret_dict = json.loads(secret_data)
            except json.JSONDecodeError:
                # If not JSON, treat as comma-separated or raise error
                logger.warning(f"Secret {credential_id} is not valid JSON")
                raise ValueError(
                    f"Secret {credential_id} must be a JSON object "
                    "with keys: user, password, account, [database], [warehouse], etc."
                )

            # Validate required fields
            required_fields = {"user", "password", "account"}
            if not required_fields.issubset(set(secret_dict.keys())):
                missing = required_fields - set(secret_dict.keys())
                raise ValueError(f"Secret {credential_id} missing required fields: {missing}")

            logger.info(f"Successfully retrieved credentials for user: {secret_dict.get('user')}")

            return CredentialSet(
                user=secret_dict["user"],
                password=secret_dict["password"],
                account=secret_dict["account"],
                database=secret_dict.get("database"),
                warehouse=secret_dict.get("warehouse"),
                schema=secret_dict.get("schema"),
                role=secret_dict.get("role"),
                region=secret_dict.get("region"),
            )

        except Exception as e:
            aws_exceptions = getattr(self.client, "exceptions", None)

            def _is_aws_exception(exception_name: str, caught_exception: Exception) -> bool:
                exception_type = getattr(aws_exceptions, exception_name, None)
                return (
                    isinstance(exception_type, type)
                    and issubclass(exception_type, BaseException)
                    and isinstance(caught_exception, exception_type)
                )

            if _is_aws_exception("ResourceNotFoundException", e):
                logger.error(f"Secret {credential_id} not found in AWS Secrets Manager")
            elif _is_aws_exception("InvalidRequestException", e):
                logger.error(f"Invalid request for secret {credential_id}: {e}")
            elif _is_aws_exception("InvalidParameterException", e):
                logger.error(f"Invalid parameter for secret {credential_id}: {e}")
            else:
                logger.error(f"Unexpected error retrieving secret {credential_id}: {e}")
            raise


class CredentialManager:
    """
    Central credential management system.

    Supports multiple credential providers (environment, AWS Secrets Manager, etc.)
    with fallback chain and caching.
    """

    def __init__(self):
        """Initialize credential manager."""
        self.providers: dict[str, CredentialProvider] = {}
        self._cache: dict[str, CredentialSet] = {}
        self.add_provider("env", EnvironmentCredentialProvider())

    def add_provider(self, name: str, provider: CredentialProvider) -> None:
        """
        Register a credential provider.

        Args:
            name: Name of the provider
            provider: CredentialProvider instance
        """
        self.providers[name] = provider
        logger.info(f"Registered credential provider: {name}")

    def add_aws_provider(self, name: str = "aws", region: str = "us-east-1") -> None:
        """
        Add AWS Secrets Manager provider.

        Args:
            name: Name for the provider
            region: AWS region
        """
        try:
            provider = AWSSecretsManagerProvider(region_name=region)
            self.add_provider(name, provider)
        except Exception as e:
            logger.error(f"Failed to add AWS provider: {e}")
            raise

    def get_credentials(
        self, credential_id: str, provider: str = "env", use_cache: bool = True
    ) -> CredentialSet:
        """
        Get credentials from specified provider.

        Args:
            credential_id: Identifier for the credentials
            provider: Name of the provider to use
            use_cache: Whether to cache credentials

        Returns:
            CredentialSet with the credentials

        Raises:
            ValueError if provider not found
            Exception if credentials cannot be retrieved
        """
        # Check cache
        cache_key = f"{provider}:{credential_id}"
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached credentials for {cache_key}")
            return self._cache[cache_key]

        # Get provider
        if provider not in self.providers:
            available = list(self.providers.keys())
            raise ValueError(
                f"Provider '{provider}' not found. " f"Available providers: {available}"
            )

        # Get credentials
        creds = self.providers[provider].get_credentials(credential_id)

        # Cache if requested
        if use_cache:
            self._cache[cache_key] = creds

        return creds

    def clear_cache(self) -> None:
        """Clear credential cache."""
        self._cache.clear()
        logger.info("Cleared credential cache")

    def test_credentials(self, credential_id: str, provider: str = "env") -> bool:
        """
        Test if credentials are valid by attempting to retrieve them.

        Args:
            credential_id: Identifier for the credentials
            provider: Name of the provider to use

        Returns:
            True if credentials can be retrieved, False otherwise
        """
        try:
            creds = self.get_credentials(credential_id, provider)

            # Check required fields
            if not creds.user or not creds.password or not creds.account:
                logger.warning(f"Missing required fields in credentials {credential_id}")
                return False

            logger.info(f"Successfully validated credentials {credential_id}")
            return True
        except Exception as e:  # noqa: BLE001 - provider backends can raise varied runtime errors
            logger.error(f"Failed to validate credentials {credential_id}: {e}")
            return False


# Global credential manager instance
_global_manager: CredentialManager | None = None


def get_credential_manager() -> CredentialManager:
    """
    Get or create the global credential manager.

    Returns:
        CredentialManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = CredentialManager()
    return _global_manager
