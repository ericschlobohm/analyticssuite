"""
Interactive Dashboard Examples - JSON Outputs

This file shows example dashboard configurations in JSON format
so you can see the actual structure and data.
"""

# Example 1: Minimal Dashboard with One Chart

MINIMAL_DASHBOARD = {
    "id": "minimal_dashboard",
    "name": "Minimal Dashboard Example",
    "description": "A simple dashboard with one chart",
    "layout": "two_column",
    "charts": [
        {
            "id": "revenue_chart",
            "title": "Total Revenue",
            "type": "metric",
            "query": "SELECT SUM(amount) as total_revenue FROM sales",
            "height": 200,
            "width": 400,
            "measures": ["total_revenue"],
        }
    ],
    "filters": [
        {
            "id": "date_filter",
            "name": "Date Range",
            "type": "date_range",
            "column": "date",
            "default_value": "last_30_days",
        }
    ],
}

# Example 2: Multi-Chart Sales Dashboard

SALES_DASHBOARD_PREVIEW = {
    "id": "sales_dashboard_2024",
    "name": "Sales Analytics Dashboard",
    "description": "Company-wide sales metrics, trends, and performance analysis",
    "layout": "two_column",
    "rows": 3,
    "cols": 2,
    "charts": [
        {
            "id": "chart_revenue_by_region",
            "title": "Total Revenue by Region",
            "type": "bar",
            "x_column": "region",
            "y_column": "total_revenue",
            "dimensions": ["region"],
            "measures": ["total_revenue"],
            "height": 400,
            "width": 600,
        },
        {
            "id": "chart_daily_trend",
            "title": "Daily Revenue Trend",
            "type": "line",
            "x_column": "sales_date",
            "y_column": "daily_revenue",
            "dimensions": ["sales_date"],
            "measures": ["daily_revenue"],
            "height": 400,
            "width": 600,
        },
        {
            "id": "chart_by_category",
            "title": "Sales Distribution by Product Category",
            "type": "pie",
            "dimensions": ["category"],
            "measures": ["category_revenue"],
            "height": 400,
            "width": 600,
        },
        {
            "id": "chart_top_sales_reps",
            "title": "Top 10 Sales Representatives",
            "type": "table",
            "dimensions": ["rep_name", "region"],
            "measures": ["deals_closed", "total_revenue", "avg_deal_size"],
            "height": 500,
            "width": 600,
        },
        {
            "id": "chart_sales_pipeline",
            "title": "Sales Pipeline Status",
            "type": "funnel",
            "dimensions": ["stage"],
            "measures": ["pipeline_value"],
            "height": 400,
            "width": 600,
        },
        {
            "id": "chart_revenue_heatmap",
            "title": "Monthly Revenue vs Target",
            "type": "heatmap",
            "dimensions": ["month", "region"],
            "measures": ["pct_of_target"],
            "height": 400,
            "width": 600,
        },
    ],
    "filters": [
        {
            "id": "date_range_filter",
            "name": "Date Range",
            "type": "date_range",
            "column": "date",
            "default_value": "last_30_days",
        },
        {
            "id": "region_filter",
            "name": "Region",
            "type": "dropdown",
            "column": "region",
            "values": ["USA", "Canada", "Europe", "APAC", "LATAM"],
            "multi_select": True,
        },
        {
            "id": "category_filter",
            "name": "Product Category",
            "type": "dropdown",
            "column": "category",
            "values": ["Enterprise", "Mid-Market", "SMB", "Startup"],
            "multi_select": True,
        },
    ],
}

# Example 3: KPI Dashboard with Metric Cards

KPI_DASHBOARD = {
    "id": "kpi_dashboard",
    "name": "Executive KPI Dashboard",
    "description": "Key performance indicators for executive overview",
    "layout": "single_column",
    "rows": 2,
    "cols": 4,
    "charts": [
        {
            "id": "metric_revenue",
            "title": "Total Revenue",
            "type": "metric",
            "measures": ["revenue"],
            "height": 150,
            "width": 250,
        },
        {
            "id": "metric_growth",
            "title": "YoY Growth (%)",
            "type": "metric",
            "measures": ["growth_pct"],
            "height": 150,
            "width": 250,
        },
        {
            "id": "metric_customers",
            "title": "Total Customers",
            "type": "metric",
            "measures": ["customer_count"],
            "height": 150,
            "width": 250,
        },
        {
            "id": "metric_churn",
            "title": "Churn Rate (%)",
            "type": "metric",
            "measures": ["churn_rate"],
            "height": 150,
            "width": 250,
        },
    ],
}

# Data Export Examples

EXPORT_EXAMPLE_1 = {
    "description": "Export top sales reps from USA",
    "chart_id": "chart_top_sales_reps",
    "filters": [{"column": "region", "operator": "equals", "value": "USA"}],
    "sort_by": "total_revenue",
    "sort_order": "desc",
}

