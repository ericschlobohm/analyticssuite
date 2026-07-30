# AWS Secrets Manager Integration Guide

## Overview

The Snowflake Analytics Agents platform includes secure credential management using AWS Secrets Manager. This allows build user credentials to be stored securely without hardcoding them in code or environment files.

## Architecture

### Credential Flow

```
┌─────────────────┐
│  AWS Secrets    │
│    Manager      │
└────────┬────────┘
         │ (secure retrieval)
         ▼
┌─────────────────────────────┐
│ AWSSecretsManagerProvider   │
│ (boto3 client)              │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│   CredentialManager         │
│   (caching & routing)       │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  SnowflakeClient            │
│  (connection pool)          │
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Snowflake Database         │
└─────────────────────────────┘
```

### Components

1. **CredentialProvider** (Abstract Base Class)
   - Base interface for all credential sources
   - Implementations: `EnvironmentCredentialProvider`, `AWSSecretsManagerProvider`

2. **CredentialSet**
   - Data class holding Snowflake credentials
   - Fields: user, password, account, database, warehouse, schema, role, region

3. **CredentialManager**
   - Central management system for credentials
   - Supports multiple providers and fallback chains
   - Built-in caching to reduce API calls

4. **AWSSecretsManagerProvider**
   - Retrieves credentials from AWS Secrets Manager
   - Handles JSON parsing and error handling
   - Supports region configuration

5. **SnowflakeClient.from_aws_secrets()**
   - Factory method for creating clients from AWS secrets
   - Automatically sets up credential provider and retrieves credentials

## Setup Instructions

### Step 1: Create AWS Secrets Manager Secret

#### Using AWS Console:

1. Navigate to AWS Secrets Manager
2. Click "Store a new secret"
3. Select "Other type of secret"
4. Enter secret name: `snowflake/prod/build-user`
5. Add key-value pairs:

```json
{
    "user": "build_user",
    "password": "YourSecurePassword123!",
    "account": "xy12345.us-east-1",
    "database": "analytics_db",
    "warehouse": "build_wh",
    "schema": "raw",
    "role": "analyst"
}
```

6. Click "Store secret"

#### Using AWS CLI:

```bash
aws secretsmanager create-secret \
    --name snowflake/prod/build-user \
    --secret-string '{
        "user": "build_user",
        "password": "YourSecurePassword123!",
        "account": "xy12345.us-east-1",
        "database": "analytics_db",
        "warehouse": "build_wh",
        "schema": "raw",
        "role": "analyst"
    }' \
    --region us-east-1
```

### Step 2: Configure AWS Credentials

Ensure your AWS credentials are configured. You can do this in several ways:

#### Option A: AWS Credentials File (~/.aws/credentials)
```
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

#### Option B: Environment Variables
```bash
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

#### Option C: IAM Role (Recommended for Production)
- Attach IAM role to EC2/Lambda/ECS task
- Role policy includes `secretsmanager:GetSecretValue`

### Step 3: Install Dependencies

```bash
# Install snowflake-analytics-agents with AWS support
pip install -e ".[dev]"

# This includes boto3 for AWS Secrets Manager access
```

### Step 4: Use in Your Code

```python
from snowflake_analytics_agents import SnowflakeClient

# Create client from AWS Secrets Manager
client = SnowflakeClient.from_aws_secrets(
    secret_id="snowflake/prod/build-user",
    region="us-east-1"
)

# Use the client
try:
    is_connected = client.test_connection()
    if is_connected:
        results = client.execute_query("SELECT * FROM my_table LIMIT 10")
        print(results)
finally:
    client.close()
```

## Usage Examples

### Basic Connection

```python
from snowflake_analytics_agents import SnowflakeClient

# Connect using AWS Secrets Manager
client = SnowflakeClient.from_aws_secrets(
    secret_id="snowflake/prod/build-user"
)

# Execute query
results = client.execute_query("SELECT COUNT(*) FROM users")
print(results)

client.close()
```

### Using with Context Manager

```python
from snowflake_analytics_agents import SnowflakeClient

# Automatically closes connection
with SnowflakeClient.from_aws_secrets("snowflake/prod/build-user") as client:
    results = client.execute_query("SELECT * FROM sales LIMIT 100")
    print(results)
```

### Direct Credential Manager Usage

```python
from snowflake_analytics_agents import get_credential_manager

# Get global credential manager
cred_manager = get_credential_manager()

# Add AWS provider
cred_manager.add_aws_provider(region="us-east-1")

# Test credentials
if cred_manager.test_credentials("snowflake/prod/build-user", provider="aws"):
    # Get credentials (cached after first call)
    creds = cred_manager.get_credentials(
        "snowflake/prod/build-user",
        provider="aws"
    )
    print(f"User: {creds.user}")
    print(f"Database: {creds.database}")
```

### Multiple User Accounts

```python
from snowflake_analytics_agents import SnowflakeClient

# Different credentials for different purposes
users = {
    "build_user": "snowflake/prod/build-user",
    "read_only": "snowflake/prod/read-only-user",
    "admin": "snowflake/prod/admin-user",
}

# Create clients for different users
for user_name, secret_id in users.items():
    client = SnowflakeClient.from_aws_secrets(secret_id)
    print(f"Connected as {user_name}: {client.test_connection()}")
    client.close()
```

### Environment Variable Fallback

```python
from snowflake_analytics_agents import SnowflakeClient

# Try AWS Secrets first, fall back to environment variables
try:
    client = SnowflakeClient.from_aws_secrets("snowflake/prod/build-user")
except Exception as e:
    print(f"AWS Secrets failed: {e}, trying environment variables...")
    client = SnowflakeClient.from_aws_secrets("dummy", credential_provider="env")

print(f"Connected: {client.test_connection()}")
client.close()
```

