"""Conservación de conteos, disponibilidad temporal e integración operativa."""

from pathlib import Path
import shutil

import numpy as np
import pandas as pd
import pytest

from predweem_twin.core import ModelParameters, PracticalANNModel, run_predweem
from predweem_twin.seasonal import load_local_seasonal_reference, load_seasonal_reference


ROOT = Path(__file__).parents[1]
COUNTS = Path("data/calibration/tres_arroyos_2026_counts.csv")


def test_2026_conserves_each_observed_interval_and_does_not_invent_early_zeros():
    reference = load_local_seasonal_reference(ROOT, as_of="2027-03-27")
    counts = pd.read_csv(ROOT / COUNTS, parse_dates=["FECHA"])
    curve = reference.set_index("Julian_days")["Progreso_2026"]
    at_visits = curve.loc[counts.FECHA.dt.dayofyear].to_numpy()
    total = counts.PLM2.sum()
    np.testing.assert_allclose(at_visits * total, counts.PLM2.cumsum(), atol=1e-9)
    np.testing.assert_allclose(np.diff(at_visits) * total, counts.PLM2.iloc[1:], atol=1e-9)
    # El dato del 27/03 fue acumulado entre dos visitas, no un único pico diario.
    first, last = counts.FECHA.iloc[5:7].dt.dayofyear
    assert curve.loc[first] < curve.loc[first + 1] < curve.loc[last]
    assert curve.loc[:35].isna().all()
    assert curve.loc[259:].eq(1).all()
    assert reference.loc[reference.Julian_days < 36, "N_Campanas_Dia"].eq(1).all()


def test_two_local_campaigns_receive_equal_weight_and_remain_monotone():
    reference = load_local_seasonal_reference(ROOT, as_of="2027-03-27")
    assert reference.N_Campanas.eq(2).all()
    assert reference.Campanas_Anos.eq("2025, 2026").all()
    assert reference.Campanas.eq(
        "test -emerel tresas 2025.xlsx, tres_arroyos_2026_counts.csv"
    ).all()
    valid = reference.Julian_days >= 36
    np.testing.assert_allclose(
        reference.loc[valid, "Progreso_Mediano_Empirico"],
        (reference.loc[valid, "Progreso_2025"] + reference.loc[valid, "Progreso_2026"]) / 2,
    )
    for column in ["Progreso_P10", "Progreso_Mediano", "Progreso_P90"]:
        assert reference[column].between(0, 1).all()
        assert (reference[column].diff().dropna() >= -1e-12).all()
    assert reference.Progreso_P10.le(reference.Progreso_Mediano).all()
    assert reference.Progreso_Mediano.le(reference.Progreso_P90).all()
    np.testing.assert_allclose(
        reference.Progreso_Mediano, reference.Progreso_Mediano_Empirico.cummax()
    )


@pytest.mark.parametrize("cutoff", ["2026-03-27", "2026-09-15"])
def test_no_2026_reference_before_the_last_count(cutoff):
    actual = load_local_seasonal_reference(ROOT, as_of=cutoff)
    legacy = load_seasonal_reference(ROOT / "models/modelo_clusters_k3.pkl", include_patterns=("tresas",))
    assert actual.N_Campanas.eq(1).all()
    assert "Progreso_2026" not in actual
    for column in ["Progreso_P10", "Progreso_Mediano", "Progreso_P90"]:
        pd.testing.assert_series_equal(actual[column], legacy[column])
    assert "2026_counts.csv" in actual.Campanas_Excluidas.iloc[0]
    assert load_local_seasonal_reference(ROOT, as_of="2026-09-16").N_Campanas.eq(2).all()


def test_partial_2027_run_uses_both_references_without_forcing_100_percent():
    weather = pd.read_csv(ROOT / "data/calibration/tres_arroyos_2026_weather.csv")
    # Meteorología sintética de prueba: desplazar un año, no un pronóstico 2027.
    weather["Fecha"] = pd.to_datetime(weather["Fecha"]) + pd.DateOffset(years=1)
    cutoff = pd.Timestamp("2027-03-27")
    weather = weather.loc[weather.Fecha <= cutoff + pd.Timedelta(days=7)]
    model = PracticalANNModel.from_directory(ROOT / "models")
    reference = load_local_seasonal_reference(ROOT, as_of=cutoff)
    actual = run_predweem(weather, model, ModelParameters(), normalization_as_of=cutoff, seasonal_reference=reference)
    legacy = run_predweem(
        weather, model, ModelParameters(), normalization_as_of=cutoff,
        seasonal_reference=load_seasonal_reference(ROOT / "models/modelo_clusters_k3.pkl", include_patterns=("tresas",)),
    )
    row = actual.loc[actual.Fecha.eq(cutoff)].iloc[0]
    expected = reference.loc[reference.Julian_days.eq(cutoff.dayofyear), "Progreso_Mediano"].iloc[0]
    assert row.EMERAC_NORMALIZADA == pytest.approx(expected)
    assert not np.isclose(row.EMERAC_NORMALIZADA, legacy.loc[legacy.Fecha.eq(cutoff), "EMERAC_NORMALIZADA"].iloc[0])
    assert actual.iloc[-1].EMERAC_NORMALIZADA < 1
    pd.testing.assert_series_equal(actual.EMERREL, legacy.EMERREL)
    pd.testing.assert_series_equal(actual.TT_DESDE_PICO, legacy.TT_DESDE_PICO)


@pytest.mark.parametrize("fault", ["negative", "nan", "duplicate", "first_count", "year", "order"])
def test_invalid_2026_reference_is_rejected(tmp_path, fault):
    (tmp_path / "models").mkdir()
    (tmp_path / COUNTS).parent.mkdir(parents=True)
    shutil.copy(ROOT / "models/modelo_clusters_k3.pkl", tmp_path / "models/modelo_clusters_k3.pkl")
    counts = pd.read_csv(ROOT / COUNTS)
    if fault == "negative":
        counts.loc[2, "PLM2"] = -1
    elif fault == "nan":
        counts.loc[2, "PLM2"] = np.nan
    elif fault == "duplicate":
        counts.loc[2, "FECHA"] = counts.loc[1, "FECHA"]
    elif fault == "first_count":
        counts.loc[0, "PLM2"] = 1
    elif fault == "year":
        counts["FECHA"] = counts["FECHA"].str.replace("2026", "2027")
    else:
        counts = counts.iloc[::-1]
    counts.to_csv(tmp_path / COUNTS, index=False)
    with pytest.raises(ValueError, match="Conteos 2026"):
        load_local_seasonal_reference(tmp_path, as_of="2027-03-27")