EXPORT_EXAMPLE_2 = {
    "description": "Export revenue data for specific date range and categories",
    "chart_id": "chart_revenue_by_region",
    "filters": [
        {"column": "date", "operator": "between", "value": "2024-01-01", "value_end": "2024-03-31"},
        {"column": "category", "operator": "in", "value": ["Enterprise", "Mid-Market"]},
    ],
    "include_columns": ["region", "category", "revenue", "date"],
    "sort_by": "revenue",
    "sort_order": "desc",
    "max_rows": 1000,
}

EXPORT_EXAMPLE_3 = {
    "description": "Export at-risk customers with specific columns",
    "chart_id": "chart_customer_health",
    "filters": [
        {"column": "health_score", "operator": "lt", "value": 40},
        {"column": "status", "operator": "equals", "value": "Active"},
    ],
    "include_columns": ["customer_name", "segment", "health_score", "mrr", "contact_email"],
    "sort_by": "health_score",
    "sort_order": "asc",
}

# Chart Type Reference

CHART_TYPES_GUIDE = {
    "metric": {
        "description": "Single KPI card showing one metric value",
        "use_cases": ["Revenue", "Customer count", "Growth rate"],
        "example_query": "SELECT SUM(amount) as total_revenue FROM sales",
    },
    "bar": {
        "description": "Horizontal bars comparing categories",
        "use_cases": ["Revenue by region", "Sales by rep", "Deals by status"],
        "requires": ["x_column", "y_column"],
    },
    "column": {
        "description": "Vertical columns comparing categories",
        "use_cases": ["Monthly revenue", "Customer by segment", "Sales by product"],
        "requires": ["x_column", "y_column"],
    },
    "line": {
        "description": "Line showing trend over time",
        "use_cases": ["Revenue trend", "Customer growth", "Performance over time"],
        "requires": ["x_column (time)", "y_column"],
    },
    "area": {
        "description": "Area chart showing cumulative trends",
        "use_cases": ["Cumulative sales", "Stacked metrics over time"],
        "requires": ["x_column (time)", "y_column"],
    },
    "pie": {
        "description": "Pie chart showing percentage distribution",
        "use_cases": ["Revenue by category", "Customer distribution", "Market share"],
        "requires": ["dimensions", "measures"],
    },
    "scatter": {
        "description": "Scatter plot showing relationship between two variables",
        "use_cases": ["LTV vs tenure", "Price vs volume", "Time vs quality"],
        "requires": ["x_column", "y_column"],
    },
    "table": {
        "description": "Tabular data display with sorting and filtering",
        "use_cases": ["Detailed records", "Top customers", "Performance rankings"],
        "requires": ["dimensions", "measures"],
    },
    "funnel": {
        "description": "Funnel chart showing progression through stages",
        "use_cases": ["Sales pipeline", "Customer lifecycle", "Conversion stages"],
        "requires": ["dimensions (stages)", "measures"],
    },
    "heatmap": {
        "description": "Intensity visualization using colors",
        "use_cases": ["Retention by cohort", "Revenue vs target", "Performance matrix"],
        "requires": ["dimensions (two columns)", "measures"],
    },
}

# Running the Examples

RUNNING_EXAMPLES = """
# In Python, load and use examples:

from examples.sales_dashboard_example import create_sales_dashboard
from examples.customer_dashboard_example import create_customer_dashboard

# Create dashboards
sales_dashboard = create_sales_dashboard()
customer_dashboard = create_customer_dashboard()

# Test them
from snowflake_analytics_agents import DashboardTesterAgent
tester = DashboardTesterAgent(config)
validation = tester.validate_dashboard(sales_dashboard)

# Export data from them
from snowflake_analytics_agents import DashboardExportAgent
export_agent = DashboardExportAgent(config)

csv_data = export_agent.export_as_csv(
    dashboard=sales_dashboard,
    chart_id="chart_top_sales_reps",
    filters=[{"column": "region", "operator": "equals", "value": "USA"}],
    sort_by="total_revenue"
)
"""

if __name__ == "__main__":
    import json

    print("=" * 80)
    print("DASHBOARD EXAMPLES - JSON OUTPUT")
    print("=" * 80)

    print("\n\nSALES DASHBOARD STRUCTURE:")
    print(json.dumps(SALES_DASHBOARD_PREVIEW, indent=2)[:1000] + "\n... (truncated)\n")

    print("\nKPI DASHBOARD:")
    print(json.dumps(KPI_DASHBOARD, indent=2))

    print("\n\nEXPORT EXAMPLES:")
    print("\nExample 1 - Filter by region:")
    print(json.dumps(EXPORT_EXAMPLE_1, indent=2))

    print("\nExample 2 - Date range and category filters:")
    print(json.dumps(EXPORT_EXAMPLE_2, indent=2))
