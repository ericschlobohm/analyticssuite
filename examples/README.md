# Examples

This directory contains two kinds of examples:

1. **Dataset dashboards** (recommended starting point): four folders that turn public data into static HTML
   dashboards using the shared [`dashboard_toolkit`](../docs/dashboard_toolkit.md).
2. **Dashboard-config scripts**: `sales_dashboard_example.py`, `customer_dashboard_example.py`,
   `dashboard_examples.py` and `snowflake_connection_examples.py`, which use the Snowflake agent classes.

## Dataset examples

Prerequisites: `pip install -e ".[dev]"` plus `pip install pandas plotly requests` (not yet declared in
`pyproject.toml`). Run all commands from the repository root; scripts locate `data/` and `output/` themselves.

| Folder | What it shows | Run | Raw cache (gitignored) | Output |
|--------|---------------|-----|------------------------|--------|
| [cms_medicare/](cms_medicare/README.md) | Medicare GAF and fee-schedule payments, CY2022–CY2026 | `python examples/cms_medicare/build_dashboard.py` | `data/cms_raw/` | `output/dashboard.html`, CSVs, `dashboard_config.json` |
| [cdc_places/](cdc_places/README.md) | County chronic-disease prevalence 2019–2023 | `python examples/cdc_places/build_dashboard.py` | `data/cdc_places_raw/` | `output/dashboard.html` (gitignored), CSVs |
| [cms_care_compare/](cms_care_compare/README.md) | Hospital star ratings and readmissions (current snapshot) | `python examples/cms_care_compare/build_dashboard.py` | `data/care_compare_raw/` | `output/dashboard.html`, `state_summary.csv` |
| [medicaid_diabetes_a1c/](medicaid_diabetes_a1c/README.md) | Medicaid diabetes HbA1c poor control by state, 2020–2024 (type 1 + type 2 combined) | `python examples/medicaid_diabetes_a1c/build_dashboard.py` | `data/medicaid_raw/` | `output/dashboard.html`, CSVs |

The first run downloads data (network required); later runs reuse the cache. Open `output/dashboard.html` in a browser.

Each folder contains `README.md`, `SOURCES.md`, a `*_data.py` loader, `build_dashboard.py` and `output/`.
**Convention:** every example folder must have a `SOURCES.md` linking to all data sources and references it uses
(checked by `tests/test_examples_health_datasets.py`).

### Adding a new example

1. Create `examples/<name>/` with:
   * `<name>_data.py`: downloads/caches raw files under `data/<name>_raw/` and returns cleaned long-format
     (key, year, value) frames. Reuse `download_zip` for zip archives; send a `User-Agent` header if the site rejects defaults.
   * `build_dashboard.py`: computes `first_last_change`, builds figures with the toolkit
     (`choropleth_change`, `bar_extremes`, `indexed_lines`, `table_figure`), then writes
     `output/dashboard.html` via `render_html` (plus any CSVs). Copy the `ROOT`/`RAW_DIR`/`OUT_DIR` pattern from an existing example.
   * `README.md` (run command, files table, method and caveats) and `SOURCES.md` (links to every source).
2. Add `data/<name>_raw/` to `.gitignore` (and any generated output you do not want to commit).
3. Add offline unit tests under `tests/` (see `tests/test_examples_health_datasets.py`) and add the folder name to
   the `test_every_example_lists_sources` parametrization.
4. List the example in the table above and in the root [README](../README.md).
5. Run `python -m pytest tests -q --no-cov`.

## Dashboard-config scripts

Note: these scripts write files to the current working directory because output paths are relative.

### 1. Sales Dashboard (`sales_dashboard_example.py`)

A comprehensive sales analytics dashboard with 6 charts showing revenue metrics, sales trends, and performance.

**Charts:**
- Revenue by Region (Bar)
- Daily Revenue Trend (Line)
- Sales by Product Category (Pie)
- Top Sales Representatives (Table)
- Sales Pipeline (Funnel)
- Monthly Revenue vs Target (Heatmap)

**Filters:**
- Date Range
- Region (multi-select)
- Product Category (multi-select)
- Sales Stage
- Minimum Deal Size (range slider)

**Run:**
```bash
python examples/sales_dashboard_example.py
```

**Output:**
- `example_sales_dashboard.json` - Dashboard configuration (written to current working directory)
- `example_sales_dashboard.html` - HTML template (written to current working directory)
- Console summary with chart details

---

### 2. Customer Dashboard (`customer_dashboard_example.py`)

A customer-focused dashboard with 10 charts for tracking acquisition, retention, health, and lifetime value.

**Charts:**
- Total Customers (Metric)
- Monthly Recurring Revenue (Metric)
- Monthly Churn Rate (Metric)
- Customer Cohort Retention (Heatmap)
- Customer Lifecycle Funnel
- Monthly Customer Acquisition (Area)
- Customer LTV vs Tenure (Scatter)
- Customers & MRR by Segment (Column)
- Customer Health Distribution (Bar)
- Top Customers by MRR (Table)

**Filters:**
- Customer Segment (multi-select)
- Customer Status (multi-select)
- Industry (multi-select)
- MRR Range (slider)

**Run:**
```bash
python examples/customer_dashboard_example.py
```

**Output:**
- `example_customer_dashboard.json` - Dashboard configuration (written to current working directory)
- `example_customer_dashboard.html` - HTML template (written to current working directory)
- Console overview with all charts and filters

---

## Supported Chart Types

