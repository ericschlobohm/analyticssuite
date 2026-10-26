# Snowflake Analytics Agents

A suite of AI-powered agents designed to write, review, correct, and document analytics code running on Snowflake databases.

## Features

- **Writer Agent**: Generates SQL and Python analytics code based on requirements
- **Reviewer Agent**: Analyzes code for quality, performance, and compliance issues
- **Corrector Agent**: Identifies and fixes errors in existing analytics pipelines
- **Documenter Agent**: Creates comprehensive documentation for analytics code and queries
- **Dashboard Builder Agent**: Designs and generates Tableau-like dashboard configurations
- **Dashboard Tester Agent**: Validates and tests dashboard queries and performance
- **Dashboard Export Agent**: Exports dashboard data to CSV with flexible filtering on all columns
- **Dashboard Toolkit**: Dataset-agnostic helpers (pandas + plotly) for static change-over-time HTML dashboards, with four public-data examples (CMS Medicare, CDC PLACES, CMS Care Compare, Medicaid diabetes HbA1c)
- **Claude subagents**: 31 project-level subagents in `.claude/agents/` (workflow managers, specialist writers/checkers/validators, workspace maintenance); see [.claude/agents/README.md](.claude/agents/README.md)

## Project Structure

```
analyticssuite/
├── .claude/agents/               # Claude subagent definitions + README
├── .github/copilot-instructions.md  # Subagent delegation policy
├── src/snowflake_analytics_agents/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py                    # Command-line interface
│   ├── config.py                 # Configuration management
│   ├── agents.py                 # Writer/Reviewer/Corrector/Documenter agents
│   ├── dashboard.py              # Dashboard data models
│   ├── dashboard_agents.py       # Dashboard builder/tester agents
│   ├── dashboard_export_agent.py # Dashboard CSV export agent
│   ├── dashboard_toolkit.py      # Shared plotly/pandas dashboard helpers
│   ├── export.py                 # Export filters and operators
│   ├── credentials.py            # Credential providers and manager
│   ├── snowflake_client.py       # Snowflake connection & utilities
│   └── utils.py                  # Helper functions
├── tests/
│   ├── test_agents.py
│   ├── test_credentials.py
│   ├── test_dashboards.py
│   ├── test_dashboard_toolkit.py
│   ├── test_example_cms_medicare.py
│   ├── test_examples_health_datasets.py
│   └── test_export.py
├── docs/
│   ├── architecture.md
│   ├── dashboard_toolkit.md
│   ├── AWS_SECRETS_MANAGER.md
│   ├── CREDENTIALS_IMPLEMENTATION.md
│   └── QUICK_START.md
├── examples/
│   ├── README.md
│   ├── cms_medicare/             # each dataset example: README.md, SOURCES.md,
│   ├── cdc_places/               #   *_data.py, build_dashboard.py, output/
│   ├── cms_care_compare/
│   ├── medicaid_diabetes_a1c/
│   ├── sales_dashboard_example.py
│   ├── customer_dashboard_example.py
│   ├── dashboard_examples.py
│   └── snowflake_connection_examples.py
├── data/                         # Raw dataset caches (*_raw/ folders are gitignored)
├── .env.example                  # Environment variables template
├── .gitignore
├── pyproject.toml                # Package configuration
└── README.md                     # This file
```

## Setup

### Prerequisites

- Python 3.9+
- Snowflake account with API access
- pip or conda

### Installation

1. Clone or open this repository:
   ```bash
   cd analyticssuite
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the package in development mode:
   ```bash
   pip install -e ".[dev]"
   ```

4. Copy `.env.example` to `.env` and configure:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your Snowflake credentials:
   ```
   SNOWFLAKE_ACCOUNT=your_account
   SNOWFLAKE_USER=your_user
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_DATABASE=your_database
   SNOWFLAKE_WAREHOUSE=your_warehouse
   ```

## Running

### CLI Usage

```bash
# List available agents
analytics-agents list

