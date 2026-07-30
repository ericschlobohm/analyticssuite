"""
Tests for dashboard agents.
"""

import json
from unittest.mock import MagicMock

import pytest

from snowflake_analytics_agents import (
    ChartConfig,
    DashboardBuilderAgent,
    DashboardConfig,
    DashboardTesterAgent,
)
from snowflake_analytics_agents.config import AgentConfig, Config, SnowflakeConfig
from snowflake_analytics_agents.dashboard import ChartType, DashboardLayout


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    snowflake_cfg = SnowflakeConfig(
        account="test_account",
        user="test_user",
        password="test_password",
        database="test_db",
        warehouse="test_wh",
    )
    agent_cfg = AgentConfig(timeout=60, max_retries=1, debug=True)
    return Config(snowflake=snowflake_cfg, agents=agent_cfg, extra={})


@pytest.fixture
def mock_client():
    """Create a mock Snowflake client."""
    mock = MagicMock()
    mock.test_connection.return_value = True
    mock.execute_query.return_value = [("test", 1), ("data", 2)]
    return mock


@pytest.fixture
def sample_dashboard():
    """Create a sample dashboard for testing."""
    dashboard = DashboardConfig(
        id="test_dashboard",
        name="Test Dashboard",
        description="A test dashboard",
        layout=DashboardLayout.TWO_COLUMN,
    )

    chart1 = ChartConfig(
        id="chart_1",
        title="Revenue by Region",
        chart_type=ChartType.BAR,
        query="SELECT region, SUM(revenue) FROM sales GROUP BY region;",
        x_column="region",
        y_column="revenue",
    )
    dashboard.add_chart(chart1)

    chart2 = ChartConfig(
        id="chart_2",
        title="Daily Revenue Trend",
        chart_type=ChartType.LINE,
        query="SELECT date, SUM(revenue) FROM sales GROUP BY date ORDER BY date;",
        x_column="date",
        y_column="revenue",
    )
    dashboard.add_chart(chart2)

    return dashboard


class TestDashboardBuilderAgent:
    """Tests for DashboardBuilderAgent."""

    def test_init(self, mock_config, mock_client):
        """Test agent initialization."""
        agent = DashboardBuilderAgent(mock_config, client=mock_client)
        assert agent.name == "DashboardBuilderAgent"

    def test_generate_dashboard(self, mock_config, mock_client):
        """Test dashboard generation."""
        agent = DashboardBuilderAgent(mock_config, client=mock_client)
        dashboard = agent.generate_dashboard(
            title="Sales Dashboard",
            description="Company sales metrics",
            requirements="Show revenue by region and daily trends",
            layout="two_column",
            num_charts=4,
        )

        assert dashboard.name == "Sales Dashboard"
        assert len(dashboard.charts) == 4
        assert dashboard.layout == DashboardLayout.TWO_COLUMN

    def test_add_chart_to_dashboard(self, mock_config, mock_client, sample_dashboard):
        """Test adding a chart to dashboard."""
        agent = DashboardBuilderAgent(mock_config, client=mock_client)
        initial_count = len(sample_dashboard.charts)

        dashboard = agent.add_chart_to_dashboard(
            sample_dashboard,
            chart_title="New Chart",
            chart_type="pie",
            query="SELECT * FROM data;",
            x_column="category",
            y_column="value",
        )

        assert len(dashboard.charts) == initial_count + 1
        assert dashboard.charts[-1].title == "New Chart"

    def test_export_dashboard_json(self, mock_config, mock_client, sample_dashboard):
        """Test JSON export."""
        agent = DashboardBuilderAgent(mock_config, client=mock_client)
        json_str = agent.export_dashboard_json(sample_dashboard)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data["name"] == "Test Dashboard"
        assert len(data["charts"]) == 2

    def test_export_dashboard_html(self, mock_config, mock_client, sample_dashboard):
        """Test HTML export."""
        agent = DashboardBuilderAgent(mock_config, client=mock_client)
        html = agent.export_dashboard_html(sample_dashboard)

        assert "Test Dashboard" in html
        assert "chart_1" in html
        assert "chart_2" in html
        assert "<html>" in html.lower()


