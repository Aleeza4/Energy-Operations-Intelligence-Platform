"""Reusable UI components for the EOIP Streamlit application."""

from eoip.app.components.charts import (
    apply_eoip_chart_style,
    plotly_chart_config,
    render_plotly_chart,
)
from eoip.app.components.common import (
    MetricCard,
    StatusLevel,
    dashboard_loading,
    load_dashboard_data,
    render_dataframe,
    render_divider,
    render_empty_state,
    render_metric_card,
    render_metric_row,
    render_page_intro,
    render_section_header,
    render_status,
)
from eoip.app.components.downloads import (
    build_report_filename,
    dataframe_to_csv_bytes,
    render_csv_download,
)
from eoip.app.components.filters import (
    DEFAULT_EQUIPMENT,
    DEFAULT_PLANTS,
    FilterSelection,
    format_filter_caption,
    get_filter_selection,
    initialize_filter_state,
    normalize_filter_selection,
    render_global_filters,
    set_filter_selection,
)

__all__ = [
    "DEFAULT_EQUIPMENT",
    "DEFAULT_PLANTS",
    "FilterSelection",
    "MetricCard",
    "StatusLevel",
    "apply_eoip_chart_style",
    "build_report_filename",
    "dataframe_to_csv_bytes",
    "dashboard_loading",
    "format_filter_caption",
    "get_filter_selection",
    "initialize_filter_state",
    "load_dashboard_data",
    "normalize_filter_selection",
    "plotly_chart_config",
    "render_csv_download",
    "render_dataframe",
    "render_divider",
    "render_empty_state",
    "render_global_filters",
    "render_metric_card",
    "render_metric_row",
    "render_page_intro",
    "render_plotly_chart",
    "render_section_header",
    "render_status",
    "set_filter_selection",
]
