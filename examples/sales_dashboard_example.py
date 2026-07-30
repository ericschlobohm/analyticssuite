"""
Example: Building a Sales Analytics Dashboard

This script demonstrates how to use the DashboardBuilderAgent to create
a Tableau-like dashboard with multiple chart types and filters.

Run this with: python examples/sales_dashboard_example.py
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


def create_sales_dashboard():
    """Create an example sales analytics dashboard."""

    # Initialize dashboard
    dashboard = DashboardConfig(
        id="sales_dashboard_2024",
        name="Sales Analytics Dashboard",
        description="Company-wide sales metrics, trends, and performance analysis",
        layout=DashboardLayout.TWO_COLUMN,
        rows=3,
        cols=2,
        theme="light",
        tags=["sales", "analytics", "kpis"],
        metadata={
            "created_by": "analytics_team",
            "last_updated": "2024-01-15",
            "department": "sales",
        },
    )

    # ===== CHART 1: Revenue by Region (Bar Chart) =====
    chart_revenue_by_region = ChartConfig(
        id="chart_revenue_by_region",
        title="Total Revenue by Region",
        chart_type=ChartType.BAR,
        query="""
            SELECT 
                region,
                SUM(amount) as total_revenue
            FROM sales
            WHERE date >= CURRENT_DATE - 90
            GROUP BY region
            ORDER BY total_revenue DESC
        """,
        x_column="region",
        y_column="total_revenue",
        dimensions=["region"],
        measures=["total_revenue"],
        description="Bar chart showing total revenue by geographic region over the last 90 days",
        height=400,
        width=600,
        color_scheme="blues",
        show_legend=False,
    )
    dashboard.add_chart(chart_revenue_by_region)

    # ===== CHART 2: Daily Revenue Trend (Line Chart) =====
    chart_daily_trend = ChartConfig(
        id="chart_daily_trend",
        title="Daily Revenue Trend",
        chart_type=ChartType.LINE,
        query="""
            SELECT 
                DATE(date) as sales_date,
                SUM(amount) as daily_revenue
            FROM sales
            WHERE date >= CURRENT_DATE - 30
            GROUP BY DATE(date)
            ORDER BY sales_date ASC
        """,
        x_column="sales_date",
        y_column="daily_revenue",
        dimensions=["sales_date"],
        measures=["daily_revenue"],
        description="Line chart showing daily revenue trend for the last 30 days",
        height=400,
        width=600,
        color_scheme="greens",
        show_grid=True,
        aggregation="SUM",
    )
    dashboard.add_chart(chart_daily_trend)

    # ===== CHART 3: Sales by Product Category (Pie Chart) =====
    chart_by_category = ChartConfig(
        id="chart_by_category",
        title="Sales Distribution by Product Category",
        chart_type=ChartType.PIE,
        query="""
            SELECT 
                category,
                COUNT(*) as num_sales,
                SUM(amount) as category_revenue
            FROM sales
            WHERE date >= CURRENT_DATE - 90
            GROUP BY category
        """,
        dimensions=["category"],
        measures=["category_revenue"],
        description="Pie chart showing revenue distribution across product categories",
        height=400,
        width=600,
        color_scheme="pastel",
    )
    dashboard.add_chart(chart_by_category)

    # ===== CHART 4: Top 10 Sales Representatives (Table) =====
    chart_top_reps = ChartConfig(
        id="chart_top_sales_reps",
        title="Top 10 Sales Representatives",
        chart_type=ChartType.TABLE,
        query="""
            SELECT 
                rep_name,
                region,
                COUNT(*) as deals_closed,
                SUM(amount) as total_revenue,
                AVG(amount) as avg_deal_size
            FROM sales
            WHERE date >= CURRENT_DATE - 90
            GROUP BY rep_name, region
            ORDER BY total_revenue DESC
            LIMIT 10
        """,
        dimensions=["rep_name", "region"],
        measures=["deals_closed", "total_revenue", "avg_deal_size"],
        description="Table showing top performing sales representatives by revenue",
        height=500,
        width=600,
        sort_by="total_revenue",
    )
    dashboard.add_chart(chart_top_reps)

    # ===== CHART 5: Sales Pipeline (Funnel Chart) =====
    chart_pipeline = ChartConfig(
        id="chart_sales_pipeline",
        title="Sales Pipeline Status",
        chart_type=ChartType.FUNNEL,
        query="""
            SELECT 
                stage,
                COUNT(*) as opportunity_count,
                SUM(amount) as pipeline_value
            FROM opportunities
            WHERE date >= CURRENT_DATE - 180
            GROUP BY stage
            ORDER BY stage
        """,
        dimensions=["stage"],
        measures=["pipeline_value"],
        description="Funnel chart showing sales pipeline progression from lead to close",
        height=400,
        width=600,
    )
    dashboard.add_chart(chart_pipeline)

    # ===== CHART 6: Revenue vs Target Heatmap =====
    chart_heatmap = ChartConfig(
        id="chart_revenue_heatmap",
        title="Monthly Revenue vs Target",
        chart_type=ChartType.HEATMAP,
        query="""
            SELECT 
                DATE_TRUNC('month', date) as month,
                region,
                SUM(amount) as actual_revenue,
                SUM(target) as target_revenue,
                ROUND(100.0 * SUM(amount) / SUM(target), 1) as pct_of_target
            FROM sales
            WHERE date >= CURRENT_DATE - 365
            GROUP BY DATE_TRUNC('month', date), region
        """,
        dimensions=["month", "region"],
        measures=["pct_of_target"],
        description="Heatmap showing revenue performance vs targets by month and region",
        height=400,
        width=600,
        color_scheme="reds",
    )
    dashboard.add_chart(chart_heatmap)

    # ===== DASHBOARD FILTERS =====

    # Date range filter
    dashboard.add_filter(
        FilterConfig(
            id="date_range_filter",
            name="Date Range",
            filter_type="date_range",
            column="date",
            default_value="last_30_days",
        )
    )

    # Region filter
    dashboard.add_filter(
        FilterConfig(
            id="region_filter",
            name="Region",
            filter_type="dropdown",
            column="region",
            values=["USA", "Canada", "Europe", "APAC", "LATAM"],
            multi_select=True,
        )
    )

    # Category filter
    dashboard.add_filter(
        FilterConfig(
            id="category_filter",
            name="Product Category",
            filter_type="dropdown",
            column="category",
            values=["Enterprise", "Mid-Market", "SMB", "Startup"],
            multi_select=True,
        )
    )

    # Sales stage filter
    dashboard.add_filter(
        FilterConfig(
            id="stage_filter",
            name="Sales Stage",
            filter_type="dropdown",
            column="stage",
            values=["Lead", "Qualified", "Proposal", "Negotiation", "Closed Won"],
            multi_select=False,
        )
    )

    # Minimum deal size slider
    dashboard.add_filter(
        FilterConfig(
            id="min_deal_size",
            name="Minimum Deal Size ($)",
            filter_type="range_slider",
            column="amount",
            default_value=0,
        )
    )

    return dashboard


def main():
    """Main function to create and export the example dashboard."""

    print("=" * 70)
    print("SALES ANALYTICS DASHBOARD - EXAMPLE")
    print("=" * 70)

    # Create dashboard
    print("\n✓ Creating dashboard...")
    dashboard = create_sales_dashboard()

    print(f"✓ Dashboard: {dashboard.name}")
    print(f"✓ Charts: {len(dashboard.charts)}")
    print(f"✓ Filters: {len(dashboard.filters)}")

    # Export as JSON
    print("\n" + "=" * 70)
    print("DASHBOARD CONFIGURATION (JSON)")
    print("=" * 70)

    dashboard_json = json.dumps(dashboard.to_dict(), indent=2)
    print(dashboard_json[:1000] + "\n... (truncated)\n")

    # Save to file
    with open("example_sales_dashboard.json", "w") as f:
        f.write(dashboard_json)
    print("✓ Saved to: example_sales_dashboard.json")

    # Show charts summary
    print("\n" + "=" * 70)
    print("CHARTS SUMMARY")
    print("=" * 70)

    for i, chart in enumerate(dashboard.charts, 1):
        print(f"\n{i}. {chart.title}")
        print(f"   Type: {chart.chart_type.value}")
        print(f"   ID: {chart.id}")
        print(f"   Dimensions: {', '.join(chart.dimensions)}")
        print(f"   Measures: {', '.join(chart.measures)}")
        print(f"   Description: {chart.description}")

    # Show filters summary
    print("\n" + "=" * 70)
    print("DASHBOARD FILTERS")
    print("=" * 70)

    for i, filt in enumerate(dashboard.filters, 1):
        print(f"\n{i}. {filt.name}")
        print(f"   Type: {filt.filter_type}")
        print(f"   Column: {filt.column}")
        if filt.values:
            print(f"   Available Values: {', '.join(str(v) for v in filt.values)}")
        if filt.multi_select:
            print("   Multi-Select: Yes")

    # Show example data export with filters
    print("\n" + "=" * 70)
    print("EXAMPLE: EXPORTING DATA WITH FILTERS")
    print("=" * 70)

    print("""
