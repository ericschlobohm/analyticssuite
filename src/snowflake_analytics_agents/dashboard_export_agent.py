from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .agents import BaseAgent
from .dashboard import DashboardConfig
from .export import (
    ColumnFilter,
    CSVExporter,
    DataFilter,
    ExportConfig,
    FilterOperator,
)

logger = logging.getLogger(__name__)


class DashboardExportAgent(BaseAgent):
    """Agent for exporting dashboard data to CSV and other formats with filtering."""

    def export_chart_data(
        self,
        dashboard: DashboardConfig,
        chart_id: str,
        export_config: ExportConfig | None = None,
    ) -> dict[str, Any]:
        """
        Export data from a chart with optional filtering.

        Args:
            dashboard: DashboardConfig containing the chart
            chart_id: ID of the chart to export
            export_config: Optional ExportConfig with filters and options

        Returns:
            Dictionary with exported data and metadata
        """
        logger.info(f"DashboardExportAgent: Exporting data from chart '{chart_id}'")

        # Find the chart
        chart = dashboard.get_chart(chart_id)
        if not chart:
            raise ValueError(f"Chart '{chart_id}' not found in dashboard")

        # Get data from query
        try:
            results = self.client.execute_query(chart.query)
            logger.info(f"Retrieved {len(results)} rows from query")
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            raise

        # Convert results to list of dictionaries
        columns = self._get_columns_from_query(chart.query)
        rows = self._convert_results_to_dicts(results, columns)

        # Apply export configuration if provided
        if export_config:
            rows = self._apply_export_config(rows, export_config)

        return {
            "chart_id": chart_id,
            "chart_title": chart.title,
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
            "data": rows,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def export_as_csv(
        self,
        dashboard: DashboardConfig,
        chart_id: str,
        filters: list[dict[str, Any]] | None = None,
        include_columns: list[str] | None = None,
        exclude_columns: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> str:
        """
        Export chart data as CSV string.

        Args:
            dashboard: DashboardConfig
            chart_id: Chart ID to export
            filters: List of filter dicts with 'column', 'operator', 'value'
            include_columns: Columns to include
            exclude_columns: Columns to exclude
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            CSV string
        """
        logger.info(f"DashboardExportAgent: Exporting chart '{chart_id}' as CSV")

        # Build filter objects
        column_filters = []
        if filters:
            for f in filters:
                col_filter = ColumnFilter(
                    column=f["column"],
                    operator=FilterOperator(f["operator"]),
                    value=f.get("value"),
                    value_end=f.get("value_end"),
                    case_sensitive=f.get("case_sensitive", False),
                )
                column_filters.append(col_filter)

        export_config = ExportConfig(
            chart_id=chart_id,
            include_columns=include_columns,
            exclude_columns=exclude_columns,
            filters=column_filters,
            sort_by=sort_by,
            sort_order=sort_order,
            format="csv",
        )

        # Export data
        export_result = self.export_chart_data(dashboard, chart_id, export_config)
        rows = export_result["data"]

        # Convert to CSV
        csv_content = CSVExporter.export_to_csv(rows, include_header=True)
        logger.info(f"CSV export complete: {len(rows)} rows")
        return csv_content

    def export_to_file(
        self,
        dashboard: DashboardConfig,
        chart_id: str,
        filepath: str,
        filters: list[dict[str, Any]] | None = None,
        include_columns: list[str] | None = None,
        exclude_columns: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        """
        Export chart data to a CSV file.

        Args:
            dashboard: DashboardConfig
            chart_id: Chart ID to export
            filepath: Output file path
            filters: List of filter configurations
            include_columns: Columns to include
            exclude_columns: Columns to exclude
            sort_by: Column to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            Export result with metadata
        """
        logger.info(f"DashboardExportAgent: Exporting to file '{filepath}'")

        csv_content = self.export_as_csv(
            dashboard=dashboard,
            chart_id=chart_id,
            filters=filters,
            include_columns=include_columns,
            exclude_columns=exclude_columns,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write(csv_content)

        return {
            "status": "success",
            "filepath": filepath,
            "rows_exported": csv_content.count("\n") - 1,  # Subtract header
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_filterable_columns(
        self,
        dashboard: DashboardConfig,
        chart_id: str,
        sample_size: int = 100,
    ) -> dict[str, dict[str, Any]]:
        """
        Get available columns and their characteristics for filtering.

        Args:
            dashboard: DashboardConfig
            chart_id: Chart ID
            sample_size: Number of rows to sample

        Returns:
            Dictionary of column metadata for filtering
        """
        logger.info(f"DashboardExportAgent: Analyzing filterable columns for '{chart_id}'")

        chart = dashboard.get_chart(chart_id)
        if not chart:
            raise ValueError(f"Chart '{chart_id}' not found")

        # Get sample data
        try:
            results = self.client.execute_query(chart.query + f" LIMIT {sample_size}")
        except Exception as e:
            logger.error(f"Failed to get column info: {e}")
            raise

        columns = self._get_columns_from_query(chart.query)
        rows = self._convert_results_to_dicts(results, columns)

        # Analyze columns
        column_info = CSVExporter.get_column_info(rows)

        return column_info

    def get_filter_suggestions(
        self,
        dashboard: DashboardConfig,
        chart_id: str,
        column: str,
    ) -> dict[str, Any]:
        """
        Get filter suggestions for a column (unique values, min/max, etc).

        Args:
            dashboard: DashboardConfig
            chart_id: Chart ID
            column: Column name

        Returns:
            Filter suggestions for the column
        """
        logger.info(
            f"DashboardExportAgent: Getting filter suggestions for '{column}' in chart '{chart_id}'"
        )

        chart = dashboard.get_chart(chart_id)
        if not chart:
            raise ValueError(f"Chart '{chart_id}' not found")

        try:
            # Get unique values and stats
            query = f"SELECT DISTINCT {column} FROM ({chart.query}) LIMIT 1000"
            results = self.client.execute_query(query)

            unique_values = [row[0] for row in results if row[0] is not None]

            suggestions = {
                "column": column,
                "unique_values": unique_values[:100],  # First 100
                "total_unique": len(unique_values),
                "sample_count": len(results),
                "has_nulls": any(row[0] is None for row in results),
            }

            # Try to infer type and provide additional suggestions
            if unique_values:
                first_val = unique_values[0]
                if isinstance(first_val, (int, float)):
                    suggestions["type"] = "numeric"
                    suggestions["min"] = min(unique_values)
                    suggestions["max"] = max(unique_values)
                    suggestions["suggested_filters"] = [
                        {"operator": "equals", "label": "Equals"},
                        {"operator": "gt", "label": "Greater than"},
                        {"operator": "lt", "label": "Less than"},
                        {"operator": "between", "label": "Between"},
                    ]
                else:
                    suggestions["type"] = "text"
                    suggestions["suggested_filters"] = [
                        {"operator": "equals", "label": "Equals"},
                        {"operator": "contains", "label": "Contains"},
                        {"operator": "starts_with", "label": "Starts with"},
                        {"operator": "in", "label": "In list"},
                    ]

            logger.info(f"Generated filter suggestions for column '{column}'")
            return suggestions

        except Exception as e:
            logger.error(f"Failed to get filter suggestions: {e}")
            raise

    def preview_filtered_data(
        self,
        dashboard: DashboardConfig,
        chart_id: str,
        filters: list[dict[str, Any]] | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Preview filtered data without full export.

        Args:
            dashboard: DashboardConfig
            chart_id: Chart ID
            filters: List of filter configurations
            limit: Number of rows to preview

        Returns:
            Preview of filtered data
        """
        logger.info(f"DashboardExportAgent: Previewing filtered data for chart '{chart_id}'")

        # Build filter objects
        column_filters = []
        if filters:
            for f in filters:
                col_filter = ColumnFilter(
                    column=f["column"],
                    operator=FilterOperator(f["operator"]),
                    value=f.get("value"),
                    value_end=f.get("value_end"),
                )
                column_filters.append(col_filter)

        export_config = ExportConfig(
            chart_id=chart_id,
            filters=column_filters,
            max_rows=limit,
        )

        export_result = self.export_chart_data(dashboard, chart_id, export_config)

        return {
            "chart_id": chart_id,
            "total_rows_available": export_result["row_count"],
            "preview_rows": min(limit, len(export_result["data"])),
            "data": export_result["data"][:limit],
            "filters_applied": len(column_filters),
        }

    def _apply_export_config(
        self,
        rows: list[dict[str, Any]],
        config: ExportConfig,
    ) -> list[dict[str, Any]]:
        """Apply export configuration to rows."""
        # Apply filters
        if config.filters:
            data_filter = DataFilter(config.filters)
            rows = data_filter.apply_filters(rows)

        # Select columns
        rows = DataFilter.select_columns(
            rows,
            include_columns=config.include_columns,
            exclude_columns=config.exclude_columns,
        )

        # Sort
        if config.sort_by:
            rows = DataFilter.sort_rows(
                rows,
                sort_by=config.sort_by,
                sort_order=config.sort_order,
            )

        # Limit rows
        if config.max_rows:
            rows = rows[: config.max_rows]

        return rows

    def _get_columns_from_query(self, query: str) -> list[str]:
        """Extract column names from query (placeholder - would need proper SQL parsing)."""
        # In production, would use sqlparse or similar
        return ["column_1", "column_2", "column_3"]

    def _convert_results_to_dicts(
        self,
        results: list[tuple],
        columns: list[str],
    ) -> list[dict[str, Any]]:
        """Convert query results to list of dictionaries."""
        return [dict(zip(columns, row)) for row in results]

    def execute(
        self,
        dashboard: DashboardConfig,
        chart_id: str,
        action: str = "preview",
    ) -> dict[str, Any]:
        """Execute the export agent."""
        if action == "preview":
            return self.preview_filtered_data(dashboard, chart_id)
        elif action == "columns":
            return self.get_filterable_columns(dashboard, chart_id)
        else:
            return self.export_chart_data(dashboard, chart_id)
