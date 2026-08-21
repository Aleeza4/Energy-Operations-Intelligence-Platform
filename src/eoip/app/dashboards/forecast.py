"""Forecast dashboard for the EOIP Streamlit application."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from eoip.app.components import (
    MetricCard,
    format_filter_caption,
    render_csv_download,
    render_dataframe,
    render_global_filters,
    render_metric_row,
    render_page_intro,
    render_plotly_chart,
    render_section_header,
    render_status,
)
from eoip.app.data_filters import apply_dataframe_filters


@st.cache_data(show_spinner=False)
def _forecast_data() -> pd.DataFrame:
    """Return temporary energy-forecast data."""
    dates = pd.date_range(
        start="2026-08-21",
        periods=14,
        freq="D",
    )

    return pd.DataFrame(
        {
            "Date": dates,
            "Forecast Energy (MWh)": [
                548.0,
                562.0,
                571.0,
                559.0,
                584.0,
                592.0,
                575.0,
                601.0,
                610.0,
                598.0,
                615.0,
                623.0,
                607.0,
                631.0,
            ],
            "Lower Bound (MWh)": [
                518.0,
                531.0,
                540.0,
                527.0,
                551.0,
                559.0,
                542.0,
                567.0,
                575.0,
                563.0,
                580.0,
                588.0,
                572.0,
                595.0,
            ],
            "Upper Bound (MWh)": [
                578.0,
                593.0,
                602.0,
                591.0,
                617.0,
                625.0,
                608.0,
                635.0,
                645.0,
                633.0,
                650.0,
                658.0,
                642.0,
                667.0,
            ],
        }
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


def render() -> None:
    """Render the EOIP Forecast Dashboard."""
    render_page_intro(
        title="Forecast Dashboard",
        icon="📈",
        description=(
            "Energy forecasting, uncertainty ranges, model accuracy, "
            "and forward-looking production intelligence."
        ),
    )
    filters = render_global_filters()
    st.caption(format_filter_caption(filters, show_equipment=False))

    render_status(
        "Forecasting intelligence is operational.",
        level="success",
    )

    render_section_header(
        "Forecast Overview",
        description=(
            "Forward-looking portfolio energy and model-performance indicators."
        ),
    )

    render_metric_row(
        (
            MetricCard(
                label="Tomorrow Forecast",
                value="562 MWh",
                delta="+2.6%",
            ),
            MetricCard(
                label="7-Day Forecast",
                value="3.99 GWh",
                delta="+3.1%",
            ),
            MetricCard(
                label="Forecast MAPE",
                value="4.8%",
                delta="-0.7%",
            ),
            MetricCard(
                label="Forecast Confidence",
                value="92.0%",
                delta="+1.4%",
            ),
        )
    )

    st.write("")

    render_section_header(
        "14-Day Energy Forecast",
        description=("Expected portfolio production with forecast uncertainty bounds."),
    )

    forecast = apply_dataframe_filters(_forecast_data(), filters)

    figure = go.Figure()

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
            name="Forecast Range",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=forecast["Date"],
            y=forecast["Forecast Energy (MWh)"],
            mode="lines+markers",
            name="Forecast Energy",
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

    left_column, right_column = st.columns((3, 2))

    with left_column:
        render_section_header(
            "Model Performance",
            description=("Backtesting accuracy across forecasting approaches."),
        )

        models = _model_comparison_data()

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
            description=("Backtesting error metrics used for model selection."),
        )

        render_dataframe(
            models,
        )

    render_section_header(
        "Plant-Level Forecast",
        description=("Forward production expectations and confidence by plant."),
    )

    plant_forecast = apply_dataframe_filters(_plant_forecast_data(), filters)

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
        label="Download model comparison CSV",
        report_name="forecast-model-comparison",
        filters=filters,
        key="forecast_models_download",
    )