| Chart Type | Use Case | Example |
|-----------|----------|---------|
| **BAR** | Compare categories | Revenue by region |
| **COLUMN** | Vertical bar comparisons | Sales by segment |
| **LINE** | Trends over time | Daily revenue trend |
| **AREA** | Cumulative trends | Customer acquisition |
| **SCATTER** | Relationship analysis | LTV vs tenure |
| **PIE** | Percentage distribution | Sales by category |
| **TABLE** | Detailed data viewing | Top customers |
| **METRIC** | Single KPI cards | Total revenue |
| **FUNNEL** | Progression stages | Sales pipeline |
| **HEATMAP** | Intensity visualization | Retention by cohort |

---

## Working with Dashboard JSON

### Load a dashboard from JSON:
```python
import json
from snowflake_analytics_agents import DashboardConfig

with open("example_sales_dashboard.json") as f:
    dashboard_dict = json.load(f)

# Reconstruct dashboard object if needed
dashboard_id = dashboard_dict["id"]
dashboard_name = dashboard_dict["name"]
charts_count = len(dashboard_dict["charts"])
```

### Test a dashboard:
```python
from snowflake_analytics_agents import DashboardTesterAgent

tester = DashboardTesterAgent(config)
validation = tester.validate_dashboard(dashboard)
performance = tester.check_performance(dashboard)

print(f"Valid: {validation['valid']}")
print(f"Performance Score: {performance['performance_score']}/100")
```

### Export dashboard data:
```python
from snowflake_analytics_agents import DashboardExportAgent

export_agent = DashboardExportAgent(config)

# Export with filters
filters = [
    {"column": "region", "operator": "equals", "value": "USA"},
    {"column": "amount", "operator": "gt", "value": 10000}
]

csv = export_agent.export_as_csv(
    dashboard=dashboard,
    chart_id="chart_revenue_by_region",
    filters=filters,
    sort_by="amount",
    sort_order="desc"
)

# Save to file
export_agent.export_to_file(
    dashboard=dashboard,
    chart_id="chart_revenue_by_region",
    filepath="filtered_revenue.csv",
    filters=filters
)
```

---

## Filter Types & Operators

### Filter Operators Supported:
- `equals` - Exact match
- `not_equals` - Not equal
- `contains` - Text contains substring
- `starts_with` - Text starts with value
- `ends_with` - Text ends with value
- `gt` - Greater than (numbers)
- `gte` - Greater than or equal
- `lt` - Less than
- `lte` - Less than or equal
- `in` - In list of values
- `not_in` - Not in list
- `between` - Between two values (numeric range)
- `is_null` - Column is null
- `is_not_null` - Column is not null

### Example Filters:
```python
filters = [
    # Exact match
    {"column": "region", "operator": "equals", "value": "USA"},
    
    # Text search
    {"column": "customer_name", "operator": "contains", "value": "Inc"},
    
    # Numeric comparison
    {"column": "revenue", "operator": "gte", "value": 50000},
    
    # Range
    {"column": "date", "operator": "between", "value": "2024-01-01", "value_end": "2024-12-31"},
    
    # List membership
    {"column": "segment", "operator": "in", "value": ["Enterprise", "Mid-Market"]},
    
    # Null check
    {"column": "parent_account", "operator": "is_not_null"}
]
```

---

## Creating Your Own Dashboard

### Step 1: Import Required Classes
```python
from snowflake_analytics_agents import (
    DashboardConfig,
    ChartConfig,
    FilterConfig,
)
from snowflake_analytics_agents.dashboard import ChartType, DashboardLayout
```

### Step 2: Create Dashboard
```python
dashboard = DashboardConfig(
    id="my_dashboard",
    name="My Custom Dashboard",
    description="Dashboard description",
    layout=DashboardLayout.TWO_COLUMN,
    rows=2,
    cols=2,
)
```

### Step 3: Add Charts
```python
chart = ChartConfig(
    id="chart_1",
    title="Chart Title",
    chart_type=ChartType.BAR,
    query="SELECT column1, column2 FROM table",
    x_column="column1",
    y_column="column2",
)
dashboard.add_chart(chart)
```

### Step 4: Add Filters
```python
dashboard.add_filter(
    FilterConfig(
        id="date_filter",
        name="Date Range",
        filter_type="date_range",
        column="date",
    )
)
```

### Step 5: Export & Test
```python
# Export as JSON
import json
json_str = json.dumps(dashboard.to_dict(), indent=2)

# Test
tester = DashboardTesterAgent(config)
validation = tester.validate_dashboard(dashboard)

# Export data
export_agent = DashboardExportAgent(config)
csv = export_agent.export_as_csv(dashboard, "chart_1")
```

---

## Tips & Best Practices

1. **Query Performance**: Use appropriate WHERE clauses and LIMIT statements
2. **Chart Types**: Choose chart types that match your data and use case
3. **Filters**: Add dashboard-level filters to enable data exploration
4. **Sorting**: Sort tables by relevant columns for better usability
5. **Descriptions**: Provide clear descriptions for all charts and filters
6. **Testing**: Always validate and test dashboards before production use
7. **Data Export**: Use filters to export only relevant data subsets

---

## See Also

- [README.md](../README.md) - Main project documentation
- [docs/architecture.md](../docs/architecture.md) - Architecture and design details
- [docs/dashboard_toolkit.md](../docs/dashboard_toolkit.md) - Shared dashboard toolkit API
- [pyproject.toml](../pyproject.toml) - Project configuration
