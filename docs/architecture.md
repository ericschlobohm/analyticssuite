# Snowflake Analytics Agents - Architecture & Design

## Overview

This document describes the architecture, design patterns, and workflow for the Snowflake Analytics Agents suite.

Note: the Python agent classes currently return placeholder output (no LLM call); the roles below describe the
intended behavior and the public interfaces. The dashboard models, export filtering, credential providers and
`dashboard_toolkit` are fully implemented.
## Agent Roles

### 1. Writer Agent
**Purpose**: Generate new analytics code based on natural language requirements

**Responsibilities**:
- Interpret business requirements
- Generate optimized SQL queries or Python code
- Support parameterized queries
- Generate code templates for common patterns

**Inputs**:
- Natural language description
- Target code type (SQL, Python)
- Optional context (schema info, existing code patterns)

**Outputs**:
- Complete, ready-to-test code
- Code with comments explaining logic
- Alternative implementations if requested

**Example Workflow**:
```
User: "Create a daily revenue report by region"
  ↓
WriterAgent: Connects to Snowflake, introspects schema, generates:
  ↓
SELECT 
  region,
  DATE(order_date) as report_date,
  SUM(amount) as total_revenue
FROM orders
GROUP BY region, DATE(order_date)
```

---

### 2. Reviewer Agent
**Purpose**: Review code quality, performance, and best practices

**Responsibilities**:
- Check SQL syntax and query plans
- Identify performance issues
- Verify Snowflake best practices
- Check for security issues
- Validate code style

**Checks Performed**:
- **Performance**: Missing indexes, full table scans, suboptimal joins
- **Compatibility**: Snowflake-specific syntax, deprecated functions
- **Security**: Hardcoded credentials, unvalidated inputs
- **Maintainability**: Formatting, naming conventions, documentation
- **Cost**: Scan volume, compute resources

**Inputs**:
- Code (SQL or Python)
- Optional: Query execution plan
- Optional: Test data sample

**Outputs**:
- Issue list with severity levels
- Performance metrics
- Improvement suggestions
- Overall quality score

**Example Output**:
```
Review Results:
  Score: 72/100

Issues:
  - Missing WHERE clause can cause full table scan (HIGH)
  - Consider partitioning by date (MEDIUM)

Warnings:
  - Column name doesn't follow naming convention (LOW)

Suggestions:
  - Add CLUSTER BY order_date for better performance
  - Consider materialized view for frequently accessed data
```

---

### 3. Corrector Agent
**Purpose**: Fix errors in existing analytics code

**Responsibilities**:
- Fix syntax errors
- Correct logic errors based on error messages
- Optimize underperforming queries
- Update deprecated functions
- Handle schema changes

**Triggers**:
- Execution failures
- Performance degradation
- Schema changes
- Manual correction requests

**Inputs**:
- Problematic code
- Error message (if available)
- Context about the failure
- Snowflake error logs

**Outputs**:
- Corrected code
- Explanation of the fix
- Validation that fix is correct

**Example**:
```
Input:  SELECT * FROM users WHER age > 18;
Error:  SQL compilation error: syntax error
  ↓
CorrectorAgent detects missing 'E' in WHERE
  ↓
Output: SELECT * FROM users WHERE age > 18;
```

---

### 4. Documenter Agent
**Purpose**: Generate documentation for analytics code

**Responsibilities**:
- Extract code purpose and logic
- Generate inline comments
- Create API/parameter documentation
- Generate business logic documentation
- Build data dictionaries

**Documentation Types**:
- **Inline**: Comments explaining complex logic
- **Markdown**: Standalone documentation files
- **Docstrings**: Python function/class documentation
- **HTML**: Web-viewable documentation

**Inputs**:
- Code file
- Optional: Query plan and statistics
- Optional: Business context

**Outputs**:
- Well-documented code
- Standalone documentation
- Data dictionary (columns, types, descriptions)

**Example**:
```python
def calculate_customer_ltv(customer_id: int) -> float:
    """
    Calculate the lifetime value of a customer.
    
    This query:
    1. Sums all revenue from completed orders
    2. Excludes refunded transactions
    3. Includes projected future orders
    
    Args:
        customer_id: The ID of the customer
        
    Returns:
        Total lifetime value in USD
        
    Dependencies:
        - orders table
        - customers table
        - refunds table
    """
    # Implementation here
```

