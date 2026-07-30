"""
Example: Customer Analytics Dashboard

This example demonstrates a customer-focused dashboard with metrics like
customer acquisition, retention, churn, and lifetime value.

Run this with: python examples/customer_dashboard_example.py
"""

import json

from snowflake_analytics_agents import (
    ChartConfig,
    DashboardBuilderAgent,
    DashboardConfig,
    FilterConfig,
)
from snowflake_analytics_agents.config import load_config
from snowflake_analytics_agents.dashboard import ChartType, DashboardLayout


def create_customer_dashboard():
    """Create an example customer analytics dashboard."""

    dashboard = DashboardConfig(
        id="customer_analytics_2024",
        name="Customer Analytics Dashboard",
        description="Customer acquisition, retention, health, and lifetime value metrics",
        layout=DashboardLayout.THREE_COLUMN,
        rows=3,
        cols=3,
        theme="light",
        tags=["customer", "metrics", "retention"],
        metadata={
            "department": "customer_success",
            "update_frequency": "daily",
        },
    )

    # ===== CHART 1: Key Metrics (Metric Cards) =====
    chart_total_customers = ChartConfig(
        id="metric_total_customers",
        title="Total Customers",
        chart_type=ChartType.METRIC,
        query="SELECT COUNT(DISTINCT customer_id) as total FROM customers WHERE status = 'Active'",
        measures=["total"],
        height=150,
        width=200,
        description="Total number of active customers",
    )
    dashboard.add_chart(chart_total_customers)

    chart_mrr = ChartConfig(
        id="metric_mrr",
        title="Monthly Recurring Revenue (MRR)",
        chart_type=ChartType.METRIC,
        query="""
            SELECT SUM(mrr) as total_mrr 
            FROM customers 
            WHERE status = 'Active'
        """,
        measures=["total_mrr"],
        height=150,
        width=200,
        description="Current MRR from active customers",
    )
    dashboard.add_chart(chart_mrr)

    chart_churn_rate = ChartConfig(
        id="metric_churn_rate",
        title="Monthly Churn Rate (%)",
        chart_type=ChartType.METRIC,
        query="""
            SELECT 
                ROUND(100.0 * COUNT(CASE WHEN status = 'Churned' THEN 1 END) / 
                COUNT(*), 2) as churn_pct
            FROM customers
            WHERE last_month_active = TRUE
        """,
        measures=["churn_pct"],
        height=150,
        width=200,
        description="Percentage of customers who churned this month",
    )
    dashboard.add_chart(chart_churn_rate)

    # ===== CHART 2: Customer Cohort Analysis (Heatmap) =====
    chart_cohort = ChartConfig(
        id="chart_cohort_analysis",
        title="Customer Cohort Retention",
        chart_type=ChartType.HEATMAP,
        query="""
            SELECT 
                DATE_TRUNC('month', signup_date) as cohort_month,
                DATE_TRUNC('month', activity_date) as activity_month,
                COUNT(DISTINCT customer_id) as retention_count
            FROM customer_activity
            GROUP BY DATE_TRUNC('month', signup_date), DATE_TRUNC('month', activity_date)
        """,
        dimensions=["cohort_month", "activity_month"],
        measures=["retention_count"],
        height=400,
        width=600,
        color_scheme="greens",
        description="Heatmap showing customer retention by signup cohort",
    )
    dashboard.add_chart(chart_cohort)

    # ===== CHART 3: Customer Lifecycle (Funnel) =====
    chart_lifecycle = ChartConfig(
        id="chart_lifecycle",
        title="Customer Lifecycle Funnel",
        chart_type=ChartType.FUNNEL,
        query="""
            SELECT 
                stage,
                COUNT(DISTINCT customer_id) as count
            FROM customer_journey
            GROUP BY stage
            ORDER BY stage
        """,
        dimensions=["stage"],
        measures=["count"],
        height=350,
        width=500,
        description="Funnel showing customer progression through lifecycle stages",
    )
    dashboard.add_chart(chart_lifecycle)

    # ===== CHART 4: Customer Acquisition Trend (Area Chart) =====
    chart_acq_trend = ChartConfig(
        id="chart_acquisition_trend",
        title="Monthly Customer Acquisition",
        chart_type=ChartType.AREA,
        query="""
            SELECT 
                DATE_TRUNC('month', signup_date) as month,
                source,
                COUNT(DISTINCT customer_id) as new_customers
            FROM customers
            GROUP BY DATE_TRUNC('month', signup_date), source
            ORDER BY month DESC
        """,
        x_column="month",
        y_column="new_customers",
        dimensions=["month", "source"],
        measures=["new_customers"],
        height=400,
        width=600,
        color_scheme="blues",
        aggregation="SUM",
        description="Area chart showing new customer acquisition by source",
    )
    dashboard.add_chart(chart_acq_trend)

    # ===== CHART 5: Customer Value Distribution (Scatter) =====
    chart_value_scatter = ChartConfig(
        id="chart_ltv_scatter",
        title="Customer LTV vs. Tenure",
        chart_type=ChartType.SCATTER,
        query="""
            SELECT 
                DATEDIFF(day, signup_date, CURRENT_DATE) as tenure_days,
                lifetime_value as ltv,
                customer_segment
            FROM customers
            WHERE status = 'Active'
        """,
        x_column="tenure_days",
        y_column="ltv",
        dimensions=["tenure_days", "customer_segment"],
        measures=["ltv"],
        height=400,
        width=600,
        color_scheme="purples",
        description="Scatter plot of customer LTV vs. tenure in days",
    )
    dashboard.add_chart(chart_value_scatter)

    # ===== CHART 6: Customers by Segment (Column Chart) =====
    chart_by_segment = ChartConfig(
        id="chart_customers_by_segment",
        title="Customers & MRR by Segment",
        chart_type=ChartType.COLUMN,
        query="""
            SELECT 
                segment,
                COUNT(DISTINCT customer_id) as customer_count,
                SUM(mrr) as total_mrr
            FROM customers
            WHERE status = 'Active'
            GROUP BY segment
            ORDER BY total_mrr DESC
        """,
        x_column="segment",
        y_column="customer_count",
        dimensions=["segment"],
        measures=["customer_count", "total_mrr"],
        height=400,
        width=600,
        color_scheme="teals",
        description="Column chart showing customer counts and MRR by segment",
    )
    dashboard.add_chart(chart_by_segment)

    # ===== CHART 7: Health Score Distribution (Bar) =====
    chart_health_dist = ChartConfig(
        id="chart_health_distribution",
        title="Customer Health Score Distribution",
        chart_type=ChartType.BAR,
        query="""
            SELECT 
                CASE 
                    WHEN health_score >= 80 THEN 'Excellent'
                    WHEN health_score >= 60 THEN 'Good'
                    WHEN health_score >= 40 THEN 'Fair'
                    ELSE 'At Risk'
                END as health_category,
                COUNT(*) as customer_count
            FROM customers
            WHERE status = 'Active'
            GROUP BY health_category
        """,
        x_column="health_category",
        y_column="customer_count",
        dimensions=["health_category"],
        measures=["customer_count"],
        height=350,
        width=500,
        color_scheme="reds",
        description="Bar chart showing distribution of customers by health score",
    )
    dashboard.add_chart(chart_health_dist)

    # ===== CHART 8: Top Customers (Table) =====
    chart_top_customers = ChartConfig(
        id="chart_top_customers",
        title="Top 20 Customers by MRR",
        chart_type=ChartType.TABLE,
        query="""
            SELECT 
                customer_name,
                industry,
                segment,
                mrr,
                lifetime_value,
                health_score,
                days_as_customer
            FROM customers
            WHERE status = 'Active'
            ORDER BY mrr DESC
            LIMIT 20
        """,
        dimensions=["customer_name", "industry", "segment"],
        measures=["mrr", "lifetime_value", "health_score"],
        height=450,
        width=700,
        sort_by="mrr",
        description="Table showing top revenue-generating customers",
    )
    dashboard.add_chart(chart_top_customers)

    # ===== FILTERS =====
    dashboard.add_filter(
        FilterConfig(
            id="segment_filter",
            name="Customer Segment",
            filter_type="dropdown",
            column="segment",
            values=["Enterprise", "Mid-Market", "SMB", "Startup"],
            multi_select=True,
        )
    )

    dashboard.add_filter(
        FilterConfig(
            id="status_filter",
            name="Customer Status",
            filter_type="dropdown",
            column="status",
            values=["Active", "Churned", "At Risk"],
            multi_select=True,
        )
    )

    dashboard.add_filter(
        FilterConfig(
            id="industry_filter",
            name="Industry",
            filter_type="dropdown",
            column="industry",
            values=["Technology", "Finance", "Healthcare", "Retail", "Other"],
            multi_select=True,
        )
    )

    dashboard.add_filter(
        FilterConfig(
            id="mrr_range",
            name="MRR Range",
            filter_type="range_slider",
            column="mrr",
            default_value=0,
        )
    )

    return dashboard