# Write new analytics code
analytics-agents write --description "Create a daily revenue report" --type sql

# Review existing code
analytics-agents review --file query.sql

# Correct code
analytics-agents correct --file pipeline.py

# Generate documentation
analytics-agents document --file query.sql --format markdown

# Dashboard commands
analytics-agents dashboard create --title "Sales Dashboard" --description "Company metrics"
analytics-agents dashboard test --file dashboard.json --type full
analytics-agents dashboard export --file dashboard.json --format html --output dashboard.html

# Export dashboard data to CSV with filtering
analytics-agents dashboard export-data \
  --chart-id sales_chart \
  --output sales_export.csv \
  --filter "region:equals:USA" \
  --filter "amount:gt:1000" \
  --sort-by date \
  --sort-order desc

# Preview filtered data before export
analytics-agents dashboard export-preview \
  --chart-id sales_chart \
  --filter "region:equals:USA" \
  --limit 10

# Get available columns for filtering
analytics-agents dashboard export-columns --chart-id sales_chart
```

Note: `write`, `review`, `correct` and `document` use the placeholder agents, and `dashboard test`,
`export-data`, `export-preview` and `export-columns` currently echo their arguments rather than processing a
dashboard. `dashboard create` and the Python API below are functional; `dashboard export --format html` writes a basic HTML skeleton.

### Python API

```python
from snowflake_analytics_agents import (
    WriterAgent,
    ReviewerAgent,
    DashboardBuilderAgent,
    DashboardTesterAgent,
    DashboardExportAgent,
    ColumnFilter,
    FilterOperator,
)
from snowflake_analytics_agents.config import load_config

config = load_config()
writer = WriterAgent(config)

code = writer.generate_query(
    description="Count active users by region",
    query_type="sql"
)
print(code)

# Build a dashboard
dashboard_builder = DashboardBuilderAgent(config)
dashboard = dashboard_builder.generate_dashboard(
    title="Sales Metrics",
    description="Key sales KPIs",
    requirements="Show revenue by region and daily trends",
    layout="two_column",
    num_charts=4
)

# Test the dashboard
dashboard_tester = DashboardTesterAgent(config)
validation = dashboard_tester.validate_dashboard(dashboard)
performance = dashboard_tester.check_performance(dashboard)

print(f"Dashboard valid: {validation['valid']}")
print(f"Performance score: {performance['performance_score']}/100")

# Export dashboard
dashboard_json = dashboard_builder.export_dashboard_json(dashboard)
dashboard_html = dashboard_builder.export_dashboard_html(dashboard)

# Export data from dashboard chart to CSV with filtering
export_agent = DashboardExportAgent(config)

# Export with filters
filters = [
    {"column": "region", "operator": "equals", "value": "USA"},
    {"column": "amount", "operator": "gt", "value": 1000},
]

csv_data = export_agent.export_as_csv(
    dashboard=dashboard,
    chart_id="chart_1",
    filters=filters,
    sort_by="date",
    sort_order="desc"
)

# Save to file
export_result = export_agent.export_to_file(
    dashboard=dashboard,
    chart_id="chart_1",
    filepath="sales_data.csv",
    filters=filters
)

print(f"Exported {export_result['rows_exported']} rows to {export_result['filepath']}")