---

### 5. Dashboard Builder Agent
**Purpose**: Generate Tableau-like dashboard configurations

**Responsibilities**:
- Design dashboard layouts based on requirements
- Generate chart configurations
- Create filter configurations
- Suggest optimal chart types for data
- Export dashboards as JSON or HTML

**Inputs**:
- Dashboard requirements (natural language or structured)
- Data schema information
- Layout preferences (columns, theme, etc.)
- Performance constraints

**Outputs**:
- Dashboard configuration (DashboardConfig object)
- JSON representation for storage
- HTML template for visualization
- Chart and filter specifications

**Example**:
```
User: "Create a sales dashboard with revenue by region, daily trends, and top customers"
  ↓
DashboardBuilderAgent generates:
  - Chart 1: Bar chart - Revenue by Region
  - Chart 2: Line chart - Daily Revenue Trend
  - Chart 3: Table - Top 10 Customers
  - Filters: Date Range, Region Selector
```

---

### 6. Dashboard Tester Agent
**Purpose**: Validate and test dashboard configurations

**Responsibilities**:
- Validate dashboard structure and configuration
- Test all queries in dashboard charts
- Check performance characteristics
- Identify missing or invalid data references
- Generate comprehensive test reports

**Validation Checks**:
- **Structure**: Chart IDs, required fields, layout validity
- **Queries**: SQL syntax, column references, data availability
- **Performance**: Query complexity, refresh intervals, estimated load
- **UX**: Number of charts, filter effectiveness, refresh frequency

**Test Types**:
- **Validation**: Configuration and structure checks
- **Query Tests**: Execute all chart queries against Snowflake
- **Performance Analysis**: Estimate load times and resource usage
- **Full Report**: Comprehensive testing with recommendations

**Inputs**:
- DashboardConfig to test
- Optional: Snowflake connection for live testing
- Optional: Performance thresholds

**Outputs**:
- Validation results with issues and warnings
- Query test results with row counts
- Performance scores and recommendations
- Comprehensive test report

**Example Report**:
```
=== DASHBOARD TEST REPORT ===
Dashboard: Sales Analysis
- Validation: PASS (0 issues, 1 warning)
- Query Tests: 3/3 PASS
- Performance: GOOD (Score: 85/100)

Recommendations:
✓ Dashboard is ready for production
⚠ Consider optimizing complex JOIN queries
```

---

## Workflow Integration

### Typical Analytics Development Workflow

```
1. WRITE PHASE
   User provides requirements
        ↓
   WriterAgent generates initial code
        ↓
   Code is reviewed by developer

2. REVIEW PHASE
   Developer runs code against test data
        ↓
   ReviewerAgent identifies issues
        ↓
   Developer decides on improvements

3. CORRECT PHASE
   If execution fails:
        ↓
   CorrectorAgent fixes issues
        ↓
   Re-test and validate

4. DOCUMENT PHASE
   Code is production-ready
        ↓
   DocumenterAgent generates documentation
        ↓
   Documentation is added to wiki/repo

5. ITERATE PHASE
   When schema changes or optimization needed
        ↓
   Repeat from REVIEW or CORRECT phase
```

### Multi-Agent Orchestration

For complex projects, agents can work together:

```
WriterAgent generates code for new data pipeline
    ↓
ReviewerAgent checks code quality
    ↓
If issues: CorrectorAgent fixes them
    ↓
ReviewerAgent validates fixes
    ↓
DocumenterAgent creates documentation
    ↓
Code ready for production
```

### Dashboard Development Workflow

```
1. DESIGN PHASE
   User describes dashboard requirements
        ↓
   DashboardBuilderAgent generates layout and charts
        ↓
   Dashboard preview created

2. BUILD PHASE
   WriterAgent generates optimal SQL for each chart
        ↓
   Charts are added to dashboard configuration
        ↓
   Filters and interactivity defined

3. TEST PHASE
   DashboardTesterAgent validates configuration
        ↓
   Query tests executed against test data
        ↓
   Performance analysis performed

4. OPTIMIZE PHASE
   If performance issues:
        ↓
   CorrectorAgent optimizes queries
        ↓
   DashboardTesterAgent re-validates
        ↓

5. DEPLOY PHASE
   Dashboard exported as JSON/HTML
        ↓
   Web app renders dashboard
        ↓
   Live analytics available to users
```

