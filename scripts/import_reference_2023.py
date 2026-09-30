"""Extrae los adjuntos Tres Arroyos 2023 sin alterar los Excel originales."""

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def build_reference_files(root=ROOT):
    folder = Path(root) / "data/reference"
    counts_original = folder / "tres_arroyos_2023_counts_original.xlsx"
    weather_original = folder / "tres_arroyos_2023_weather_original.xls"
    raw = pd.read_excel(counts_original, sheet_name="Emergencias", header=1)
    counts = raw.rename(columns={
        "fecha": "FECHA", "promedio plantas.m-2": "PLM2",
        **{f"rep{i}": f"REP{i}" for i in range(1, 6)},
    }).copy()
    counts["FECHA"] = pd.to_datetime(counts["FECHA"], errors="raise").dt.normalize()
    replicas = [f"REP{i}" for i in range(1, 6)]
    for column in [*replicas, "PLM2"]:
        counts[column] = pd.to_numeric(counts[column], errors="raise")
    values = counts[[*replicas, "PLM2"]].to_numpy(float)
    if (not counts.FECHA.dt.year.eq(2023).all() or counts.FECHA.duplicated().any()
            or not counts.FECHA.is_monotonic_increasing or not np.isfinite(values).all()
            or (values < 0).any() or counts.PLM2.sum() <= 0):
        raise ValueError("Conteos originales 2023 inválidos.")
    if not np.allclose(counts[replicas].mean(axis=1), counts.PLM2, rtol=0, atol=1e-9):
        raise ValueError("El promedio informado no coincide con las cinco réplicas.")
    counts["N_REPLICAS"] = 5
    counts["SD_PLM2"] = counts[replicas].std(axis=1, ddof=1)
    counts["EE_PLM2"] = counts.SD_PLM2 / np.sqrt(5)
    counts_path = folder / "tres_arroyos_2023_counts.csv"
    counts.to_csv(counts_path, index=False, date_format="%Y-%m-%d")

    weather = pd.read_excel(weather_original, sheet_name="Datos diarios").rename(
        columns={"tmax": "TMAX", "tmin": "TMIN", "prec": "Prec"}
    )
    weather["Fecha"] = pd.to_datetime(weather["Fecha"], errors="raise").dt.normalize()
    for column in ["TMAX", "TMIN", "Prec"]:
        weather[column] = pd.to_numeric(weather[column], errors="raise")
    if (not weather.Fecha.dt.year.eq(2023).all() or weather.Fecha.duplicated().any()
            or not weather.Fecha.is_monotonic_increasing
            or not weather.Fecha.equals(pd.Series(pd.date_range(weather.Fecha.min(), weather.Fecha.max()), name="Fecha"))
            or np.isinf(weather[["TMAX", "TMIN", "Prec"]].to_numpy(float)).any()
            or weather.Prec.isna().any() or weather.Prec.lt(0).any()
            or weather.TMAX.lt(weather.TMIN).any()):
        raise ValueError("Meteorología original 2023 inválida.")
    missing = weather.loc[weather[["TMAX", "TMIN"]].isna().any(axis=1), "Fecha"]
    weather["Fuente"] = "Adjunto del usuario; Tres Arroyos 2023"
    weather["TipoDato"] = "Historico_adjunto"
    weather["CalidadDato"] = np.where(
        weather[["TMAX", "TMIN"]].isna().any(axis=1),
        "Temperaturas_faltantes", "Sin_faltantes_en_variables_requeridas",
    )
    weather_path = folder / "tres_arroyos_2023_weather.csv"
    weather.to_csv(weather_path, index=False, date_format="%Y-%m-%d", na_rep="")
    source = {
        "site": "Tres Arroyos", "year": 2023, "role": "referencia histórica observada",
        "incorporated_on": "2026-09-30",
        "available_from": counts.FECHA.max().date().isoformat(),
        "availability_note": "Disponibilidad del total por cierre del archivo; incorporado al sistema en 2026. Las revisiones pasadas son retrospectivas.",
        "counts": {
            "uploaded_name": "Datos emergencia Lolium 2023- RAMON Tres Arroyos.xlsx",
            "original_file": counts_original.name, "original_sha256": sha256(counts_original.read_bytes()).hexdigest(),
            "file": counts_path.name, "sha256": sha256(counts_path.read_bytes()).hexdigest(),
            "sheet": "Emergencias", "header_row": 2, "replicate_count": 5,
            "units": "plantas/m²", "mean_verified_against_replicates": True,
            "replicate_scale_factor": 1.0,
            "standard_error": "desvío estándar muestral entre cinco réplicas / raíz de 5; no pondera el pool",
            "sample_count": len(counts), "start": counts.FECHA.min().date().isoformat(),
            "end": counts.FECHA.max().date().isoformat(), "window_total_plm2": float(counts.PLM2.sum()),
            "initial_zero_reference": False, "first_count_plm2": float(counts.PLM2.iloc[0]),
            "first_interval_start": None,
            "processing": "acumulado PLM2 / suma PLM2 de las 29 visitas; interpolación lineal entre visitas; sin cero inicial inventado",
            "scope": "ventana registrada; no certifica cierre biológico ni ausencia previa al primer conteo",
        },
        "weather": {
            "uploaded_name": "meteo 2023 tres arroyos.xls",
            "original_file": weather_original.name, "original_sha256": sha256(weather_original.read_bytes()).hexdigest(),
            "file": weather_path.name, "sha256": sha256(weather_path.read_bytes()).hexdigest(),
            "sheet": "Datos diarios", "rows": len(weather),
            "start": weather.Fecha.min().date().isoformat(), "end": weather.Fecha.max().date().isoformat(),
            "temperature_units": "°C", "precipitation_units": "mm",
            "station": None, "station_note": "El adjunto no identifica estación ni coordenadas.",
            "missing_temperature_dates": missing.dt.strftime("%Y-%m-%d").tolist(),
            "imputation": "ninguna; faltantes conservados, no sustituidos por cero",
            "role": "archivo histórico asociado; no reemplaza meteorología operativa ni calcula la curva observada",
        },
    }
    (folder / "tres_arroyos_2023_source.json").write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return source


if __name__ == "__main__":
    result = build_reference_files()
    print(json.dumps({"counts": result["counts"]["sample_count"],
                      "total_plm2": result["counts"]["window_total_plm2"],
                      "weather_rows": result["weather"]["rows"],
                      "missing_temperature_dates": result["weather"]["missing_temperature_dates"]}))
