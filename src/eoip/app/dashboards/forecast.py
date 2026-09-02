"""Forecast dashboard for the EOIP Streamlit application."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from eoip.app import data_access
from eoip.app.components import (
    MetricCard,
    eoip_forecast_style,
    render_csv_download,
    render_dataframe,
    render_empty_state,
    render_global_filters,
    render_metric_row,
    render_page_intro,
    render_plotly_chart,
    render_section_header,
)
from eoip.app.components.filters import (
    SESSION_END_DATE_KEY,
    SESSION_START_DATE_KEY,
)
from eoip.app.data_filters import FilterDimensions, PageDataContract
from eoip.app.navigation import navigate_to
from eoip.app.theme import (
    EOIP_PRIMARY,
    EOIP_SECONDARY,
)


@st.cache_data(show_spinner=False)
def _model_comparison_data() -> pd.DataFrame:
    """Return temporary forecasting-model comparison data."""
    return pd.DataFrame(
        {
            "Model": [
                "Naive Baseline",
                "Moving Average",
                "Prophet",
            ],
            "MAE (MWh)": [
                39.4,
                31.8,
                22.6,
            ],
            "RMSE (MWh)": [
                51.2,
                42.5,
                30.7,
            ],
            "MAPE (%)": [
                8.7,
                6.9,
                4.8,
            ],
        }
    )


@st.cache_data(show_spinner=False)
def _plant_forecast_data() -> pd.DataFrame:
    """Return temporary plant-level forecast data."""
    return pd.DataFrame(
        {
            "Plant": [
                "Solar Plant A",
                "Solar Plant B",
                "Solar Plant C",
                "Solar Plant D",
            ],
            "Tomorrow Forecast (MWh)": [
                158.0,
                132.0,
                169.0,
                103.0,
            ],
            "7-Day Forecast (MWh)": [
                1118.0,
                941.0,
                1196.0,
                734.0,
            ],
            "Forecast Confidence (%)": [
                94.0,
                91.0,
                95.0,
                87.0,
            ],
        }
    )


def calculate_forecast_variance(
    actual: float, forecast: float
) -> tuple[float, float | None]:
    """Return actual-minus-forecast variance with a safe percentage."""
    variance = actual - forecast
    percentage = None if forecast == 0 else variance / forecast * 100
    return variance, percentage


def get_default_forecast_date_range(forecast: pd.DataFrame) -> tuple[date, date]:
    """Return the actual date window supported by the forecast dataset."""
    if forecast.empty:
        today = date.today()
        return today - timedelta(days=6), today

    timestamps = pd.to_datetime(forecast["Date"], errors="coerce")
    valid = timestamps.dropna()
    if valid.empty:
        today = date.today()
        return today - timedelta(days=6), today

    start = valid.dt.date.min()
    end = valid.dt.date.max()
    return start, end


def render() -> None:
    """Render the EOIP Forecast Dashboard."""
    forecast_source = data_access.get_forecasts()
    default_start, default_end = get_default_forecast_date_range(forecast_source)
    session_start = st.session_state.get(SESSION_START_DATE_KEY)
    session_end = st.session_state.get(SESSION_END_DATE_KEY)
    if (
        not isinstance(session_start, date)
        or not isinstance(session_end, date)
        or session_start < default_start
        or session_end > default_end
    ):
        st.session_state[SESSION_START_DATE_KEY] = default_start
        st.session_state[SESSION_END_DATE_KEY] = default_end

    render_page_intro(
        title="Forecast Intelligence",
        icon="forecast",
        description=(
            "Energy forecasting, uncertainty ranges, model accuracy, "
            "and forward-looking production intelligence."
        ),
    )
    filters = render_global_filters(show_plant=False)
    contract = PageDataContract(
        filters,
        {
            "forecast": forecast_source,
            "models": _model_comparison_data(),
            "plant_forecast": _plant_forecast_data(),
        },
    )
    forecast = contract.scoped(
        "forecast", dimensions=FilterDimensions(plant=False, equipment=False)
    )
    if forecast.empty:
        render_empty_state(
            title="No forecast data",
            message="No forecast records exist for the selected reporting period.",
        )
        return

    forecast_total = float(forecast["Forecast Energy (MWh)"].sum())
    first_day_forecast = float(forecast.iloc[0]["Forecast Energy (MWh)"])
    models = contract.scoped(
        "models",
        dimensions=FilterDimensions(plant=False, equipment=False, date=False),
    )
    plant_forecast = contract.scoped(
        "plant_forecast",
        dimensions=FilterDimensions(plant=False, equipment=False, date=False),
    )
    average_range = float(
        (forecast["Upper Bound (MWh)"] - forecast["Lower Bound (MWh)"]).mean()
    )
    horizon_days = int((forecast["Date"].max() - forecast["Date"].min()).days + 1)

    render_section_header(
        "Forecast Outlook",
        description=(
            "Forward-looking portfolio energy and model-performance indicators."
        ),
    )

    render_metric_row(
        (
            MetricCard(
                label="First Day Forecast",
                value=f"{first_day_forecast:.0f} MWh",
            ),
            MetricCard(
                label="Selected-Period Forecast",
                value=f"{forecast_total / 1000:.2f} GWh",
            ),
            MetricCard(
                label="Forecast Horizon",
                value=f"{horizon_days} days",
            ),
            MetricCard(
                label="Average Forecast Range",
                value=f"{average_range:.0f} MWh",
                subtitle="Upper bound minus lower bound",
            ),
        )
    )

    render_section_header(
        "Expected Performance",
        description=("Expected portfolio production with forecast uncertainty bounds."),
    )

    figure = go.Figure()
    forecast_style = eoip_forecast_style()

    figure.add_trace(
        go.Scatter(
            x=forecast["Date"],
            y=forecast["Upper Bound (MWh)"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=forecast["Date"],
            y=forecast["Lower Bound (MWh)"],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor=forecast_style["confidence_fill"],
            name="Forecast Range",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=forecast["Date"],
            y=forecast["Forecast Energy (MWh)"],
            mode="lines+markers",
            name="Forecast Energy",
            line=forecast_style["forecast_line"],
            marker={"color": forecast_style["forecast_line"]["color"]},
        )
    )

    figure.update_layout(
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        xaxis_title="Date",
        yaxis_title="Energy (MWh)",
        legend_title_text="",
    )

    render_plotly_chart(
        figure,
        data=forecast,
        time_series=True,
    )

    render_section_header(
        "Forecast Detail",
        description="Portfolio forecast and supported uncertainty bounds by date.",
    )
    render_dataframe(
        forecast,
        column_config={
            "Date": st.column_config.DateColumn(format="DD MMM YYYY"),
            "Forecast Energy (MWh)": st.column_config.NumberColumn(format="%.0f MWh"),
            "Lower Bound (MWh)": st.column_config.NumberColumn(format="%.0f MWh"),
            "Upper Bound (MWh)": st.column_config.NumberColumn(format="%.0f MWh"),
        },
    )

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Model Diagnostics",
            description=("Global backtesting accuracy across forecasting approaches."),
        )

        model_long = models.melt(
            id_vars="Model",
            value_vars=[
                "MAE (MWh)",
                "RMSE (MWh)",
            ],
            var_name="Metric",
            value_name="Error",
        )

        model_figure = px.bar(
            model_long,
            x="Model",
            y="Error",
            color="Metric",
            color_discrete_map={
                "MAE (MWh)": EOIP_PRIMARY,
                "RMSE (MWh)": EOIP_SECONDARY,
            },
            barmode="group",
        )

        model_figure.update_layout(
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            legend_title_text="",
        )

        render_plotly_chart(
            model_figure,
            data=model_long,
        )

    with right_column:
        render_section_header(
            "Model Accuracy",
            description=("Global error metrics used for model selection."),
        )

        render_dataframe(
            models,
        )

    render_section_header(
        "Plant-Level Forecast",
        description=("Portfolio plant expectations; this table is not date-filtered."),
    )

    render_dataframe(
        plant_forecast,
        column_config={
            "Forecast Confidence (%)": st.column_config.ProgressColumn(
                "Forecast Confidence (%)",
                min_value=0.0,
                max_value=100.0,
                format="%.0f%%",
            )
        },
    )
    render_csv_download(
        forecast,
        label="Download forecast CSV",
        report_name="energy-forecast",
        filters=filters,
        key="forecast_download",
    )
    render_csv_download(
        models,
        label="Download global model comparison CSV",
        report_name="forecast-model-comparison",
        key="forecast_models_download",
    )

    render_section_header(
        "Investigation Actions",
        description="Continue with portfolio-level operational context.",
    )
    with st.container(horizontal=True):
        if st.button("Review operations", key="forecast_open_operations"):
            navigate_to("operations")