### Claude subagent workflow

The Python agents above are mirrored by project-level Claude subagents in `.claude/agents/`
(see [.claude/agents/README.md](../.claude/agents/README.md)). Start with a wrapper such as
`analytics-workflow-manager` or `dashboard-workflow-manager`; it routes to creators, runs checkers/validators
and loops failures back to the creator (max 3 iterations).

---

## Dashboard toolkit and dataset examples

`src/snowflake_analytics_agents/dashboard_toolkit.py` is a separate, dataset-agnostic layer (pandas + plotly) for
static, change-over-time HTML dashboards. It does not use Snowflake or the agent classes. Each dataset example under
`examples/` (`cms_medicare`, `cdc_places`, `cms_care_compare`, `medicaid_diabetes_a1c`) supplies a loader module
and a `build_dashboard.py` that calls the toolkit. See [dashboard_toolkit.md](dashboard_toolkit.md) and
[examples/README.md](../examples/README.md).

---

## Configuration & Customization

Settings come from `load_config()` (`config.py`): environment variables, then an optional YAML file, then defaults.

### Agent configuration
```yaml
agents:
  timeout: 300      # seconds (AGENT_TIMEOUT)
  max_retries: 3    # AGENT_MAX_RETRIES
  debug: false      # DEBUG
  log_level: INFO   # LOG_LEVEL
```

### Snowflake connection
```yaml
snowflake:
  account: my_account
  warehouse: compute_wh
  database: analytics
  schema: PUBLIC
  # optional: role, region
```

Each field can be overridden by `SNOWFLAKE_<FIELD>` environment variables (e.g. `SNOWFLAKE_ACCOUNT`). Credentials
can also come from AWS Secrets Manager; see [AWS_SECRETS_MANAGER.md](AWS_SECRETS_MANAGER.md).

---

## Extension Points

All agents subclass `BaseAgent` (`agents.py`) and implement `execute(...)`.

- **New agent**: subclass `BaseAgent`, implement `execute`, export it from `__init__.py`, add tests in `tests/`.
- **Review checks**: `ReviewerAgent.review_code(code, code_type, checks=[...])` accepts a list of checks to run.
- **Credentials**: implement `CredentialProvider` (`credentials.py`) and register it with `CredentialManager.add_provider(name, provider)`.
- **New dataset dashboard**: add an example folder (see [examples/README.md](../examples/README.md#adding-a-new-example)).
- **New Claude subagent**: add a `.claude/agents/<name>.md` file and list it in `.claude/agents/README.md`.

---

## Security Considerations

- Snowflake credentials come from environment variables / `.env` (gitignored) or AWS Secrets Manager; never
  hardcode them. See [AWS_SECRETS_MANAGER.md](AWS_SECRETS_MANAGER.md).
- Generated code should use parameterized queries and validate user input.
- `analytics-security-reviewer` (Claude subagent) audits code for credential leaks and injection risks.
- Dashboard toolkit HTML escapes titles, headings and KPI text; `kpis_html`/`notes_html` are trusted fragments.

---

## Testing Strategy

Run `python -m pytest tests -q --no-cov` (coverage is enabled by default through `pyproject.toml`).

| Test file | Covers |
|-----------|--------|
| `test_agents.py` | Writer/Reviewer/Corrector/Documenter agents |
| `test_dashboards.py` | Dashboard models, builder and tester agents |
| `test_export.py` | Export filters and `DashboardExportAgent` |
| `test_credentials.py` | Credential providers and manager |
| `test_dashboard_toolkit.py` | Shared dashboard toolkit |
| `test_example_cms_medicare.py` | CMS Medicare calculations (offline) |
| `test_examples_health_datasets.py` | PLACES, Care Compare, Medicaid cleaning/aggregation and `SOURCES.md` presence |

Tests are offline; Snowflake and network access are not required.

---

## Future Enhancements

1. **Multi-Language Support**: dbt, Scala
2. **LLM-backed agents**: `WriterAgent`, `ReviewerAgent`, `CorrectorAgent` and `DocumenterAgent` are currently
   placeholders (templates / empty review results) with the interfaces described above
3. **Real dashboard rendering and export in the CLI**: `dashboard test`, `export-data`, `export-preview` and
   `export-columns` are currently placeholders that echo their arguments
