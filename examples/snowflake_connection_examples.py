"""
Snowflake Connection Examples with AWS Secrets Manager

This module demonstrates different ways to connect to Snowflake:
1. Using environment variables
2. Using AWS Secrets Manager (production approach)
3. Using a dummy/mock Snowflake connection for testing

The build user credentials are stored in AWS Secrets Manager and
retrieved securely without hardcoding them.
"""

import logging

from snowflake_analytics_agents import (
    SnowflakeClient,
    get_credential_manager,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Environment Variable Credentials
# ============================================================================


def example_env_credentials():
    """
    Connect using credentials from environment variables.

    Requires environment variables:
    - SNOWFLAKE_USER=build_user
    - SNOWFLAKE_PASSWORD=secure_password
    - SNOWFLAKE_ACCOUNT=xy12345.us-east-1
    - SNOWFLAKE_DATABASE=analytics_db
    - SNOWFLAKE_WAREHOUSE=build_wh
    - SNOWFLAKE_SCHEMA=raw
    """
    logger.info("\n=== Example 1: Environment Variable Credentials ===\n")

    try:
        client = SnowflakeClient.from_aws_secrets(
            secret_id="dummy", credential_provider="env"  # Not used with env provider
        )

        # Test connection
        is_connected = client.test_connection()
        logger.info(f"Connection test: {'PASSED' if is_connected else 'FAILED'}")

        client.close()
        return True

    except Exception as e:  # noqa: BLE001 - example should log any failure and continue
        logger.error(f"Failed to connect with environment credentials: {e}")
        return False


# ============================================================================
# EXAMPLE 2: AWS Secrets Manager Credentials (Production)
# ============================================================================


def example_aws_secrets_credentials():
    """
    Connect using credentials stored in AWS Secrets Manager.
    
    Before running this, you need to create a secret in AWS Secrets Manager.
    
    AWS Console Steps:
    1. Go to AWS Secrets Manager
    2. Create New Secret
    3. Secret type: "Other type of secret"
    4. Secret name: snowflake/prod/build-user
    5. Key-value pairs:
       {
           "user": "build_user",
           "password": "SecurePassword123!",
           "account": "xy12345.us-east-1",
           "database": "analytics_db",
           "warehouse": "build_wh",
           "schema": "raw",
           "role": "analyst"
       }
    
    AWS CLI Alternative:
        aws secretsmanager create-secret \\
            --name snowflake/prod/build-user \\
            --secret-string '{
                "user": "build_user",
                "password": "SecurePassword123!",
                "account": "xy12345.us-east-1",
                "database": "analytics_db",
                "warehouse": "build_wh",
                "schema": "raw"
            }' \\
            --region us-east-1
    """
    logger.info("\n=== Example 2: AWS Secrets Manager Credentials ===\n")

    try:
        # Create client from AWS Secrets Manager
        client = SnowflakeClient.from_aws_secrets(
            secret_id="snowflake/prod/build-user", region="us-east-1"
        )

        # Test connection
        is_connected = client.test_connection()
        logger.info(f"Connection test: {'PASSED' if is_connected else 'FAILED'}")

        # Execute a test query
        if is_connected:
            results = client.execute_query("SELECT CURRENT_USER(), CURRENT_DATABASE()")
            logger.info(f"Query results: {results}")

        client.close()
        return True

    except Exception as e:  # noqa: BLE001 - example should log any failure and continue
        logger.warning(f"AWS Secrets Manager connection failed (expected if not configured): {e}")
        logger.info("This is normal in test environments without AWS credentials")
        return False


# ============================================================================
# EXAMPLE 3: Using Credential Manager Directly
# ============================================================================


def example_credential_manager():
    """
    Use the CredentialManager for more control and caching.
    """
    logger.info("\n=== Example 3: Credential Manager Direct Usage ===\n")

    try:
        # Get the global credential manager
        cred_manager = get_credential_manager()

        # Add AWS provider
        cred_manager.add_aws_provider(name="aws", region="us-east-1")

        # Test credentials
        is_valid = cred_manager.test_credentials(
            credential_id="snowflake/prod/build-user", provider="aws"
        )
        logger.info(f"Credentials valid: {is_valid}")

        # Get credentials with caching
        if is_valid:
            creds = cred_manager.get_credentials(
                credential_id="snowflake/prod/build-user", provider="aws", use_cache=True
            )
            logger.info(f"Retrieved credentials for user: {creds.user}")
            logger.info(f"Account: {creds.account}")
            logger.info(f"Database: {creds.database}")

        return True

    except Exception as e:  # noqa: BLE001 - example should log any failure and continue
        logger.warning(f"Credential manager test failed (expected if AWS not configured): {e}")
        return False


# ============================================================================
# EXAMPLE 4: Dummy Snowflake Connection for Testing
# ============================================================================


class DummySnowflakeConnection:
    """
    Mock Snowflake connection for testing and development.

    Use this when you don't want to connect to a real Snowflake
    instance but still want to test your code logic.
    """

    def __init__(self):
        """Initialize dummy connection with mock data."""
        self.is_connected = True
        self.queries_executed = []

    def cursor(self):
        """Return a mock cursor."""
        return DummyCursor(self)

    def close(self):
        """Close the connection."""
        self.is_connected = False


class DummyCursor:
    """Mock Snowflake cursor."""

    def __init__(self, connection):
        self.connection = connection
        self.results = []

    def execute(self, query, params=None):
        """Execute a mock query."""
        self.connection.queries_executed.append(query)

        # Return mock data based on query type
        if "SELECT 1" in query:
            self.results = [(1,)]
        elif "SELECT CURRENT_USER" in query:
            self.results = [("build_user", "analytics_db")]
        elif "DESCRIBE TABLE" in query:
            self.results = [
                ("id", "INTEGER", "COLUMN", "Y"),
                ("name", "VARCHAR", "COLUMN", "Y"),
                ("created_at", "TIMESTAMP", "COLUMN", "Y"),
            ]
        else:
            self.results = []

    def fetchall(self):
        """Fetch all results."""
        return self.results

    def close(self):
        """Close the cursor."""


def example_dummy_connection():
    """
    Demonstrate using a dummy/mock Snowflake connection for testing.

    This is useful for:
    - Unit tests
    - Development without real Snowflake access
    - CI/CD pipelines
    """
    logger.info("\n=== Example 4: Dummy Snowflake Connection ===\n")

    try:
        # Create dummy connection
        dummy_conn = DummySnowflakeConnection()

        # Test basic connection
        logger.info("Testing dummy connection...")
        cursor = dummy_conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchall()
        logger.info(f"SELECT 1 result: {result}")

        # Test user query
        cursor.execute("SELECT CURRENT_USER(), CURRENT_DATABASE()")
        result = cursor.fetchall()
        logger.info(f"User/Database: {result}")

        # Test describe table
        cursor.execute("DESCRIBE TABLE dummy_table")
        result = cursor.fetchall()
        logger.info(f"Table columns: {result}")

        logger.info(f"Total queries executed: {len(dummy_conn.queries_executed)}")

        dummy_conn.close()
        return True

    except Exception as e:  # noqa: BLE001 - example should log any failure and continue
        logger.error(f"Dummy connection test failed: {e}")
        return False


# ============================================================================
# EXAMPLE 5: Multi-User Credentials
# ============================================================================


def example_multi_user_setup():
    """
    Example showing how to manage multiple user credentials
    for different purposes (read-only, build user, admin, etc.)
    """
    logger.info("\n=== Example 5: Multi-User Credentials Setup ===\n")

    try:
        cred_manager = get_credential_manager()
        cred_manager.add_aws_provider(region="us-east-1")

        # Define different credential IDs for different purposes
        credential_sets = {
            "build_user": "snowflake/prod/build-user",
            "read_only": "snowflake/prod/read-only-user",
            "admin": "snowflake/prod/admin-user",
        }

        logger.info("Credential sets configured:")
        for name, secret_id in credential_sets.items():
            logger.info(f"  - {name}: {secret_id}")

        logger.info("\nTo use a specific credential:")
        logger.info("  client = SnowflakeClient.from_aws_secrets(")
        logger.info(f'      secret_id="{credential_sets["build_user"]}",')
        logger.info('      region="us-east-1"')
        logger.info("  )")

        return True

    except Exception as e:  # noqa: BLE001 - example should log any failure and continue
        logger.error(f"Multi-user setup failed: {e}")
        return False


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Run all connection examples."""
    logger.info("=" * 80)
    logger.info("SNOWFLAKE CONNECTION EXAMPLES")
    logger.info("=" * 80)

    results = {}

    # Run examples
    results["env"] = example_env_credentials()
    results["aws_secrets"] = example_aws_secrets_credentials()
    results["credential_manager"] = example_credential_manager()
    results["dummy"] = example_dummy_connection()
    results["multi_user"] = example_multi_user_setup()

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)

    for example, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{example:25} {status}")

    logger.info("\n" + "=" * 80)
    logger.info("SETUP INSTRUCTIONS")
    logger.info("=" * 80)

    logger.info("""
For Production Setup with AWS Secrets Manager:

1. Create an AWS Secrets Manager secret:
   
   aws secretsmanager create-secret \\
       --name snowflake/prod/build-user \\
       --secret-string '{
           "user": "build_user",
           "password": "your_secure_password",
           "account": "xy12345.us-east-1",
           "database": "analytics_db",
           "warehouse": "build_wh",
           "schema": "raw",
           "role": "analyst"
       }' \\
       --region us-east-1

2. Ensure your AWS credentials are configured:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - AWS_DEFAULT_REGION

3. Use in your code:
   
   from snowflake_analytics_agents import SnowflakeClient
   
   client = SnowflakeClient.from_aws_secrets(
       secret_id="snowflake/prod/build-user",
       region="us-east-1"
   )

4. The credentials are retrieved securely and never hardcoded!
    """)


if __name__ == "__main__":
    main()