def main():
    """Main function to create and display the example dashboard."""

    print("\n" + "=" * 80)
    print(" " * 20 + "CUSTOMER ANALYTICS DASHBOARD - EXAMPLE")
    print("=" * 80)

    # Create dashboard
    print("\n✓ Creating dashboard...")
    dashboard = create_customer_dashboard()

    print(f"✓ Dashboard: {dashboard.name}")
    print(f"✓ Charts: {len(dashboard.charts)}")
    print(f"✓ Filters: {len(dashboard.filters)}")

    # Show dashboard info
    print("\n" + "=" * 80)
    print("DASHBOARD OVERVIEW")
    print("=" * 80)
    print(f"ID: {dashboard.id}")
    print(f"Description: {dashboard.description}")
    print(f"Layout: {dashboard.layout.value} ({dashboard.rows} rows × {dashboard.cols} cols)")
    print(f"Theme: {dashboard.theme}")

    # Show charts
    print("\n" + "=" * 80)
    print("CHARTS INCLUDED")
    print("=" * 80)

    for i, chart in enumerate(dashboard.charts, 1):
        print(f"\n{i}. {chart.title:<40} [{chart.chart_type.value.upper():>8}]")
        print(f"   ID: {chart.id}")
        if chart.dimensions:
            print(f"   Dimensions: {', '.join(chart.dimensions)}")
        if chart.measures:
            print(f"   Measures: {', '.join(chart.measures)}")

    # Show filters
    print("\n" + "=" * 80)
    print("DASHBOARD FILTERS")
    print("=" * 80)

    for i, filt in enumerate(dashboard.filters, 1):
        print(f"\n{i}. {filt.name}")
        print(f"   Type: {filt.filter_type}")
        print(f"   Column: {filt.column}")
        print(f"   Multi-Select: {'Yes' if filt.multi_select else 'No'}")

    # Export examples
    print("\n" + "=" * 80)
    print("EXPORT EXAMPLE")
    print("=" * 80)

    print("""
Using the DashboardExportAgent to export data from the dashboard:

# Export top customers from specific segments
filters = [
    {"column": "segment", "operator": "in", "value": ["Enterprise", "Mid-Market"]},
    {"column": "status", "operator": "equals", "value": "Active"}
]

csv_data = export_agent.export_as_csv(
    dashboard=dashboard,
    chart_id="chart_top_customers",
    filters=filters,
    sort_by="mrr",
    sort_order="desc"
)

# Filter to at-risk customers only
at_risk_filters = [
    {"column": "health_score", "operator": "lt", "value": 40}
]

at_risk_export = export_agent.export_to_file(
    dashboard=dashboard,
    chart_id="chart_top_customers",
    filepath="at_risk_customers.csv",
    filters=at_risk_filters
)
""")

    # Save configuration
    config = load_config()
    builder = DashboardBuilderAgent(config)

    dashboard_json = json.dumps(dashboard.to_dict(), indent=2)
    with open("example_customer_dashboard.json", "w") as f:
        f.write(dashboard_json)
    print("\n✓ Saved dashboard config to: example_customer_dashboard.json")

    # Save HTML
    html = builder.export_dashboard_html(dashboard)
    with open("example_customer_dashboard.html", "w") as f:
        f.write(html)
    print("✓ Saved HTML template to: example_customer_dashboard.html")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
