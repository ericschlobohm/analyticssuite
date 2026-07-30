from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from .agents import BaseAgent
from .dashboard import (
    ChartConfig,
    ChartType,
    DashboardConfig,
    DashboardLayout,
    FilterConfig,
)
from .snowflake_client import SnowflakeClient

logger = logging.getLogger(__name__)


class DashboardBuilderAgent(BaseAgent):
    """Agent for generating Tableau-like dashboard configurations."""

    def generate_dashboard(
        self,
        title: str,
        description: str,
        requirements: str,
        layout: str = "two_column",
        num_charts: int = 4,
    ) -> DashboardConfig:
        """
        Generate a dashboard configuration from natural language requirements.

        Args:
            title: Dashboard title
            description: Dashboard description
            requirements: Natural language description of what the dashboard should show
            layout: Dashboard layout type (single_column, two_column, three_column, grid)
            num_charts: Number of charts to generate

        Returns:
            DashboardConfig object with generated charts and filters
        """
        logger.info(f"DashboardBuilderAgent: Generating dashboard '{title}'")

        # Create dashboard config
        dashboard = DashboardConfig(
            id=f"dashboard_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            name=title,
            description=description,
            layout=DashboardLayout(layout),
            rows=2,
            cols=2 if layout == "two_column" else (3 if layout == "three_column" else 1),
        )

        # Generate placeholder charts
        # In production, this would use an LLM to interpret requirements
        for i in range(num_charts):
            chart = ChartConfig(
                id=f"chart_{i+1}",
                title=f"Chart {i+1}",
                chart_type=ChartType.LINE if i % 2 == 0 else ChartType.BAR,
                query=f"-- Generated chart query\nSELECT * FROM table_{i+1};",
                x_column="date" if i % 2 == 0 else "category",
                y_column="value",
                dimensions=["date"] if i % 2 == 0 else ["category"],
                measures=["value"],
                description="Auto-generated chart based on requirements",
                height=400,
                width=500,
            )
            dashboard.add_chart(chart)

        # Add sample filters
        dashboard.add_filter(
            FilterConfig(
                id="date_filter",
                name="Date Range",
                filter_type="date_range",
                column="date",
                default_value="last_30_days",
            )
        )

        logger.info(f"Dashboard generated with {len(dashboard.charts)} charts")
        return dashboard

    def add_chart_to_dashboard(
        self,
        dashboard: DashboardConfig,
        chart_title: str,
        chart_type: str,
        query: str,
        x_column: str | None = None,
        y_column: str | None = None,
    ) -> DashboardConfig:
        """
        Add a new chart to an existing dashboard.

        Args:
            dashboard: DashboardConfig to update
            chart_title: Title for the new chart
            chart_type: Type of chart (line, bar, pie, etc.)
            query: SQL query for the chart
            x_column: X-axis column
            y_column: Y-axis column

        Returns:
            Updated DashboardConfig
        """
        chart = ChartConfig(
            id=f"chart_{len(dashboard.charts) + 1}",
            title=chart_title,
            chart_type=ChartType(chart_type),
            query=query,
            x_column=x_column,
            y_column=y_column,
        )
        dashboard.add_chart(chart)
        logger.info(f"Added chart '{chart_title}' to dashboard")
        return dashboard

    def export_dashboard_json(self, dashboard: DashboardConfig) -> str:
        """
        Export dashboard configuration as JSON.

        Args:
            dashboard: DashboardConfig to export

        Returns:
            JSON string representation
        """
        return json.dumps(dashboard.to_dict(), indent=2)

    def export_dashboard_html(self, dashboard: DashboardConfig) -> str:
        """
        Export dashboard as HTML template for rendering.

        Args:
            dashboard: DashboardConfig to export

        Returns:
            HTML string
        """
        charts_html = "\n".join(
            f'<div class="chart" id="{chart.id}" style="height: {chart.height}px; width: {chart.width}px;">'
            f"<h3>{chart.title}</h3><p>Chart placeholder for {chart.chart_type.value}</p></div>"
            for chart in dashboard.charts
        )

        filters_html = "\n".join(
            f'<div class="filter" id="{f.id}"><label>{f.name}</label></div>'
            for f in dashboard.filters
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{dashboard.name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .dashboard {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ margin-bottom: 20px; }}
        .filters {{ background: #f5f5f5; padding: 15px; border-radius: 4px; margin-bottom: 20px; }}
        .charts {{ display: grid; grid-template-columns: repeat({dashboard.cols}, 1fr); gap: 20px; }}
        .chart {{ border: 1px solid #ddd; border-radius: 4px; padding: 15px; }}
        .filter {{ display: inline-block; margin-right: 15px; }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>{dashboard.name}</h1>
            <p>{dashboard.description}</p>
        </div>
        <div class="filters">
            {filters_html}
        </div>
        <div class="charts">
            {charts_html}
        </div>
    </div>
</body>
</html>"""
        return html

    def execute(
        self,
        title: str,
        description: str,
        requirements: str,
        layout: str = "two_column",
    ) -> DashboardConfig:
        """Execute the dashboard builder agent."""
        return self.generate_dashboard(title, description, requirements, layout)


class DashboardTesterAgent(BaseAgent):
    """Agent for testing and validating dashboard configurations."""

    def validate_dashboard(
        self,
        dashboard: DashboardConfig,
    ) -> dict[str, Any]:
        """
        Validate dashboard configuration for common issues.

        Args:
            dashboard: DashboardConfig to validate

        Returns:
            Validation results with issues and warnings
        """
        logger.info(f"DashboardTesterAgent: Validating dashboard '{dashboard.name}'")

        results = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "stats": {
                "num_charts": len(dashboard.charts),
                "num_filters": len(dashboard.filters),
                "total_refresh_time_ms": 0,
            },
        }

        # Check for empty dashboard
        if not dashboard.charts:
            results["issues"].append("Dashboard has no charts")
            results["valid"] = False

        # Check chart validity
        for chart in dashboard.charts:
            if not chart.query:
                results["issues"].append(f"Chart '{chart.id}' has no query")
                results["valid"] = False

            if chart.chart_type == ChartType.LINE and not chart.x_column:
                results["warnings"].append(
                    f"Chart '{chart.id}' ({chart.chart_type.value}) should have X axis"
                )

            if not chart.title:
                results["warnings"].append(f"Chart '{chart.id}' has no title")

        # Check for duplicate chart IDs
        chart_ids = [c.id for c in dashboard.charts]
        if len(chart_ids) != len(set(chart_ids)):
            results["issues"].append("Dashboard has duplicate chart IDs")
            results["valid"] = False

        # Check for filter validity
        for filter_config in dashboard.filters:
            if not filter_config.column:
                results["issues"].append(f"Filter '{filter_config.id}' has no column")
                results["valid"] = False

        # Performance warnings
        if len(dashboard.charts) > 10:
            results["warnings"].append("Dashboard has many charts - may impact performance")

        # Check refresh intervals
        slow_refresh = [c.id for c in dashboard.charts if c.refresh_interval < 60]
        if slow_refresh:
            results["warnings"].append(
                f"Charts {slow_refresh} have very short refresh intervals (< 1 min)"
            )

        return results

    def test_queries(
        self,
        dashboard: DashboardConfig,
        test_connection: SnowflakeClient | None = None,
    ) -> dict[str, Any]:
        """
        Test all queries in a dashboard against Snowflake.

        Args:
            dashboard: DashboardConfig to test
            test_connection: Optional SnowflakeClient (uses agent's client if not provided)

        Returns:
            Test results for each query
        """
        logger.info(f"DashboardTesterAgent: Testing queries for '{dashboard.name}'")

        client = test_connection or self.client
        results = {
            "total_charts": len(dashboard.charts),
            "successful": 0,
            "failed": 0,
            "charts": [],
        }

        for chart in dashboard.charts:
            chart_result = {
                "chart_id": chart.id,
                "chart_title": chart.title,
                "status": "unknown",
                "error": None,
                "row_count": 0,
                "execution_time_ms": 0,
            }

            try:
                # Test the query
                query_results = client.execute_query(chart.query)
                chart_result["status"] = "success"
                chart_result["row_count"] = len(query_results)
                results["successful"] += 1
                logger.info(f"Chart '{chart.id}' query successful - {len(query_results)} rows")
            except Exception as e:  # noqa: BLE001
                chart_result["status"] = "failed"
                chart_result["error"] = str(e)
                results["failed"] += 1
                logger.error(f"Chart '{chart.id}' query failed: {e}")

            results["charts"].append(chart_result)

        return results

    def check_performance(
        self,
        dashboard: DashboardConfig,
        query_time_threshold_ms: int = 5000,
    ) -> dict[str, Any]:
        """
        Check dashboard performance characteristics.

        Args:
            dashboard: DashboardConfig to analyze
            query_time_threshold_ms: Threshold for slow queries in milliseconds

        Returns:
            Performance analysis results
        """
        logger.info(f"DashboardTesterAgent: Analyzing performance for '{dashboard.name}'")

        results = {
            "performance_score": 100,
            "recommendations": [],
            "high_refresh_count": 0,
            "estimated_total_refresh_ms": 0,
        }

        # Analyze refresh intervals
        fast_refresh = [c for c in dashboard.charts if c.refresh_interval < 60]
        if fast_refresh:
            results["high_refresh_count"] = len(fast_refresh)
            results["performance_score"] -= 10
            results["recommendations"].append(
                f"Consider increasing refresh intervals for {len(fast_refresh)} chart(s)"
            )

        # Check for complex queries (placeholder logic)
        complex_queries = [c for c in dashboard.charts if "JOIN" in c.query.upper()]
        if len(complex_queries) > dashboard.cols:
            results["performance_score"] -= 15
            results["recommendations"].append(
                "Dashboard has many complex queries - consider optimization"
            )

        # Estimate total refresh time
        results["estimated_total_refresh_ms"] = (
            sum(c.refresh_interval * 1000 for c in dashboard.charts) // len(dashboard.charts)
            if dashboard.charts
            else 0
        )

        return results

    def generate_test_report(
        self,
        dashboard: DashboardConfig,
        test_connection: SnowflakeClient | None = None,
    ) -> str:
        """
        Generate a comprehensive test report for a dashboard.

        Args:
            dashboard: DashboardConfig to test
            test_connection: Optional SnowflakeClient

        Returns:
            Formatted test report
        """
        logger.info(f"DashboardTesterAgent: Generating test report for '{dashboard.name}'")

        # Run all tests
        validation = self.validate_dashboard(dashboard)
        query_tests = self.test_queries(dashboard, test_connection)
        performance = self.check_performance(dashboard)

        report = f"""
=== DASHBOARD TEST REPORT ===
Dashboard: {dashboard.name}
Generated: {datetime.now(timezone.utc).isoformat()}

--- VALIDATION RESULTS ---
Valid: {validation['valid']}
Issues: {len(validation['issues'])}
Warnings: {len(validation['warnings'])}

{self._format_issues(validation['issues'])}
{self._format_warnings(validation['warnings'])}

--- QUERY TEST RESULTS ---
Total Charts: {query_tests['total_charts']}
Successful: {query_tests['successful']}
Failed: {query_tests['failed']}

{self._format_query_results(query_tests['charts'])}

--- PERFORMANCE ANALYSIS ---
Performance Score: {performance['performance_score']}/100
High Refresh Charts: {performance['high_refresh_count']}
Estimated Refresh Time: {performance['estimated_total_refresh_ms']}ms

Recommendations:
{self._format_recommendations(performance['recommendations'])}

=== END REPORT ===
"""
        return report

    def _format_issues(self, issues: list[str]) -> str:
        """Format issues for report."""
        if not issues:
            return "âœ“ No issues found"
        return "âœ— Issues:\n" + "\n".join(f"  - {issue}" for issue in issues)

    def _format_warnings(self, warnings: list[str]) -> str:
        """Format warnings for report."""
        if not warnings:
            return ""
        return "âš  Warnings:\n" + "\n".join(f"  - {warning}" for warning in warnings)

    def _format_query_results(self, results: list[dict[str, Any]]) -> str:
        """Format query test results for report."""
        lines = []
        for result in results:
            status_icon = "âœ“" if result["status"] == "success" else "âœ—"
            lines.append(
                f"  {status_icon} {result['chart_title']} ({result['chart_id']}): "
                f"{result['status']} - {result['row_count']} rows"
            )
            if result["error"]:
                lines.append(f"      Error: {result['error']}")
        return "\n".join(lines)

    def _format_recommendations(self, recommendations: list[str]) -> str:
        """Format recommendations for report."""
        if not recommendations:
            return "  None"
        return "\n".join(f"  â€¢ {rec}" for rec in recommendations)

    def execute(
        self,
        dashboard: DashboardConfig,
        test_type: str = "full",
    ) -> dict[str, Any]:
        """Execute the dashboard tester agent."""
        if test_type == "validation":
            return self.validate_dashboard(dashboard)
        elif test_type == "queries":
            return self.test_queries(dashboard)
        elif test_type == "performance":
            return self.check_performance(dashboard)
        else:
            return {
                "validation": self.validate_dashboard(dashboard),
                "queries": self.test_queries(dashboard),
                "performance": self.check_performance(dashboard),
            }