class TestDashboardTesterAgent:
    """Tests for DashboardTesterAgent."""

    def test_init(self, mock_config, mock_client):
        """Test agent initialization."""
        agent = DashboardTesterAgent(mock_config, client=mock_client)
        assert agent.name == "DashboardTesterAgent"

    def test_validate_dashboard_valid(self, mock_config, mock_client, sample_dashboard):
        """Test validation of valid dashboard."""
        agent = DashboardTesterAgent(mock_config, client=mock_client)
        results = agent.validate_dashboard(sample_dashboard)

        assert results["valid"] is True
        assert len(results["issues"]) == 0

    def test_validate_dashboard_no_charts(self, mock_config, mock_client):
        """Test validation of dashboard with no charts."""
        agent = DashboardTesterAgent(mock_config, client=mock_client)
        dashboard = DashboardConfig(
            id="empty",
            name="Empty Dashboard",
            description="No charts",
            layout=DashboardLayout.TWO_COLUMN,
        )

        results = agent.validate_dashboard(dashboard)
        assert results["valid"] is False
        assert any("no charts" in issue.lower() for issue in results["issues"])

    def test_validate_dashboard_duplicate_ids(self, mock_config, mock_client):
        """Test validation detects duplicate chart IDs."""
        agent = DashboardTesterAgent(mock_config, client=mock_client)
        dashboard = DashboardConfig(
            id="test",
            name="Test",
            description="Test",
            layout=DashboardLayout.TWO_COLUMN,
        )

        chart1 = ChartConfig(
            id="chart_1",
            title="Chart 1",
            chart_type=ChartType.BAR,
            query="SELECT 1;",
        )
        chart2 = ChartConfig(
            id="chart_1",  # Duplicate ID
            title="Chart 2",
            chart_type=ChartType.LINE,
            query="SELECT 2;",
        )
        dashboard.add_chart(chart1)
        dashboard.add_chart(chart2)

        results = agent.validate_dashboard(dashboard)
        assert results["valid"] is False
        assert any("duplicate" in issue.lower() for issue in results["issues"])

    def test_test_queries(self, mock_config, mock_client, sample_dashboard):
        """Test query execution."""
        agent = DashboardTesterAgent(mock_config, client=mock_client)
        results = agent.test_queries(sample_dashboard, test_connection=mock_client)

        assert results["total_charts"] == 2
        assert results["successful"] == 2
        assert results["failed"] == 0

    def test_check_performance(self, mock_config, mock_client, sample_dashboard):
        """Test performance analysis."""
        agent = DashboardTesterAgent(mock_config, client=mock_client)
        results = agent.check_performance(sample_dashboard)

        assert "performance_score" in results
        assert isinstance(results["performance_score"], int)
        assert 0 <= results["performance_score"] <= 100

    def test_generate_test_report(self, mock_config, mock_client, sample_dashboard):
        """Test report generation."""
        agent = DashboardTesterAgent(mock_config, client=mock_client)
        report = agent.generate_test_report(sample_dashboard, test_connection=mock_client)

        assert "DASHBOARD TEST REPORT" in report
        assert "Test Dashboard" in report
        assert "VALIDATION RESULTS" in report
        assert "QUERY TEST RESULTS" in report
        assert "PERFORMANCE ANALYSIS" in report


class TestDashboardConfig:
    """Tests for DashboardConfig."""

    def test_create_dashboard(self):
        """Test dashboard creation."""
        dashboard = DashboardConfig(
            id="test",
            name="Test Dashboard",
            description="Test",
            layout=DashboardLayout.TWO_COLUMN,
        )

        assert dashboard.name == "Test Dashboard"
        assert len(dashboard.charts) == 0

    def test_add_chart(self, sample_dashboard):
        """Test adding chart to dashboard."""
        initial_count = len(sample_dashboard.charts)
        chart = ChartConfig(
            id="new_chart",
            title="New Chart",
            chart_type=ChartType.PIE,
            query="SELECT * FROM data;",
        )
        sample_dashboard.add_chart(chart)

        assert len(sample_dashboard.charts) == initial_count + 1

    def test_get_chart(self, sample_dashboard):
        """Test retrieving chart by ID."""
        chart = sample_dashboard.get_chart("chart_1")
        assert chart is not None
        assert chart.title == "Revenue by Region"

        missing = sample_dashboard.get_chart("nonexistent")
        assert missing is None

    def test_to_dict(self, sample_dashboard):
        """Test conversion to dictionary."""
        data = sample_dashboard.to_dict()
        assert data["name"] == "Test Dashboard"
        assert len(data["charts"]) == 2
        assert data["layout"] == "two_column"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
