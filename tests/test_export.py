"""
Tests for dashboard export functionality.
"""

from unittest.mock import MagicMock

import pytest

from snowflake_analytics_agents import (
    ChartConfig,
    ColumnFilter,
    DashboardConfig,
    DashboardExportAgent,
    ExportConfig,
    FilterOperator,
)
from snowflake_analytics_agents.config import AgentConfig, Config, SnowflakeConfig
from snowflake_analytics_agents.dashboard import ChartType, DashboardLayout
from snowflake_analytics_agents.export import CSVExporter, DataFilter


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
    # Sample query results as tuples
    mock.execute_query.return_value = [
        ("USA", "John", 100, "2024-01-01"),
        ("USA", "Jane", 150, "2024-01-02"),
        ("Canada", "Bob", 120, "2024-01-03"),
        ("USA", "Alice", 200, "2024-01-04"),
        ("Canada", "Charlie", 180, "2024-01-05"),
    ]
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

    chart = ChartConfig(
        id="sales_chart",
        title="Sales Data",
        chart_type=ChartType.TABLE,
        query="SELECT region, name, amount, date FROM sales;",
    )
    dashboard.add_chart(chart)

    return dashboard


class TestColumnFilter:
    """Tests for ColumnFilter."""

    def test_equals_filter(self):
        """Test equals operator."""
        filt = ColumnFilter(column="region", operator=FilterOperator.EQUALS, value="USA")
        assert filt.apply("USA") is True
        assert filt.apply("Canada") is False

    def test_contains_filter(self):
        """Test contains operator."""
        filt = ColumnFilter(column="name", operator=FilterOperator.CONTAINS, value="John")
        assert filt.apply("John Doe") is True
        assert filt.apply("Jane Doe") is False

    def test_numeric_filters(self):
        """Test numeric operators."""
        filt_gt = ColumnFilter(column="amount", operator=FilterOperator.GREATER_THAN, value=100)
        assert filt_gt.apply(150) is True
        assert filt_gt.apply(50) is False

        filt_between = ColumnFilter(
            column="amount",
            operator=FilterOperator.BETWEEN,
            value=100,
            value_end=200,
        )
        assert filt_between.apply(150) is True
        assert filt_between.apply(250) is False

    def test_in_operator(self):
        """Test in operator."""
        filt = ColumnFilter(
            column="region",
            operator=FilterOperator.IN,
            value=["USA", "Canada"],
        )
        assert filt.apply("USA") is True
        assert filt.apply("Mexico") is False

    def test_null_filters(self):
        """Test null operators."""
        filt_null = ColumnFilter(column="value", operator=FilterOperator.IS_NULL)
        assert filt_null.apply(None) is True
        assert filt_null.apply("data") is False

        filt_not_null = ColumnFilter(column="value", operator=FilterOperator.IS_NOT_NULL)
        assert filt_not_null.apply(None) is False
        assert filt_not_null.apply("data") is True


class TestDataFilter:
    """Tests for DataFilter."""

    def test_apply_single_filter(self):
        """Test applying single filter."""
        rows = [
            {"region": "USA", "amount": 100},
            {"region": "Canada", "amount": 150},
            {"region": "USA", "amount": 200},
        ]

        filt = ColumnFilter(column="region", operator=FilterOperator.EQUALS, value="USA")
        data_filter = DataFilter([filt])
        result = data_filter.apply_filters(rows)

        assert len(result) == 2
        assert all(r["region"] == "USA" for r in result)

    def test_apply_multiple_filters(self):
        """Test applying multiple filters."""
        rows = [
            {"region": "USA", "amount": 100},
            {"region": "Canada", "amount": 150},
            {"region": "USA", "amount": 200},
        ]

        filters = [
            ColumnFilter(column="region", operator=FilterOperator.EQUALS, value="USA"),
            ColumnFilter(column="amount", operator=FilterOperator.GREATER_THAN, value=150),
        ]
        data_filter = DataFilter(filters)
        result = data_filter.apply_filters(rows)

        assert len(result) == 1
        assert result[0]["region"] == "USA"
        assert result[0]["amount"] == 200

    def test_select_columns(self):
        """Test column selection."""
        rows = [
            {"a": 1, "b": 2, "c": 3},
            {"a": 4, "b": 5, "c": 6},
        ]

        result = DataFilter.select_columns(rows, include_columns=["a", "c"])
        assert all("b" not in row for row in result)
        assert all("a" in row and "c" in row for row in result)

    def test_exclude_columns(self):
        """Test column exclusion."""
        rows = [
            {"a": 1, "b": 2, "c": 3},
            {"a": 4, "b": 5, "c": 6},
        ]

        result = DataFilter.select_columns(rows, exclude_columns=["b"])
        assert all("b" not in row for row in result)
        assert all("a" in row and "c" in row for row in result)

    def test_sort_rows(self):
        """Test sorting rows."""
        rows = [
            {"name": "Charlie", "value": 30},
            {"name": "Alice", "value": 10},
            {"name": "Bob", "value": 20},
        ]

        result = DataFilter.sort_rows(rows, sort_by="value", sort_order="asc")
        assert result[0]["value"] == 10
        assert result[1]["value"] == 20
        assert result[2]["value"] == 30

        result_desc = DataFilter.sort_rows(rows, sort_by="value", sort_order="desc")
        assert result_desc[0]["value"] == 30