# Preview filtered data
preview = export_agent.preview_filtered_data(
    dashboard=dashboard,
    chart_id="chart_1",
    filters=filters,
    limit=10
)
print(f"Preview: {preview['preview_rows']} rows (of {preview['total_rows_available']} total)")
```

## Examples

Check the [examples/](examples/README.md) directory.

**Dataset dashboards** (built with the shared [dashboard toolkit](docs/dashboard_toolkit.md); need `pandas`, `plotly`, `requests`; each folder has a `SOURCES.md`):

| Example | Run |
|---------|-----|
| [CMS Medicare GAF & payments](examples/cms_medicare/README.md) | `python examples/cms_medicare/build_dashboard.py` |
| [CDC PLACES county health](examples/cdc_places/README.md) | `python examples/cdc_places/build_dashboard.py` |
| [CMS Care Compare hospital quality](examples/cms_care_compare/README.md) | `python examples/cms_care_compare/build_dashboard.py` |
| [Medicaid diabetes HbA1c](examples/medicaid_diabetes_a1c/README.md) | `python examples/medicaid_diabetes_a1c/build_dashboard.py` |

Raw downloads are cached under `data/*_raw/` (gitignored); outputs go to each example's `output/` folder.
To add one, see [Adding a new example](examples/README.md#adding-a-new-example).

**Dashboard-config scripts:**

- **[Sales Dashboard](examples/sales_dashboard_example.py)** - Revenue metrics, trends, and performance
- **[Customer Dashboard](examples/customer_dashboard_example.py)** - Acquisition, retention, and lifetime value

```bash
python examples/sales_dashboard_example.py
python examples/customer_dashboard_example.py
```

## Development

### Running Tests

```bash
python -m pytest tests -q --no-cov
python -m pytest tests            # with coverage report (default addopts in pyproject.toml)
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type checking
mypy src/
```

### Building

```bash
pip install build
python -m build
```

## Configuration

Configuration is managed via:

1. **Environment variables** (`.env` file)
2. **Optional YAML config file** (pass path via `--config` or `load_config(config_file=...)`)
3. **Command-line flags** (for CLI behavior like `--debug`)
4. **AWS Secrets Manager** (credential provider for Snowflake connections)

Priority for config values in `load_config()`: Environment variables > YAML config file (if provided) > defaults.

AWS Secrets Manager is opt-in and used through credential APIs such as `SnowflakeClient.from_aws_secrets(...)`.

### Secure Credential Management with AWS Secrets Manager

For production deployments, use AWS Secrets Manager to securely store and retrieve Snowflake credentials without hardcoding them:

```python
from snowflake_analytics_agents import SnowflakeClient

# Create client from AWS Secrets Manager
client = SnowflakeClient.from_aws_secrets(
    secret_id="snowflake/prod/build-user",
    region="us-east-1"
)

# Use the client
results = client.execute_query("SELECT * FROM analytics_table")
client.close()
```

**Setup Instructions:**

1. Create a secret in AWS Secrets Manager:
```bash
aws secretsmanager create-secret \
    --name snowflake/prod/build-user \
    --secret-string '{
        "user": "build_user",
        "password": "YourSecurePassword",
        "account": "xy12345.us-east-1",
        "database": "analytics_db",
        "warehouse": "build_wh",
        "schema": "raw"
    }' \
    --region us-east-1
```

2. Configure AWS credentials (via environment or IAM role)

3. See [docs/AWS_SECRETS_MANAGER.md](docs/AWS_SECRETS_MANAGER.md) for detailed setup and best practices

## Documentation

See documentation files for detailed information:

- [docs/architecture.md](docs/architecture.md) - Agent design and integration patterns
- [docs/dashboard_toolkit.md](docs/dashboard_toolkit.md) - Shared dashboard toolkit API
- [docs/QUICK_START.md](docs/QUICK_START.md) - Credential quick start
- [docs/AWS_SECRETS_MANAGER.md](docs/AWS_SECRETS_MANAGER.md) - Secure credential management
- [examples/README.md](examples/README.md) - Dataset dashboards, config examples, and how to add an example
- [.claude/agents/README.md](.claude/agents/README.md) - Claude subagents

## License

MIT License (declared in `pyproject.toml`).

## Contributing

1. Create a feature branch
2. Make changes and write tests
3. Run quality checks: `black`, `ruff`, `mypy`
4. Submit a pull request

## Support

For issues or questions, contact the analytics team or check the documentation.