From the Python API, you can export chart data with flexible filtering:

from snowflake_analytics_agents import DashboardExportAgent, FilterOperator

export_agent = DashboardExportAgent(config)

# Export top sales reps from USA and Canada only
filters = [
    {
        "column": "region",
        "operator": "in",
        "value": ["USA", "Canada"]
    }
]

csv_data = export_agent.export_as_csv(
    dashboard=dashboard,
    chart_id="chart_top_sales_reps",
    filters=filters,
    sort_by="total_revenue",
    sort_order="desc"
)

# Or export to file
export_agent.export_to_file(
    dashboard=dashboard,
    chart_id="chart_top_sales_reps",
    filepath="top_reps_usa_canada.csv",
    filters=filters
)
""")

    # Example HTML export
    print("\n" + "=" * 70)
    print("HTML EXPORT")
    print("=" * 70)

    config = load_config()
    builder = DashboardBuilderAgent(config)
    html = builder.export_dashboard_html(dashboard)

    with open("example_sales_dashboard.html", "w") as f:
        f.write(html)
    print("✓ Saved HTML template to: example_sales_dashboard.html")

    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Load the dashboard from JSON:
   with open("example_sales_dashboard.json") as f:
       dashboard_dict = json.load(f)

2. Test the dashboard:
   tester = DashboardTesterAgent(config)
   validation = tester.validate_dashboard(dashboard)
   performance = tester.check_performance(dashboard)

3. Export data from charts:
   export_agent = DashboardExportAgent(config)
   csv_data = export_agent.export_as_csv(
       dashboard=dashboard,
       chart_id="chart_revenue_by_region",
       filters=[{"column": "region", "operator": "equals", "value": "USA"}]
   )

4. See README.md for more examples and CLI usage
""")


if __name__ == "__main__":
    main()
