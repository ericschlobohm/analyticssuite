"""
Tests for AWS Secrets Manager credential integration.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from snowflake_analytics_agents.credentials import (
    AWSSecretsManagerProvider,
    CredentialManager,
    CredentialSet,
    EnvironmentCredentialProvider,
    get_credential_manager,
)


class TestCredentialSet:
    """Test CredentialSet data class."""

    def test_credential_set_creation(self):
        """Test creating a credential set."""
        creds = CredentialSet(
            user="build_user",
            password="password123",
            account="xy12345.us-east-1",
            database="analytics_db",
            warehouse="compute_wh",
            schema="raw",
            role="analyst",
        )

        assert creds.user == "build_user"
        assert creds.password == "password123"
        assert creds.account == "xy12345.us-east-1"

    def test_credential_set_to_dict(self):
        """Test converting credential set to dictionary."""
        creds = CredentialSet(
            user="build_user",
            password="password123",
            account="xy12345.us-east-1",
            database="analytics_db",
        )

        creds_dict = creds.to_dict()

        assert creds_dict["user"] == "build_user"
        assert creds_dict["password"] == "password123"
        assert creds_dict["account"] == "xy12345.us-east-1"
        assert creds_dict["database"] == "analytics_db"

    def test_credential_set_to_dict_excludes_none(self):
        """Test that to_dict excludes None values."""
        creds = CredentialSet(
            user="build_user",
            password="password123",
            account="xy12345.us-east-1",
            database=None,  # None value
        )

        creds_dict = creds.to_dict()

        assert "database" not in creds_dict
        assert len(creds_dict) == 3


class TestEnvironmentCredentialProvider:
    """Test environment variable credential provider."""

    @patch.dict(
        "os.environ",
        {
            "SNOWFLAKE_USER": "env_user",
            "SNOWFLAKE_PASSWORD": "env_pass",
            "SNOWFLAKE_ACCOUNT": "env_account",
        },
    )
    def test_get_credentials_from_env(self):
        """Test retrieving credentials from environment variables."""
        provider = EnvironmentCredentialProvider()
        creds = provider.get_credentials()

        assert creds.user == "env_user"
        assert creds.password == "env_pass"
        assert creds.account == "env_account"

    @patch.dict(
        "os.environ",
        {
            "SNOWFLAKE_USER": "user",
            "SNOWFLAKE_PASSWORD": "pass",
            "SNOWFLAKE_ACCOUNT": "account",
            "SNOWFLAKE_DATABASE": "db",
            "SNOWFLAKE_WAREHOUSE": "wh",
        },
        clear=True,
    )
    def test_get_credentials_with_optional_fields(self):
        """Test retrieving credentials with optional fields."""
        provider = EnvironmentCredentialProvider()
        creds = provider.get_credentials()

        assert creds.database == "db"
        assert creds.warehouse == "wh"
        assert creds.schema is None


class TestAWSSecretsManagerProvider:
    """Test AWS Secrets Manager credential provider."""

    @patch("snowflake_analytics_agents.credentials.boto3")
    def test_initialize_client(self, mock_boto3):
        """Test initializing AWS Secrets Manager client."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider(region_name="us-west-2")

        assert provider.client == mock_client
        mock_boto3.client.assert_called_once_with("secretsmanager", region_name="us-west-2")

    @patch("snowflake_analytics_agents.credentials.boto3")
    def test_get_credentials_from_aws(self, mock_boto3):
        """Test retrieving credentials from AWS Secrets Manager."""
        mock_client = MagicMock()
        secret_data = {
            "user": "build_user",
            "password": "secure_pass",
            "account": "xy12345.us-east-1",
            "database": "analytics_db",
            "warehouse": "build_wh",
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()
        creds = provider.get_credentials("snowflake/prod/build-user")

        assert creds.user == "build_user"
        assert creds.password == "secure_pass"
        assert creds.account == "xy12345.us-east-1"
        assert creds.database == "analytics_db"

    @patch("snowflake_analytics_agents.credentials.boto3")
    def test_get_credentials_missing_required_field(self, mock_boto3):
        """Test error when required fields are missing."""
        mock_client = MagicMock()
        secret_data = {
            "user": "build_user",
            # Missing password and account
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()

        with pytest.raises(ValueError, match="missing required fields"):
            provider.get_credentials("snowflake/prod/build-user")

    @patch("snowflake_analytics_agents.credentials.boto3")
    def test_get_credentials_invalid_json(self, mock_boto3):
        """Test error when secret is not valid JSON."""
        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = {"SecretString": "not valid json {"}
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()

        with pytest.raises(ValueError, match="must be a JSON object"):
            provider.get_credentials("snowflake/prod/build-user")

    @patch("snowflake_analytics_agents.credentials.boto3")
    def test_get_credentials_secret_not_found(self, mock_boto3):
        """Test error when secret is not found."""
        mock_client = MagicMock()

        class ResourceNotFoundException(Exception):
            pass

        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundException
        mock_client.get_secret_value.side_effect = (
            mock_client.exceptions.ResourceNotFoundException()
        )
        mock_boto3.client.return_value = mock_client

        provider = AWSSecretsManagerProvider()

        with pytest.raises(ResourceNotFoundException):
            provider.get_credentials("nonexistent/secret")


class TestCredentialManager:
    """Test credential manager."""

    def test_create_credential_manager(self):
        """Test creating credential manager."""
        manager = CredentialManager()

        assert manager is not None
        assert "env" in manager.providers

    def test_add_provider(self):
        """Test adding a provider."""
        manager = CredentialManager()
        mock_provider = MagicMock()

        manager.add_provider("test_provider", mock_provider)

        assert "test_provider" in manager.providers

    @patch.dict(
        "os.environ",
        {
            "SNOWFLAKE_USER": "test_user",
            "SNOWFLAKE_PASSWORD": "test_pass",
            "SNOWFLAKE_ACCOUNT": "test_account",
        },
    )
    def test_get_credentials_env_provider(self):
        """Test getting credentials from env provider."""
        manager = CredentialManager()
        creds = manager.get_credentials("test", provider="env")

        assert creds.user == "test_user"

    @patch("snowflake_analytics_agents.credentials.boto3")
    def test_add_aws_provider(self, mock_boto3):
        """Test adding AWS provider."""
        mock_boto3.client.return_value = MagicMock()

        manager = CredentialManager()
        manager.add_aws_provider(region="us-west-2")

        assert "aws" in manager.providers

    def test_get_credentials_with_cache(self):
        """Test credential caching."""
        manager = CredentialManager()
        mock_provider = MagicMock()
        mock_creds = CredentialSet(user="test", password="pass", account="account")
        mock_provider.get_credentials.return_value = mock_creds

        manager.add_provider("mock", mock_provider)

        # First call
        creds1 = manager.get_credentials("test_id", provider="mock", use_cache=True)
        # Second call (should use cache)
        creds2 = manager.get_credentials("test_id", provider="mock", use_cache=True)

        assert creds1 == creds2
        # Provider should only be called once
        mock_provider.get_credentials.assert_called_once()

    def test_clear_cache(self):
        """Test clearing credential cache."""
        manager = CredentialManager()
        mock_provider = MagicMock()
        mock_creds = CredentialSet(user="test", password="pass", account="account")
        mock_provider.get_credentials.return_value = mock_creds

        manager.add_provider("mock", mock_provider)

        # Cache credentials
        manager.get_credentials("test_id", provider="mock", use_cache=True)

        # Clear cache
        manager.clear_cache()

        # Get credentials again (should call provider again)
        manager.get_credentials("test_id", provider="mock", use_cache=True)

        assert mock_provider.get_credentials.call_count == 2

    def test_test_credentials_valid(self):
        """Test testing valid credentials."""
        manager = CredentialManager()
        mock_provider = MagicMock()
        mock_creds = CredentialSet(user="test", password="pass", account="account")
        mock_provider.get_credentials.return_value = mock_creds

        manager.add_provider("mock", mock_provider)

        result = manager.test_credentials("test_id", provider="mock")

        assert result is True

    def test_test_credentials_invalid(self):
        """Test testing invalid credentials."""
        manager = CredentialManager()
        mock_provider = MagicMock()
        mock_provider.get_credentials.side_effect = Exception("Test error")

        manager.add_provider("mock", mock_provider)

        result = manager.test_credentials("test_id", provider="mock")

        assert result is False

    def test_provider_not_found(self):
        """Test error when provider not found."""
        manager = CredentialManager()

        with pytest.raises(ValueError, match="Provider 'nonexistent' not found"):
            manager.get_credentials("test", provider="nonexistent")

    def test_get_global_credential_manager(self):
        """Test getting global credential manager."""
        manager1 = get_credential_manager()
        manager2 = get_credential_manager()

        assert manager1 is manager2


class TestSnowflakeClientWithCredentials:
    """Test SnowflakeClient with credential management."""

    @patch("snowflake_analytics_agents.snowflake_client.snowflake.connector.connect")
    @patch("snowflake_analytics_agents.credentials.boto3")
    def test_from_aws_secrets(self, mock_boto3, mock_snowflake_connect):
        """Test creating SnowflakeClient from AWS secrets."""
        # Setup AWS Secrets Manager mock
        mock_client = MagicMock()
        secret_data = {
            "user": "build_user",
            "password": "secure_pass",
            "account": "xy12345.us-east-1",
            "database": "analytics_db",
            "warehouse": "build_wh",
            "schema": "raw",
        }
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}
        mock_boto3.client.return_value = mock_client

        # Setup Snowflake mock
        mock_connection = MagicMock()
        mock_snowflake_connect.return_value = mock_connection

        # Import here to avoid circular imports
        from snowflake_analytics_agents import SnowflakeClient

        client = SnowflakeClient.from_aws_secrets(secret_id="snowflake/prod/build-user")

        assert client is not None
        mock_snowflake_connect.assert_called_once()

    @patch("snowflake_analytics_agents.snowflake_client.snowflake.connector.connect")
    @patch.dict(
        "os.environ",
        {
            "SNOWFLAKE_USER": "env_user",
            "SNOWFLAKE_PASSWORD": "env_pass",
            "SNOWFLAKE_ACCOUNT": "env_account",
        },
    )
    def test_from_aws_secrets_env_provider(self, mock_snowflake_connect):
        """Test creating SnowflakeClient using environment provider."""
        mock_connection = MagicMock()
        mock_snowflake_connect.return_value = mock_connection

        from snowflake_analytics_agents import SnowflakeClient

        client = SnowflakeClient.from_aws_secrets(secret_id="dummy", credential_provider="env")

        assert client is not None
        # Check that env credentials were used
        call_kwargs = mock_snowflake_connect.call_args[1]
        assert call_kwargs["user"] == "env_user"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
