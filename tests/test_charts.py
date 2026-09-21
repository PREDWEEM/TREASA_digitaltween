"""Límites temporales del fondo histórico frente al pronóstico operativo."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from predweem_twin.charts import annual_historical_reference, trajectory_charts
from predweem_twin.seasonal import load_local_seasonal_reference


ROOT = Path(__file__).parents[1]


@pytest.fixture
def reference():
    return load_local_seasonal_reference(ROOT, as_of="2027-05-05")


def trajectory():
    dates = pd.date_range("2027-04-25", "2027-05-20")
    return pd.DataFrame({
        "Fecha": dates,
        "EMERAC_NORMALIZADA": np.linspace(.3, .7, len(dates)),
        "EMERAC_TWIN": np.linspace(.4, .8, len(dates)),
        "EMERREL_TWIN": .016,
        "TT_DESDE_PICO": np.linspace(500, 900, len(dates)),
    })


def test_annual_reference_keeps_unknown_periods_and_observed_2026_window(reference):
    annual = annual_historical_reference(reference, "2027-05-05")
    assert annual.Fecha.tolist() == pd.date_range("2027-01-01", "2027-12-31").tolist()
    assert annual.loc[annual.Fecha.lt("2027-02-05"), "Progreso_2026"].isna().all()
    assert annual.loc[annual.Fecha.gt("2027-09-16"), "Progreso_2026"].isna().all()
    last_day = pd.Timestamp("2027-01-01") + pd.Timedelta(days=reference.Julian_days.max() - 1)
    outside = annual.Fecha.gt(last_day)
    assert annual.loc[outside, ["Progreso_Mediano", "Flujo_Diario"]].isna().all().all()
    assert annual.Flujo_Diario.sum() == pytest.approx(1.)


def test_reference_preserves_month_day_in_leap_year(reference):
    normal = annual_historical_reference(reference, "2027-05-05").set_index("Fecha")
    leap = annual_historical_reference(reference, "2028-05-05").set_index("Fecha")
    assert leap.loc["2028-03-01", "Progreso_Mediano"] == normal.loc["2027-03-01", "Progreso_Mediano"]
    assert leap.loc["2028-02-29", "Progreso_Mediano"] == pytest.approx(
        (normal.loc["2027-02-28", "Progreso_Mediano"] + normal.loc["2027-03-01", "Progreso_Mediano"]) / 2
    )


def test_chart_shows_annual_context_without_extending_weather_or_changing_state(reference):
    frame = trajectory()
    before = frame.copy(deep=True)
    observations = pd.DataFrame({
        "Fecha": pd.to_datetime(["2027-05-03", "2027-05-18"]), "Observado": [.5, .9]
    })
    daily, cumulative = trajectory_charts(frame, observations, "2027-05-05", seasonal_reference=reference)
    pd.testing.assert_frame_equal(frame, before)
    for fig in (daily, cumulative):
        assert pd.Timestamp(fig.layout.xaxis.range[1]) == pd.Timestamp("2027-10-01")
        assert "yaxis2" not in fig.layout
    assert daily.layout.xaxis.range == cumulative.layout.xaxis.range
    assert all(trace.type == "bar" for trace in daily.data)
    assert all(trace.type == "scatter" for trace in cumulative.data)
    traces = {trace.name: trace for trace in (*daily.data, *cumulative.data)}
    history = traces["Pool histórico · orientativo"]
    assert pd.to_datetime(history.x)[np.isfinite(history.y)].max() > pd.Timestamp("2027-05-12")
    assert pd.to_datetime(traces["Estado actualizado"].x).max() == pd.Timestamp("2027-05-05")
    assert pd.to_datetime(traces["Proyección meteorológica · hasta 7 días"].x).max() == pd.Timestamp("2027-05-12")
    assert pd.to_datetime(traces["Conteo de campo"].x).max() == pd.Timestamp("2027-05-03")
    for trace in (*daily.data, *cumulative.data):
        assert trace.yaxis in (None, "y")
        assert pd.to_datetime(trace.x).max() <= pd.Timestamp("2027-10-01")
        if "histórico" not in trace.name.casefold():
            assert pd.to_datetime(trace.x).max() <= pd.Timestamp("2027-05-12")
    for fig in (daily, cumulative):
        assert "Sin referencia disponible" not in [item.text for item in fig.layout.annotations]


def test_historical_backdrop_does_not_leak_2026_into_earlier_cutoffs():
    ref = load_local_seasonal_reference(ROOT, as_of="2026-05-05")
    annual = annual_historical_reference(ref, "2026-05-05")
    assert "Progreso_2026" not in annual
    assert annual.attrs["campaigns"] == "2025"


def test_no_forecast_trace_when_weather_ends_at_cutoff(reference):
    frame = trajectory().loc[lambda data: data.Fecha.le("2027-05-05")]
    figures = trajectory_charts(frame, None, "2027-05-05", seasonal_reference=reference)
    for fig in figures:
        assert not any("Proyección meteorológica" in trace.name for trace in fig.data)
        assert not any(item.text == "Pronóstico 7 d" for item in fig.layout.annotations)


def test_field_audit_is_only_in_cumulative_chart_and_stops_at_cutoff(reference):
    audit = pd.DataFrame({
        "Fecha_asimilada": pd.to_datetime(["2027-05-03", "2027-05-18"]),
        "Estado_campo_estimado": [.5, .9],
    })
    daily, cumulative = trajectory_charts(trajectory(), None, "2027-05-05", audit, seasonal_reference=reference)
    assert not any(trace.name == "Estado estimado desde campo" for trace in daily.data)
    field = next(trace for trace in cumulative.data if trace.name == "Estado estimado desde campo")
    assert field.yaxis in (None, "y")
    assert pd.to_datetime(field.x).max() == pd.Timestamp("2027-05-03")