class TestCSVExporter:
    """Tests for CSVExporter."""

    def test_export_to_csv(self):
        """Test CSV export."""
        rows = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]

        csv_content = CSVExporter.export_to_csv(rows)
        lines = csv_content.strip().split("\n")

        assert len(lines) == 3  # header + 2 rows
        assert "name" in lines[0]
        assert "age" in lines[0]

    def test_export_empty_rows(self):
        """Test exporting empty rows."""
        csv_content = CSVExporter.export_to_csv([])
        assert csv_content == ""

    def test_get_column_info(self):
        """Test column info extraction."""
        rows = [
            {"name": "Alice", "age": 30, "score": None},
            {"name": "Bob", "age": 25, "score": 95},
        ]

        info = CSVExporter.get_column_info(rows)

        assert "name" in info
        assert info["name"]["type"] == "str"
        assert info["age"]["unique_count"] == 2

        assert info["score"]["null_count"] == 1


class TestDashboardExportAgent:
    """Tests for DashboardExportAgent."""

    def test_init(self, mock_config, mock_client):
        """Test agent initialization."""
        agent = DashboardExportAgent(mock_config, client=mock_client)
        assert agent.name == "DashboardExportAgent"

    def test_export_chart_data(self, mock_config, mock_client, sample_dashboard):
        """Test exporting chart data."""
        agent = DashboardExportAgent(mock_config, client=mock_client)
        result = agent.export_chart_data(sample_dashboard, "sales_chart")

        assert result["chart_id"] == "sales_chart"
        assert result["chart_title"] == "Sales Data"
        assert "data" in result
        assert "row_count" in result

    def test_export_as_csv(self, mock_config, mock_client, sample_dashboard):
        """Test CSV export."""
        agent = DashboardExportAgent(mock_config, client=mock_client)
        csv_content = agent.export_as_csv(sample_dashboard, "sales_chart")

        assert isinstance(csv_content, str)
        assert len(csv_content) > 0

    def test_export_with_filters(self, mock_config, mock_client, sample_dashboard):
        """Test export with filters."""
        agent = DashboardExportAgent(mock_config, client=mock_client)

        filters = [
            {
                "column": "region",
                "operator": "equals",
                "value": "USA",
            }
        ]

        csv_content = agent.export_as_csv(sample_dashboard, "sales_chart", filters=filters)

        assert isinstance(csv_content, str)

    def test_export_with_column_selection(self, mock_config, mock_client, sample_dashboard):
        """Test export with column selection."""
        agent = DashboardExportAgent(mock_config, client=mock_client)

        csv_content = agent.export_as_csv(
            sample_dashboard,
            "sales_chart",
            include_columns=["region", "amount"],
        )

        assert isinstance(csv_content, str)

    def test_export_to_file(self, mock_config, mock_client, sample_dashboard, tmp_path):
        """Test exporting to file."""
        agent = DashboardExportAgent(mock_config, client=mock_client)
        output_file = tmp_path / "export.csv"

        result = agent.export_to_file(sample_dashboard, "sales_chart", str(output_file))

        assert result["status"] == "success"
        assert output_file.exists()

    def test_preview_filtered_data(self, mock_config, mock_client, sample_dashboard):
        """Test data preview."""
        agent = DashboardExportAgent(mock_config, client=mock_client)

        preview = agent.preview_filtered_data(sample_dashboard, "sales_chart", limit=5)

        assert "data" in preview
        assert preview["preview_rows"] <= 5
        assert preview["chart_id"] == "sales_chart"

    def test_get_filterable_columns(self, mock_config, mock_client, sample_dashboard):
        """Test getting filterable columns."""
        agent = DashboardExportAgent(mock_config, client=mock_client)
        columns = agent.get_filterable_columns(sample_dashboard, "sales_chart")

        assert isinstance(columns, dict)

    def test_export_config_to_dict(self):
        """Test ExportConfig serialization."""
        config = ExportConfig(
            chart_id="test",
            include_columns=["a", "b"],
            filters=[
                ColumnFilter(
                    column="x",
                    operator=FilterOperator.EQUALS,
                    value="test",
                )
            ],
        )

        config_dict = config.to_dict()
        assert config_dict["chart_id"] == "test"
        assert len(config_dict["filters"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
