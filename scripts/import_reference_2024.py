"""Extrae promedios y meteorología de Tres Arroyos 2024; conserva originales."""

from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def build_reference_files(root=ROOT):
    folder = Path(root) / "data/reference"
    counts_original = folder / "tres_arroyos_2024_counts_original.xlsx"
    weather_original = folder / "tres_arroyos_2024_weather_original.csv"
    counts = pd.read_excel(counts_original, sheet_name="Hoja1").rename(columns={"pl.m2": "PLM2"})
    counts = counts[["FECHA", "PLM2"]].copy()
    counts["FECHA"] = pd.to_datetime(counts.FECHA, errors="raise").dt.normalize()
    counts["PLM2"] = pd.to_numeric(counts.PLM2, errors="raise")
    if (counts.FECHA.isna().any() or not counts.FECHA.dt.year.eq(2024).all()
            or counts.FECHA.duplicated().any() or not counts.FECHA.is_monotonic_increasing
            or not np.isfinite(counts.PLM2).all() or counts.PLM2.lt(0).any()
            or counts.PLM2.sum() <= 0):
        raise ValueError("Conteos originales 2024 inválidos.")
    counts_path = folder / "tres_arroyos_2024_counts.csv"
    counts.to_csv(counts_path, index=False, date_format="%Y-%m-%d")

    raw = pd.read_csv(weather_original, sep=";", decimal=",")
    undated = raw.fecha.isna()
    if raw.loc[undated, ["TMAX", "TMIN"]].notna().any().any():
        raise ValueError("Hay temperaturas sin fecha; revisar el archivo original.")
    weather = raw.loc[~undated].rename(columns={"fecha": "Fecha", "prec": "Prec"}).copy()
    weather["Fecha"] = pd.to_datetime(weather.Fecha, format="%d/%m/%Y", errors="raise")
    for column in ("TMAX", "TMIN", "Prec"):
        weather[column] = pd.to_numeric(weather[column], errors="raise")
    if (not weather.Fecha.dt.year.eq(2024).all() or weather.Fecha.duplicated().any()
            or not weather.Fecha.is_monotonic_increasing
            or not pd.DatetimeIndex(weather.Fecha).equals(pd.date_range(weather.Fecha.min(), weather.Fecha.max()))
            or not np.isfinite(weather[["TMAX", "TMIN", "Prec"]]).all().all()
            or weather.Prec.lt(0).any() or weather.TMAX.lt(weather.TMIN).any()):
        raise ValueError("Meteorología fechada 2024 inválida.")
    weather["Fuente"] = "Adjunto del usuario; Tres Arroyos 2024"
    weather["TipoDato"] = "Historico_adjunto"
    weather["CalidadDato"] = "Sin_faltantes_en_variables_requeridas"
    weather_path = folder / "tres_arroyos_2024_weather.csv"
    weather.to_csv(weather_path, index=False, date_format="%Y-%m-%d")
    source = {
        "site": "Tres Arroyos", "year": 2024, "role": "referencia histórica observada",
        "incorporated_on": "2026-09-30",
        "available_from": counts.FECHA.max().date().isoformat(),
        "availability_note": "Disponibilidad del total por cierre del archivo; incorporado al sistema en 2026. Las revisiones pasadas son retrospectivas.",
        "calendar_alignment": "mes/día en eje no bisiesto; 29/02 en coordenada 59.5, sin desplazar marzo-diciembre",
        "counts": {
            "uploaded_name": "emergencia 2024.xlsx", "sheet": "Hoja1", "header_row": 1,
            "source_range": "A2:B11", "original_file": counts_original.name,
            "original_sha256": sha256(counts_original.read_bytes()).hexdigest(),
            "file": counts_path.name, "sha256": sha256(counts_path.read_bytes()).hexdigest(),
            "units": "plantas/m²", "measurement": "promedio de nuevos nacimientos por visita/intervalo",
            "replicate_count": None, "replicates_note": "Sólo se aportaron promedios; no se infiere cantidad de réplicas ni SD/EE.",
            "sample_count": len(counts), "start": counts.FECHA.min().date().isoformat(),
            "end": counts.FECHA.max().date().isoformat(), "window_total_plm2": float(counts.PLM2.sum()),
            "initial_zero_reference": bool(counts.PLM2.iloc[0] == 0),
            "first_count_plm2": float(counts.PLM2.iloc[0]), "first_interval_start": None,
            "processing": "acumulado PLM2 / suma PLM2 de las diez visitas; interpolación lineal entre visitas en calendario común; sin cero inicial inventado",
            "scope": "ventana registrada; no certifica cierre biológico ni ausencia previa al primer conteo",
        },
        "weather": {
            "uploaded_name": "meteo TRES ARROYOS 2024.csv",
            "original_file": weather_original.name, "original_sha256": sha256(weather_original.read_bytes()).hexdigest(),
            "file": weather_path.name, "sha256": sha256(weather_path.read_bytes()).hexdigest(),
            "delimiter": ";", "decimal_separator": ",", "source_rows": len(raw),
            "rows": len(weather), "start": weather.Fecha.min().date().isoformat(),
            "end": weather.Fecha.max().date().isoformat(),
            "excluded_undated_rows": int(undated.sum()),
            "excluded_empty_rows": int(raw.isna().all(axis=1).sum()),
            "excluded_precipitation_only_rows": int((undated & raw.prec.notna()).sum()),
            "exclusion_note": "Filas sin fecha no se asignan a días ni se suman; permanecen íntegramente en el CSV original.",
            "temperature_units": "°C", "precipitation_units": "mm", "station": None,
            "station_note": "El adjunto no identifica estación ni coordenadas.",
            "missing_temperature_dates": [], "imputation": "ninguna; registros fechados completos",
            "role": "archivo histórico asociado; no reemplaza meteorología operativa ni calcula la curva observada",
        },
    }
    (folder / "tres_arroyos_2024_source.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return source


if __name__ == "__main__":
    result = build_reference_files()
    print(json.dumps({"counts": result["counts"]["sample_count"], "total_plm2": result["counts"]["window_total_plm2"],
                      "weather_rows": result["weather"]["rows"], "excluded_undated_rows": result["weather"]["excluded_undated_rows"]}))
