from __future__ import annotations

import csv
from dataclasses import dataclass, field
from enum import Enum
from io import StringIO
from typing import Any, Literal


class FilterOperator(str, Enum):
    """Supported filter operators."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "gt"
    GREATER_THAN_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"


@dataclass
class ColumnFilter:
    """Filter configuration for a single column."""

    column: str
    operator: FilterOperator
    value: Any | None = None
    value_end: Any | None = None  # For BETWEEN operator
    case_sensitive: bool = False

    def apply(self, row_value: Any) -> bool:
        """
        Apply filter to a value.

        Args:
            row_value: Value to check

        Returns:
            True if value passes filter, False otherwise
        """
        if self.operator == FilterOperator.IS_NULL:
            return row_value is None
        if self.operator == FilterOperator.IS_NOT_NULL:
            return row_value is not None
        if row_value is None:
            return False

        # Convert to string for text operations
        if self.operator in [
            FilterOperator.CONTAINS,
            FilterOperator.NOT_CONTAINS,
            FilterOperator.STARTS_WITH,
            FilterOperator.ENDS_WITH,
        ]:
            row_str = str(row_value)
            val_str = str(self.value) if self.value else ""

            if not self.case_sensitive:
                row_str = row_str.lower()
                val_str = val_str.lower()

            if self.operator == FilterOperator.CONTAINS:
                return val_str in row_str
            elif self.operator == FilterOperator.NOT_CONTAINS:
                return val_str not in row_str
            elif self.operator == FilterOperator.STARTS_WITH:
                return row_str.startswith(val_str)
            elif self.operator == FilterOperator.ENDS_WITH:
                return row_str.endswith(val_str)

        # Numeric/comparison operators
        if self.operator == FilterOperator.EQUALS:
            return row_value == self.value
        elif self.operator == FilterOperator.NOT_EQUALS:
            return row_value != self.value
        elif self.operator == FilterOperator.GREATER_THAN:
            return row_value > self.value
        elif self.operator == FilterOperator.GREATER_THAN_EQUAL:
            return row_value >= self.value
        elif self.operator == FilterOperator.LESS_THAN:
            return row_value < self.value
        elif self.operator == FilterOperator.LESS_THAN_EQUAL:
            return row_value <= self.value
        elif self.operator == FilterOperator.IN:
            return row_value in (self.value or [])
        elif self.operator == FilterOperator.NOT_IN:
            return row_value not in (self.value or [])
        elif self.operator == FilterOperator.BETWEEN:
            return self.value <= row_value <= self.value_end

        return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "column": self.column,
            "operator": self.operator.value,
            "value": self.value,
            "value_end": self.value_end,
            "case_sensitive": self.case_sensitive,
        }


@dataclass
class ExportConfig:
    """Configuration for data export."""

    chart_id: str
    include_columns: list[str] | None = None  # None = all columns
    exclude_columns: list[str] | None = None
    filters: list[ColumnFilter] = field(default_factory=list)
    sort_by: str | None = None
    sort_order: Literal["asc", "desc"] = "asc"
    max_rows: int | None = None
    format: Literal["csv", "json"] = "csv"
    include_header: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chart_id": self.chart_id,
            "include_columns": self.include_columns,
            "exclude_columns": self.exclude_columns,
            "filters": [f.to_dict() for f in self.filters],
            "sort_by": self.sort_by,
            "sort_order": self.sort_order,
            "max_rows": self.max_rows,
            "format": self.format,
            "include_header": self.include_header,
        }


class DataFilter:
    """Helper class for filtering data rows."""

    def __init__(self, filters: list[ColumnFilter]):
        """
        Initialize filter.

        Args:
            filters: List of column filters to apply
        """
        self.filters = filters

    def apply_filters(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Apply all filters to rows.

        Args:
            rows: List of row dictionaries

        Returns:
            Filtered list of rows
        """
        filtered = []
        for row in rows:
            if self._matches_all_filters(row):
                filtered.append(row)
        return filtered

    def _matches_all_filters(self, row: dict[str, Any]) -> bool:
        """Check if row matches all filters."""
        for filter_config in self.filters:
            value = row.get(filter_config.column)
            if not filter_config.apply(value):
                return False
        return True

    @staticmethod
    def select_columns(
        rows: list[dict[str, Any]],
        include_columns: list[str] | None = None,
        exclude_columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Select/exclude specific columns from rows.

        Args:
            rows: List of row dictionaries
            include_columns: Columns to include (None = all)
            exclude_columns: Columns to exclude

        Returns:
            Rows with selected columns only
        """
        if not rows:
            return rows

        selected = []
        all_columns = set(rows[0].keys())

        if include_columns:
            columns_to_keep = set(include_columns) & all_columns
        else:
            columns_to_keep = all_columns

        if exclude_columns:
            columns_to_keep -= set(exclude_columns)

        for row in rows:
            selected_row = {k: v for k, v in row.items() if k in columns_to_keep}
            selected.append(selected_row)

        return selected

    @staticmethod
    def sort_rows(
        rows: list[dict[str, Any]],
        sort_by: str,
        sort_order: str = "asc",
    ) -> list[dict[str, Any]]:
        """
        Sort rows by column.

        Args:
            rows: List of row dictionaries
            sort_by: Column to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Sorted rows
        """
        if not rows or sort_by not in rows[0]:
            return rows

        reverse = sort_order.lower() == "desc"
        return sorted(rows, key=lambda x: x.get(sort_by, ""), reverse=reverse)


class CSVExporter:
    """Helper class for CSV export."""

    @staticmethod
    def export_to_csv(
        rows: list[dict[str, Any]],
        include_header: bool = True,
        delimiter: str = ",",
    ) -> str:
        """
        Export rows to CSV string.

        Args:
            rows: List of row dictionaries
            include_header: Whether to include header row
            delimiter: CSV delimiter character

        Returns:
            CSV string
        """
        if not rows:
            return ""

        output = StringIO()
        columns = list(rows[0].keys())

        writer = csv.DictWriter(output, fieldnames=columns, delimiter=delimiter)

        if include_header:
            writer.writeheader()

        writer.writerows(rows)
        return output.getvalue()

    @staticmethod
    def export_to_file(
        rows: list[dict[str, Any]],
        filepath: str,
        include_header: bool = True,
        delimiter: str = ",",
    ) -> None:
        """
        Export rows to CSV file.

        Args:
            rows: List of row dictionaries
            filepath: Path to output file
            include_header: Whether to include header row
            delimiter: CSV delimiter character
        """
        csv_content = CSVExporter.export_to_csv(rows, include_header, delimiter)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write(csv_content)

    @staticmethod
    def get_column_info(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """
        Analyze columns in data.

        Args:
            rows: List of row dictionaries

        Returns:
            Dictionary of column info (type, null_count, unique_count)
        """
        if not rows:
            return {}

        columns = {}
        all_keys = set()
        for row in rows:
            all_keys.update(row.keys())

        for col in all_keys:
            values = [row.get(col) for row in rows]
            non_null_values = [v for v in values if v is not None]

            columns[col] = {
                "type": type(non_null_values[0]).__name__ if non_null_values else "unknown",
                "null_count": len([v for v in values if v is None]),
                "unique_count": len({str(v) for v in non_null_values}),
                "sample_values": list({str(v) for v in non_null_values})[:5],
            }

        return columns
