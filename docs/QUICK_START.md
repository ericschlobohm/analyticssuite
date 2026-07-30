# Quick Start: AWS Secrets Manager Integration

## 60-Second Setup

### Step 1: Create AWS Secret (1 minute)

```bash
aws secretsmanager create-secret \
    --name snowflake/prod/build-user \
    --secret-string '{
        "user": "build_user",
        "password": "YourPassword123!",
        "account": "xy12345.us-east-1",
        "database": "analytics_db",
        "warehouse": "build_wh",
        "schema": "raw"
    }'
```

### Step 2: Configure AWS (if needed)

```bash
# Set environment variables
export AWS_ACCESS_KEY_ID=YOUR_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET
export AWS_DEFAULT_REGION=us-east-1

# OR use AWS CLI
aws configure
```

### Step 3: Use in Code

```python
from snowflake_analytics_agents import SnowflakeClient

# That's it! Credentials retrieved securely
with SnowflakeClient.from_aws_secrets("snowflake/prod/build-user") as client:
    results = client.execute_query("SELECT * FROM your_table")
    print(results)
```

## Common Tasks

### Check if Secret Exists
```bash
aws secretsmanager get-secret-value --secret-id snowflake/prod/build-user
```

### Update Secret
```bash
aws secretsmanager update-secret \
    --secret-id snowflake/prod/build-user \
    --secret-string '{...new credentials...}'
```

### List All Snowflake Secrets
```bash
aws secretsmanager list-secrets --filter Key=name,Values=snowflake
```

### Delete Secret
```bash
aws secretsmanager delete-secret \
    --secret-id snowflake/prod/build-user \
    --force-delete-without-recovery
```

## Development vs Production

### Development (Use Environment Variables)
```python
from snowflake_analytics_agents import SnowflakeClient

# Read from .env or env vars
client = SnowflakeClient.from_aws_secrets(
    secret_id="dummy",
    credential_provider="env"
)
```

Requires `.env` file:
```
SNOWFLAKE_USER=dev_user
SNOWFLAKE_PASSWORD=dev_password
SNOWFLAKE_ACCOUNT=dev_account.us-east-1
SNOWFLAKE_DATABASE=dev_db
SNOWFLAKE_WAREHOUSE=dev_wh
SNOWFLAKE_SCHEMA=dev_schema
```

### Production (Use AWS Secrets Manager)
```python
from snowflake_analytics_agents import SnowflakeClient

# Retrieve from AWS Secrets Manager
client = SnowflakeClient.from_aws_secrets(
    secret_id="snowflake/prod/build-user",
    region="us-east-1"
)
```

## Multi-User Setup

Different credentials for different users:

```bash
# Create read-only user
aws secretsmanager create-secret \
    --name snowflake/prod/read-only-user \
    --secret-string '{
        "user": "read_only",
        "password": "password",
        "account": "xy12345.us-east-1",
        "database": "analytics_db"
    }'

# Create admin user
aws secretsmanager create-secret \
    --name snowflake/prod/admin-user \
    --secret-string '{...}'
```

Use in code:
```python
# Build user
build_client = SnowflakeClient.from_aws_secrets("snowflake/prod/build-user")

# Read-only user
read_client = SnowflakeClient.from_aws_secrets("snowflake/prod/read-only-user")

# Admin user
admin_client = SnowflakeClient.from_aws_secrets("snowflake/prod/admin-user")
```

## Testing

### Test Credential Retrieval (No Snowflake Connection)
```python
from snowflake_analytics_agents import get_credential_manager

cred_manager = get_credential_manager()
cred_manager.add_aws_provider()

is_valid = cred_manager.test_credentials(
    "snowflake/prod/build-user",
    provider="aws"
)
print(f"Credentials valid: {is_valid}")
```

### Run Examples
```bash
python examples/snowflake_connection_examples.py
```

### Run Tests
```bash
pytest tests/test_credentials.py -v
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Unable to locate credentials" | Run `aws configure` or set AWS env vars |
| "ResourceNotFoundException" | Check secret name in AWS Secrets Manager |
| "Permission denied" | Check IAM policy has `secretsmanager:GetSecretValue` |
| "Invalid JSON" | Verify secret value is valid JSON |
| "User is empty" | Check all required fields in secret (user, password, account) |

## Security Checklist

- [ ] Credentials stored in AWS Secrets Manager (not in code)
- [ ] IAM role has minimal required permissions
- [ ] `.env` file added to `.gitignore`
- [ ] Secret rotation enabled (optional, for security)
- [ ] CloudTrail logging enabled (optional, for audit)
- [ ] Different secrets for dev/staging/prod

## File Reference

- **Implementation**: `src/snowflake_analytics_agents/credentials.py`
- **Client Factory**: `src/snowflake_analytics_agents/snowflake_client.py`
- **Examples**: `examples/snowflake_connection_examples.py`
- **Tests**: `tests/test_credentials.py`
- **Full Guide**: `docs/AWS_SECRETS_MANAGER.md`
- **Implementation Summary**: `docs/CREDENTIALS_IMPLEMENTATION.md`

## Key Files to Know

```python
from snowflake_analytics_agents import (
    SnowflakeClient,              # Use .from_aws_secrets()
    get_credential_manager,        # Advanced credential management
    CredentialSet,                 # Credential data class
    EnvironmentCredentialProvider, # Read from env vars
    AWSSecretsManagerProvider,     # Read from AWS Secrets
)
```

## Need Help?

- Quick reference: This file
- Complete guide: `docs/AWS_SECRETS_MANAGER.md`
- Examples: `python examples/snowflake_connection_examples.py`
- Test suite: `pytest tests/test_credentials.py -v`

That's it! You now have secure, production-ready credential management! 🔐
