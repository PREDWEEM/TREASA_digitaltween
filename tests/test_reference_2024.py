"""Trazabilidad 2024, calendario bisiesto y consistencia del pool operativo."""
from hashlib import sha256
import json
from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from predweem_twin.core import ModelParameters, PracticalANNModel, run_predweem
from predweem_twin.flows import annual_historical_reference, historical_weekly_max, weekly_flow_groups
from predweem_twin.seasonal import calendar_reference_days, load_local_seasonal_reference
from scripts.import_reference_2024 import build_reference_files

ROOT = Path(__file__).parents[1]
DATA = ROOT / "data/reference"


def test_2024_originals_extraction_and_means_are_preserved(tmp_path):
    source = json.loads((DATA / "tres_arroyos_2024_source.json").read_text())
    folder = tmp_path / "data/reference"
    folder.mkdir(parents=True)
    for section in ("counts", "weather"):
        info = source[section]
        assert sha256((DATA / info["original_file"]).read_bytes()).hexdigest() == info["original_sha256"]
        assert sha256((DATA / info["file"]).read_bytes()).hexdigest() == info["sha256"]
        shutil.copy(DATA / info["original_file"], folder)
    assert build_reference_files(tmp_path) == source
    original = pd.read_excel(DATA / source["counts"]["original_file"])
    counts = pd.read_csv(DATA / source["counts"]["file"], parse_dates=["FECHA"])
    np.testing.assert_allclose(counts.PLM2, original["pl.m2"])
    assert len(counts) == 10 and counts.PLM2.sum() == pytest.approx(7946.666666666667)
    assert counts.PLM2.iloc[0] == pytest.approx(346.666666666667)
    assert counts.FECHA.eq("2024-02-29").sum() == 1
    assert source["counts"]["replicate_count"] is None
    assert set(counts.columns) == {"FECHA", "PLM2"}  # Sin réplicas o errores inventados.


def test_weather_only_uses_dated_records_and_retains_february_29():
    raw = pd.read_csv(DATA / "tres_arroyos_2024_weather_original.csv", sep=";", decimal=",")
    weather = pd.read_csv(DATA / "tres_arroyos_2024_weather.csv", parse_dates=["Fecha"])
    assert len(raw) == 23705 and raw.fecha.isna().sum() == 23370
    assert raw.isna().all(axis=1).sum() == 885
    assert (raw.fecha.isna() & raw.prec.notna()).sum() == 22485
    assert weather.Fecha.tolist() == pd.date_range("2024-01-01", "2024-11-30").tolist()
    assert len(weather) == 335 and weather.Fecha.eq("2024-02-29").sum() == 1
    assert not weather[["TMAX", "TMIN", "Prec"]].isna().any().any()
    np.testing.assert_allclose(weather[["TMAX", "TMIN", "Prec"]], raw.loc[raw.fecha.notna(), ["TMAX", "TMIN", "prec"]])


def test_calendar_alignment_preserves_every_2024_count_and_later_months():
    ref = load_local_seasonal_reference(ROOT, "2027-05-05")
    counts = pd.read_csv(DATA / "tres_arroyos_2024_counts.csv", parse_dates=["FECHA"])
    days = calendar_reference_days(counts.FECHA)
    np.testing.assert_array_equal(days, [46, 59.5, 74, 86, 105, 120, 149, 166, 182, 211])
    progress = ref.set_index("Julian_days").Progreso_2024
    np.testing.assert_allclose(progress.loc[days] * counts.PLM2.sum(), counts.PLM2.cumsum())
    np.testing.assert_allclose(np.diff(progress.loc[days]) * counts.PLM2.sum(), counts.PLM2.iloc[1:])
    assert progress.loc[:45].isna().all()
    assert ref.Campanas_Anos.eq("2023, 2024, 2025, 2026").all()
    assert "2024.xlsx" in ref.Campanas_Excluidas.iloc[0]  # Curva genérica del clasificador excluida.
    # La vista bisiesta reproduce el conteo real del 29/02; marzo no se desplaza.
    leap = annual_historical_reference(ref, "2028-05-05").set_index("Fecha")
    ordinary = annual_historical_reference(ref, "2027-05-05").set_index("Fecha")
    assert leap.loc["2028-02-29", "Progreso_2024"] == pytest.approx(counts.PLM2.iloc[:2].sum() / counts.PLM2.sum())
    for date in ["03-15", "03-27", "04-30", "07-30"]:
        assert leap.loc[f"2028-{date}", "Progreso_2024"] == pytest.approx(ordinary.loc[f"2027-{date}", "Progreso_2024"])
    assert pd.isna(leap.loc["2028-07-31", "Progreso_2024"])
    for annual in [leap, ordinary]:
        assert annual.Flujo_Diario.sum() + annual.Incremento_No_Distribuido.sum() == pytest.approx(1)


def test_2024_not_available_before_last_count_and_pool_has_equal_year_weights():
    before = load_local_seasonal_reference(ROOT, "2024-07-29")
    assert before.Campanas_Anos.eq("2023").all() and "Progreso_2024" not in before
    assert load_local_seasonal_reference(ROOT, "2024-07-30").Campanas_Anos.eq("2023, 2024").all()
    ref = load_local_seasonal_reference(ROOT, "2027-05-05")
    curves = ref[[f"Progreso_{year}" for year in (2023, 2024, 2025, 2026)]]
    np.testing.assert_allclose(ref.Progreso_Mediano, curves.median(axis=1).cummax())
    assert ref.N_Campanas.eq(4).all()
    # El máximo proviene del mismo flujo evaluable y excluye semanas parciales.
    annual = annual_historical_reference(ref, "2027-05-05")
    annual = annual.loc[annual.Fecha.le("2027-10-01")]
    sums = [group.Flujo.sum() for _, group in weekly_flow_groups(annual.Fecha, annual.Flujo_Diario)
            if group.Flujo.notna().sum() == 7]
    assert historical_weekly_max(ref, "2027-05-05") == pytest.approx(max(sums))


def test_leap_year_model_anchor_agrees_with_historical_calendar():
    weather = pd.read_csv(DATA / "tres_arroyos_2024_weather.csv")
    weather["Fecha"] = pd.to_datetime(weather.Fecha) + pd.DateOffset(years=4)
    cutoff = pd.Timestamp("2028-03-27")
    weather = weather.loc[weather.Fecha <= cutoff + pd.Timedelta(days=7)]
    # Serie sintética sólo para comprobar el calendario, no pronóstico real 2028.
    model = PracticalANNModel.from_directory(ROOT / "models")
    reference = load_local_seasonal_reference(ROOT, cutoff)
    actual = run_predweem(weather, model, ModelParameters(), normalization_as_of=cutoff, seasonal_reference=reference)
    expected = annual_historical_reference(reference, cutoff).set_index("Fecha").loc[cutoff, "Progreso_Mediano"]
    row = actual.loc[actual.Fecha.eq(cutoff)].iloc[0]
    assert row.EMERAC_NORMALIZADA == pytest.approx(expected)
    assert row.Progreso_Estacional_Referencia == pytest.approx(expected)
