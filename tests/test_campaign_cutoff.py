"""Fuentes SIGA/ECMWF y cierre de la campaña 2026, sin consultas de red."""

from datetime import date, timedelta
import json

import pandas as pd
import pytest

import actualizar_meteo_tres_arroyos as updater
from predweem_twin.weather import operational_weather_window


def weather_series(start, end, kind):
    frame = pd.DataFrame({"Fecha": pd.date_range(start, end).strftime("%Y-%m-%d")})
    frame["TMAX"], frame["TMIN"], frame["TMEDIA"], frame["Prec"] = 20., 10., 15., 1.
    frame["TipoDato"] = kind
    frame["Fuente"] = {
        "Observado": "SIGA_INTA_TRES_ARROYOS_BARROW",
        "Provisional": "ECMWF_IFS_HISTORICO", "Pronostico": "ECMWF_IFS_ENS_025",
    }[kind]
    if kind == "Pronostico":
        for column in ("TMAX", "TMIN", "TMEDIA", "Prec"):
            frame[column + "_P50"] = frame[column]
        frame["N_miembros"] = 51
    return updater.asegurar_columnas(frame)


@pytest.mark.parametrize("cutoff,expected", [("2026-09-28", 3), ("2026-10-01", 0), ("2026-10-10", 0)])
def test_twin_horizon_stops_at_campaign_end(cutoff, expected):
    frame = pd.DataFrame({"Fecha": pd.date_range("2026-09-25", "2026-10-10")})
    window, meta = operational_weather_window(frame, as_of=cutoff)
    assert window.Fecha.max() == pd.Timestamp("2026-10-01")
    assert meta["forecast_days_expected"] == expected
    assert meta["forecast_days_available"] == expected
    assert meta["complete"]


@pytest.mark.parametrize("today", [date(2026, 9, 19), date(2026, 9, 29), date(2026, 10, 1), date(2026, 10, 8)])
def test_update_keeps_observed_provisional_and_forecast_separate(monkeypatch, tmp_path, today):
    last_observed = min(today - timedelta(days=4), updater.CAMPANIA_END)
    yesterday = min(today - timedelta(days=1), updater.CAMPANIA_END)
    last_forecast = min(today + timedelta(days=6), updater.CAMPANIA_END)
    observed = weather_series(updater.CAMPANIA_START, last_observed, "Observado")
    provisional = weather_series(last_observed + timedelta(days=1), yesterday, "Provisional")
    forecast = weather_series(today, last_forecast, "Pronostico")
    monkeypatch.setattr(updater, "hoy_argentina", lambda: today)
    def get_siga(start, end, archivo_forzado=None):
        assert end == yesterday
        return observed, "test"
    def get_bridge(start, end):
        assert end == yesterday
        return provisional
    monkeypatch.setattr(updater, "obtener_siga_dataframe", get_siga)
    monkeypatch.setattr(updater, "cargar_provisional_ecmwf", get_bridge)
    monkeypatch.setattr(updater, "cargar_pronostico_ecmwf", lambda: forecast)
    monkeypatch.setattr(updater, "ARCHIVO_ESTADO", tmp_path / "state.json")
    result = updater.construir_meteo_daily(tmp_path / "meteo.csv")
    expected_end = updater.CAMPANIA_END if today > updater.CAMPANIA_END else last_forecast
    assert result.Fecha.max() == expected_end.isoformat()
    assert len(result) == (expected_end - updater.CAMPANIA_START).days + 1
    assert result.TipoDato.eq("Observado").sum() == len(observed)
    assert result.TipoDato.eq("Provisional").sum() == len(provisional)
    assert result.TipoDato.eq("Pronostico").sum() == len(forecast)
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["fecha_fin_campania"] == "2026-10-01"
    assert state["huecos_finales"] == []


def test_closed_campaign_does_not_query_ensemble(monkeypatch):
    monkeypatch.setattr(updater, "hoy_argentina", lambda: date(2026, 10, 2))
    def unexpected(*args, **kwargs):
        raise AssertionError("No debe consultar ECMWF ENS después del cierre")
    monkeypatch.setattr(updater, "consultar_ecmwf_ens", unexpected)
    assert updater.cargar_pronostico_ecmwf().empty