## IAM Policy for Production

For production deployments, create an IAM policy that restricts access to specific secrets:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret"
            ],
            "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:snowflake/prod/*"
        }
    ]
}
```

## Secret Naming Convention

Recommended naming scheme for organizing secrets:

```
snowflake/environment/user-type/purpose
```

Examples:
- `snowflake/prod/build-user` - Production build user
- `snowflake/prod/read-only-user` - Production read-only user
- `snowflake/dev/build-user` - Development build user
- `snowflake/staging/admin-user` - Staging admin user
- `snowflake/test/test-user` - Testing user

## Credential Management Best Practices

### 1. Separate Credentials by Role

Create different secrets for different access levels:

```python
credentials = {
    "build": "snowflake/prod/build-user",      # Can write, transform
    "analyst": "snowflake/prod/analyst-user",  # Read-only, dashboards
    "admin": "snowflake/prod/admin-user",      # Full access
}
```

### 2. Rotate Credentials Regularly

```bash
# Update secret in AWS Secrets Manager
aws secretsmanager update-secret \
    --secret-id snowflake/prod/build-user \
    --secret-string '{...new credentials...}'
```

### 3. Use Least Privilege

- Build user: Only needs permission to create/modify tables in specific schemas
- Analyst user: Read-only access to necessary tables
- Admin user: Full access (sparingly used)

### 4. Enable Secret Rotation

In AWS Secrets Manager, enable automatic rotation:

```bash
aws secretsmanager rotate-secret \
    --secret-id snowflake/prod/build-user \
    --rotation-rules AutomaticallyAfterDays=30
```

### 5. Audit Access

Monitor who accesses secrets:

```bash
# View secret access history
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=ResourceName,AttributeValue=snowflake/prod/build-user
```

## Troubleshooting

### Error: "User is empty"

**Cause**: Snowflake credentials not properly loaded

**Solution**:
```python
# Check if secret exists
aws secretsmanager get-secret-value --secret-id snowflake/prod/build-user

# Verify credentials format is valid JSON
aws secretsmanager get-secret-value \
    --secret-id snowflake/prod/build-user \
    --query SecretString \
    --output text | python -m json.tool
```

### Error: "ResourceNotFoundException"

**Cause**: Secret name doesn't exist in AWS Secrets Manager

**Solution**:
```python
# List available secrets
aws secretsmanager list-secrets --filter Key=name,Values=snowflake

# Create the secret if it doesn't exist
aws secretsmanager create-secret \
    --name snowflake/prod/build-user \
    --secret-string '{...}'
```

### Error: "InvalidRequestException"

**Cause**: Credentials format is invalid

**Solution**:
```python
# Verify the JSON is valid
import json
secret_json = '{"user": "...", "password": "...", ...}'
try:
    json.loads(secret_json)
    print("JSON is valid")
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
```

### Error: "User doesn't have permission"

**Cause**: IAM role doesn't have `secretsmanager:GetSecretValue` permission

**Solution**: Attach the IAM policy with required permissions (see above)

## Testing Credentials

```python
from snowflake_analytics_agents import get_credential_manager

cred_manager = get_credential_manager()
cred_manager.add_aws_provider()

# Test credentials without connecting to Snowflake
if cred_manager.test_credentials("snowflake/prod/build-user", provider="aws"):
    print("Credentials retrieved successfully!")
    creds = cred_manager.get_credentials("snowflake/prod/build-user", provider="aws")
    print(f"User: {creds.user}")
    print(f"Account: {creds.account}")
else:
    print("Failed to retrieve credentials")
```

## Performance Considerations

### Credential Caching

Credentials are cached after first retrieval to reduce API calls:

```python
# First call: retrieves from AWS Secrets Manager
creds1 = cred_manager.get_credentials("snowflake/prod/build-user", use_cache=True)

# Second call: uses cached credentials
creds2 = cred_manager.get_credentials("snowflake/prod/build-user", use_cache=True)

# Clear cache manually if needed
cred_manager.clear_cache()
```

### Connection Pooling

Use connection contexts for better resource management:

```python
# Good: Automatically closes connection
with SnowflakeClient.from_aws_secrets("snowflake/prod/build-user") as client:
    results = client.execute_query("SELECT 1")

# Also good: Explicit close
client = SnowflakeClient.from_aws_secrets("snowflake/prod/build-user")
try:
    results = client.execute_query("SELECT 1")
finally:
    client.close()
```

## Migration from Hardcoded Credentials

### Before (Not Secure)
```python
# ❌ DO NOT DO THIS
from snowflake_analytics_agents import load_config

config = load_config()  # Uses .env file with hardcoded password
client = SnowflakeClient(config.snowflake)
```

### After (Secure)
```python
# ✓ SECURE
from snowflake_analytics_agents import SnowflakeClient

client = SnowflakeClient.from_aws_secrets("snowflake/prod/build-user")
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Analytics Pipeline

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Run analytics agents
        run: |
          pip install -e ".[dev]"
          python examples/snowflake_connection_examples.py
```

### GitLab CI Example

```yaml
stages:
  - test

build_analytics:
  stage: test
  script:
    - pip install -e ".[dev]"
    - AWS_ACCESS_KEY_ID=$AWS_KEY
    - AWS_SECRET_ACCESS_KEY=$AWS_SECRET
    - python examples/snowflake_connection_examples.py
  only:
    - main
```

## See Also

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [Snowflake Connector Python](https://docs.snowflake.com/en/user-guide/python-connector.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
