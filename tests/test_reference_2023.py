"""Origen, unidades, intervalos desconocidos y disponibilidad de la nueva campaña."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from predweem_twin.flows import annual_historical_reference, historical_weekly_max
from predweem_twin.seasonal import load_local_seasonal_reference
from predweem_twin.charts import trajectory_charts
from scripts.import_reference_2023 import build_reference_files

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data/reference"


def test_sources_and_replica_means_are_preserved_and_import_is_reproducible(tmp_path):
    source = json.loads((DATA / "tres_arroyos_2023_source.json").read_text())
    folder = tmp_path / "data/reference"
    folder.mkdir(parents=True)
    for section in ("counts", "weather"):
        info = source[section]
        assert sha256((DATA / info["original_file"]).read_bytes()).hexdigest() == info["original_sha256"]
        assert sha256((DATA / info["file"]).read_bytes()).hexdigest() == info["sha256"]
        shutil.copy(DATA / info["original_file"], folder)
    build_reference_files(tmp_path)
    for filename in ("tres_arroyos_2023_counts.csv", "tres_arroyos_2023_weather.csv"):
        pd.testing.assert_frame_equal(pd.read_csv(DATA / filename), pd.read_csv(folder / filename))
    counts = pd.read_csv(DATA / "tres_arroyos_2023_counts.csv")
    replicas = counts[[f"REP{i}" for i in range(1, 6)]]
    assert len(counts) == 29
    assert counts.N_REPLICAS.eq(5).all()
    assert counts.PLM2.sum() == pytest.approx(2658.8)
    np.testing.assert_allclose(replicas.mean(axis=1), counts.PLM2)
    np.testing.assert_allclose(replicas.std(axis=1, ddof=1), counts.SD_PLM2)
    np.testing.assert_allclose(counts.SD_PLM2 / np.sqrt(5), counts.EE_PLM2)


def test_weather_retains_all_dates_and_missing_temperatures_without_imputation():
    weather = pd.read_csv(DATA / "tres_arroyos_2023_weather.csv", parse_dates=["Fecha"])
    assert len(weather) == 283
    assert weather.Fecha.tolist() == pd.date_range("2023-01-01", "2023-10-10").tolist()
    missing = weather.loc[weather[["TMAX", "TMIN"]].isna().any(axis=1)]
    assert missing.Fecha.tolist() == [pd.Timestamp("2023-06-17")]
    assert missing[["TMAX", "TMIN"]].isna().all().all()
    assert missing.Prec.eq(0).all()  # Cero de lluvia informado, no temperatura imputada.
    assert missing.CalidadDato.eq("Temperaturas_faltantes").all()


def test_2023_curve_preserves_first_positive_count_and_every_later_interval():
    ref = load_local_seasonal_reference(ROOT, "2027-05-05")
    counts = pd.read_csv(DATA / "tres_arroyos_2023_counts.csv", parse_dates=["FECHA"])
    curve = ref.set_index("Julian_days").Progreso_2023
    at_visits = curve.loc[counts.FECHA.dt.dayofyear]
    np.testing.assert_allclose(at_visits * counts.PLM2.sum(), counts.PLM2.cumsum())
    np.testing.assert_allclose(np.diff(at_visits) * counts.PLM2.sum(), counts.PLM2.iloc[1:], atol=1e-10)
    assert curve.loc[:57].isna().all()
    assert curve.loc[58] == pytest.approx(570 / 2658.8)
    assert ref.Julian_days.max() >= 282  # También se conservan ambos registros de octubre.
    assert curve.loc[282] == pytest.approx(1)
    assert "2023.xlsx" in ref.Campanas_Excluidas.iloc[0]  # La curva genérica NO se usa como local.
    assert ref.attrs["source_2023"]["replicate_count"] == 5


def test_first_2023_interval_does_not_become_a_false_daily_or_weekly_peak():
    ref = load_local_seasonal_reference(ROOT, "2027-05-05")
    annual = annual_historical_reference(ref, "2027-05-05")
    first = annual.loc[annual.Fecha.eq("2027-02-27")].iloc[0]
    assert first.Cambio_Composicion_Pool
    assert np.isnan(first.Flujo_Diario)
    assert first.Incremento_No_Distribuido > 0
    assert annual.Flujo_Diario.sum() + annual.Incremento_No_Distribuido.sum() == pytest.approx(1)
    dates = pd.date_range("2027-05-05", periods=8)
    frame = pd.DataFrame({"Fecha": dates, "EMERAC_TWIN": .5, "EMERAC_NORMALIZADA": .5,
                          "EMERREL_TWIN": .01, "TT_DESDE_PICO": 0})
    weekly, _ = trajectory_charts(frame, None, "2027-05-05", seasonal_reference=ref, flow_frequency="Semanal")
    trace = weekly.data[0]
    index = list(pd.to_datetime(trace.x)).index(pd.Timestamp("2027-02-22"))
    assert trace.marker.pattern.shape[index] == "/"
    assert "6/7" in trace.customdata[index][1]
    valid_bars = [v / 100 for v, pattern in zip(trace.y, trace.marker.pattern.shape) if pattern == ""]
    assert historical_weekly_max(ref, "2027-05-05") == pytest.approx(max(valid_bars))


def test_reference_availability_never_uses_future_totals_or_future_years():
    with pytest.raises(ValueError, match="No hay referencias"):
        load_local_seasonal_reference(ROOT, "2023-10-08")
    local_2023 = load_local_seasonal_reference(ROOT, "2023-10-09")
    assert local_2023.Campanas_Anos.eq("2023").all()
    assert "Progreso_2025" not in local_2023 and "Progreso_2026" not in local_2023
    early_2026 = load_local_seasonal_reference(ROOT, "2026-09-15")
    assert early_2026.Campanas_Anos.eq("2023, 2025").all()
    assert "Progreso_2026" not in early_2026
    current = load_local_seasonal_reference(ROOT, "2026-09-16")
    assert current.Campanas_Anos.eq("2023, 2025, 2026").all()
