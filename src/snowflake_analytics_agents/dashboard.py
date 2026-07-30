from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class ChartType(str, Enum):
    """Supported chart types."""

    LINE = "line"
    BAR = "bar"
    COLUMN = "column"
    SCATTER = "scatter"
    PIE = "pie"
    TABLE = "table"
    METRIC = "metric"
    HEATMAP = "heatmap"
    AREA = "area"
    FUNNEL = "funnel"


class DashboardLayout(str, Enum):
    """Dashboard layout templates."""

    SINGLE_COLUMN = "single_column"
    TWO_COLUMN = "two_column"
    THREE_COLUMN = "three_column"
    GRID = "grid"
    CUSTOM = "custom"


@dataclass
class ChartConfig:
    """Configuration for a single chart/visualization."""

    id: str
    title: str
    chart_type: ChartType
    query: str
    x_column: str | None = None
    y_column: str | None = None
    dimensions: list[str] = field(default_factory=list)
    measures: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    color_scheme: str = "default"
    height: int = 400
    width: int = 500
    aggregation: str | None = None
    sort_by: str | None = None
    show_legend: bool = True
    show_grid: bool = True
    refresh_interval: int = 300  # seconds
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.chart_type.value,
            "query": self.query,
            "x_column": self.x_column,
            "y_column": self.y_column,
            "dimensions": self.dimensions,
            "measures": self.measures,
            "filters": self.filters,
            "color_scheme": self.color_scheme,
            "height": self.height,
            "width": self.width,
            "aggregation": self.aggregation,
            "sort_by": self.sort_by,
            "show_legend": self.show_legend,
            "show_grid": self.show_grid,
            "refresh_interval": self.refresh_interval,
            "description": self.description,
        }


@dataclass
class FilterConfig:
    """Configuration for dashboard-level filters."""

    id: str
    name: str
    filter_type: Literal["date_range", "dropdown", "search", "range_slider"]
    column: str
    values: list[Any] | None = None
    default_value: Any | None = None
    multi_select: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.filter_type,
            "column": self.column,
            "values": self.values,
            "default_value": self.default_value,
            "multi_select": self.multi_select,
        }


@dataclass
class DashboardConfig:
    """Complete dashboard configuration."""

    id: str
    name: str
    description: str
    layout: DashboardLayout
    charts: list[ChartConfig] = field(default_factory=list)
    filters: list[FilterConfig] = field(default_factory=list)
    refresh_interval: int = 300  # seconds
    theme: str = "light"
    rows: int = 2
    cols: int = 2
    auto_refresh: bool = True
    shared: bool = False
    tags: list[str] = field(default_factory=list)
    owner: str = ""
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "layout": self.layout.value,
            "charts": [chart.to_dict() for chart in self.charts],
            "filters": [f.to_dict() for f in self.filters],
            "refresh_interval": self.refresh_interval,
            "theme": self.theme,
            "rows": self.rows,
            "cols": self.cols,
            "auto_refresh": self.auto_refresh,
            "shared": self.shared,
            "tags": self.tags,
            "owner": self.owner,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def add_chart(self, chart: ChartConfig) -> None:
        """Add a chart to the dashboard."""
        self.charts.append(chart)

    def add_filter(self, filter_config: FilterConfig) -> None:
        """Add a filter to the dashboard."""
        self.filters.append(filter_config)

    def get_chart(self, chart_id: str) -> ChartConfig | None:
        """Get a chart by ID."""
        for chart in self.charts:
            if chart.id == chart_id:
                return chart
        return None
