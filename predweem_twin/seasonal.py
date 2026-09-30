"""Referencia estacional para normalizar ejecuciones meteorológicas parciales."""

from __future__ import annotations

from pathlib import Path
from hashlib import sha256
import pickle
import json

import numpy as np
import pandas as pd


EXCLUDED_SITES = ("balcarce", "san pedro")


def calendar_reference_days(dates):
    """Coordenada común por mes/día; conserva 29/02 entre 28/02 y 01/03."""
    dates = pd.DatetimeIndex(pd.to_datetime(dates))
    days = dates.dayofyear.to_numpy(dtype=float)
    days[dates.is_leap_year & (dates.month > 2)] -= 1
    days[(dates.month == 2) & (dates.day == 29)] = 59.5
    return days


def load_seasonal_reference(
    source: str | Path,
    excluded_years: tuple[str, ...] = ("2010", "2015"),
    include_patterns: tuple[str, ...] | None = None,
    excluded_sites: tuple[str, ...] = EXCLUDED_SITES,
) -> pd.DataFrame:
    """Construye percentiles de progreso y permite una referencia local.

    Balcarce y San Pedro se excluyen antes de calcular los percentiles.
    ``include_patterns`` filtra por nombre de campaña sin distinguir
    mayúsculas. En el gemelo Tres Arroyos se selecciona la campaña 2025
    identificada por «tresas». Una sola campaña no permite estimar de forma
    robusta la variabilidad entre años.
    """
    with Path(source).open("rb") as handle:
        payload = pickle.load(handle)

    julian_days = np.asarray(
        payload.get("JD_common", payload.get("JD_COMMON")), dtype=float
    )
    curves = np.asarray(
        payload.get("curves_interp", payload.get("curves")), dtype=float
    )
    names = [str(value) for value in payload.get("names", payload.get("files", []))]
    if curves.ndim != 2 or len(julian_days) != curves.shape[1]:
        raise ValueError("La referencia histórica no contiene curvas compatibles.")
    if len(names) != len(curves) or any(not name.strip() for name in names):
        raise ValueError("La referencia requiere un nombre por curva para filtrar años y localidades.")
    patterns = tuple(" ".join(str(value).casefold().split()) for value in (include_patterns or ()))
    sites = tuple(" ".join(str(value).casefold().split()) for value in excluded_sites)
    normalized_names = [" ".join(name.casefold().split()) for name in names]
    keep = np.array([
        not any(year in name for year in excluded_years)
        and not any(site in normalized for site in sites)
        and (not patterns or any(pattern in normalized for pattern in patterns))
        for name, normalized in zip(names, normalized_names)
    ], dtype=bool)
    excluded_names = [name for name, selected in zip(names, keep) if not selected]
    curves = curves[keep]
    names = [name for name, selected in zip(names, keep) if selected]
    if include_patterns and not len(curves):
        raise ValueError(
            "La referencia histórica no contiene campañas para: "
            + ", ".join(include_patterns)
        )
    curves = np.clip(curves, 0.0, None)
    totals = curves.sum(axis=1, keepdims=True)
    valid = totals[:, 0] > 1e-12
    if not valid.any():
        raise ValueError("La referencia histórica no contiene flujos positivos.")
    progress = np.cumsum(curves[valid], axis=1) / totals[valid]
    return pd.DataFrame(
        {
            "Julian_days": julian_days,
            "Progreso_P10": np.quantile(progress, 0.10, axis=0),
            "Progreso_Mediano": np.median(progress, axis=0),
            "Progreso_P90": np.quantile(progress, 0.90, axis=0),
            "N_Campanas": int(valid.sum()),
            "Campanas_Excluidas": ", ".join(excluded_names),
            "Campanas": ", ".join(
                name for name, selected in zip(names, valid) if selected
            ) if names else "",
        }
    )


def _local_counts(root, year):
    relative = (f"data/calibration/tres_arroyos_{year}_counts.csv" if year == 2026
                else f"data/reference/tres_arroyos_{year}_counts.csv")
    path = root / relative
    counts = pd.read_csv(path)
    if not {"FECHA", "PLM2"}.issubset(counts.columns) or len(counts) < 2:
        raise ValueError(f"La referencia {year} requiere FECHA y PLM2 y al menos dos visitas.")
    dates = pd.to_datetime(counts["FECHA"], errors="raise").dt.normalize()
    flows = pd.to_numeric(counts["PLM2"], errors="raise").to_numpy(float)
    if (dates.isna().any() or dates.duplicated().any()
            or not dates.is_monotonic_increasing or not dates.dt.year.eq(year).all()
            or not np.isfinite(flows).all() or (flows < 0).any()
            or flows.sum() <= 0 or (year == 2026 and flows[0] != 0)):
        raise ValueError(f"Conteos {year} inválidos" + (" o sin cero inicial delimitador." if year == 2026 else "."))
    metadata = {
        "path": relative, "sha256": sha256(path.read_bytes()).hexdigest(),
        "start": dates.iloc[0].date().isoformat(), "end": dates.iloc[-1].date().isoformat(),
        "sample_count": len(counts), "window_total_plm2": float(flows.sum()),
        "initial_zero_reference": bool(flows[0] == 0),
        "processing": "acumulado / total registrado; interpolación lineal entre visitas",
        "scope": "ventana registrada; no certifica el cierre biológico de la campaña",
    }
    if year in (2023, 2024):
        source_file = f"data/reference/tres_arroyos_{year}_source.json"
        source = json.loads((root / source_file).read_text())
        if (source.get("site") != "Tres Arroyos" or source.get("year") != year
                or source["counts"]["sha256"] != metadata["sha256"]):
            raise ValueError(f"La procedencia de Tres Arroyos {year} no coincide con los conteos.")
        metadata.update(replicate_count=source["counts"]["replicate_count"], first_interval_start=None,
                        source_file=source_file,
                        weather=source["weather"], incorporated_on=source["incorporated_on"])
    if year == 2023:
        replicas = counts[[f"REP{i}" for i in range(1, 6)]].to_numpy(float)
        if (not np.isfinite(replicas).all() or (replicas < 0).any()
                or not np.allclose(replicas.mean(axis=1), flows, rtol=0, atol=1e-9)):
            raise ValueError("Las réplicas 2023 no coinciden con el promedio PLM2.")
    return dates, flows, metadata


def load_local_seasonal_reference(root: str | Path, as_of=None) -> pd.DataFrame:
    """Pool exclusivo Tres Arroyos 2023–2026, con igual peso por año.

    Los conteos se normalizan por su propio total registrado, nunca por el
    número de réplicas ni por la densidad relativa a otras campañas. Los
    primeros conteos de 2023 y 2024 no tienen inicio de intervalo documentado:
    se conservan sin asignarlos a días anteriores ni a un pico diario.
    """
    root = Path(root)
    legacy = load_seasonal_reference(
        root / "models/modelo_clusters_k3.pkl",
        excluded_years=("2010", "2015"), include_patterns=("tresas",),
    )
    if (not legacy["N_Campanas"].eq(1).all()
            or not legacy["Campanas"].eq("test -emerel tresas 2025.xlsx").all()):
        raise ValueError("Se requiere una única referencia local de Tres Arroyos 2025.")
    # Validar también fuentes todavía no habilitadas; no aceptar datos dañados.
    records = {year: _local_counts(root, year) for year in (2026, 2023, 2024)}
    cutoff = pd.Timestamp(as_of).tz_localize(None).normalize() if as_of is not None else None
    if cutoff is not None and pd.isna(cutoff):
        raise ValueError("Fecha de corte de la referencia inválida.")
    used = {year: cutoff is None or cutoff >= dates.iloc[-1]
            for year, (dates, _, _) in records.items()}
    # 2025 es una curva procesada previa a la campaña operativa 2026.
    used[2025] = cutoff is None or cutoff >= pd.Timestamp("2026-01-01")
    if not any(used.values()):
        raise ValueError("No hay referencias locales disponibles para esta fecha.")
    axis_end = max([int(legacy.Julian_days.max())] + [
        int(calendar_reference_days(dates).max()) for year, (dates, _, _) in records.items() if used[year]
    ])
    axis = np.arange(1, axis_end + 1, dtype=float)
    if used[2024]:
        axis = np.sort(np.append(axis, 59.5))
    reference = pd.DataFrame({"Julian_days": axis})
    reference.attrs["calendar_basis"] = "month_day_nonleap_feb29_half"
    included, excluded = [], [legacy.Campanas_Excluidas.iloc[0]]
    if used[2025]:
        reference["Progreso_2025"] = np.interp(
            reference.Julian_days, legacy.Julian_days, legacy.Progreso_Mediano,
            left=np.nan, right=1.0,
        )
        included.append(legacy.Campanas.iloc[0])
    else:
        excluded.append(legacy.Campanas.iloc[0] + " (disponible desde 01/01/2026)")
    for year in (2023, 2024, 2026):
        dates, flows, metadata = records[year]
        metadata["used"] = used[year]
        reference.attrs[f"source_{year}"] = metadata
        reference[f"Referencia_{year}_Desde"] = metadata["end"]
        if used[year]:
            reference[f"Progreso_{year}"] = np.interp(
                reference.Julian_days, calendar_reference_days(dates), np.cumsum(flows) / flows.sum(),
                left=np.nan, right=1.0,
            )
            included.append(Path(metadata["path"]).name)
        else:
            excluded.append(f"{Path(metadata['path']).name} (disponible desde {dates.iloc[-1]:%d/%m/%Y})")
    years = sorted(year for year, selected in used.items() if selected)
    campaigns = reference[[f"Progreso_{year}" for year in years]]
    reference["N_Campanas_Dia"] = campaigns.notna().sum(axis=1)
    for q, column in [(0.10, "Progreso_P10"), (0.50, "Progreso_Mediano"), (0.90, "Progreso_P90")]:
        empirical = campaigns.quantile(q, axis=1)
        reference[column + "_Empirico"] = empirical
        # Conserva el criterio vigente de ancla no decreciente cuando cambia
        # la cantidad de campañas con referencia para ese día del calendario.
        reference[column] = empirical.cummax()
    changed = reference.N_Campanas_Dia.diff().fillna(reference.N_Campanas_Dia).gt(0)
    increment = reference.Progreso_Mediano.diff().fillna(reference.Progreso_Mediano)
    # Un salto al ingresar una curva incompleta al inicio es cambio de
    # composición, no evidencia de nacimientos ocurridos ese día.
    reference["Flujo_No_Comparable"] = changed & increment.gt(1e-12)
    reference["N_Campanas"] = len(years)
    reference["Campanas_Anos"] = ", ".join(map(str, years))
    reference["Campanas"] = ", ".join(included)
    reference["Campanas_Excluidas"] = ", ".join(excluded)
    return reference


def reference_progress(
    reference: pd.DataFrame, julian_days, *, dates=None
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpola cuantiles; en el pool local alinea por mes/día si hay fechas."""
    days = (calendar_reference_days(dates)
            if dates is not None and reference.attrs.get("calendar_basis") == "month_day_nonleap_feb29_half"
            else np.asarray(julian_days, dtype=float))
    axis = reference["Julian_days"].to_numpy(float)
    values = []
    for column in ("Progreso_P10", "Progreso_Mediano", "Progreso_P90"):
        values.append(
            np.interp(
                days,
                axis,
                reference[column].to_numpy(float),
                left=0.0,
                right=1.0,
            )
        )
    return tuple(values)


def partial_season_normalization(
    trajectory: pd.DataFrame,
    as_of,
    reference: pd.DataFrame,
) -> tuple[float | None, dict]:
    """Estima el total de señal estacional sin usar el fin del pronóstico.

    La señal acumulada de PREDWEEM se ancla, en la fecha del estado, al progreso
    mediano de campañas históricas. Si aún no existe señal positiva, utiliza el
    último día disponible como ancla provisional.
    """
    cutoff = pd.Timestamp(as_of).tz_localize(None).normalize()
    candidates = trajectory.index[trajectory["Fecha"] <= cutoff].tolist()
    anchor_idx = candidates[-1] if candidates else 0
    p10, median, p90 = reference_progress(
        reference, trajectory["Julian_days"].to_numpy(float), dates=trajectory["Fecha"]
    )
    raw_cumulative = trajectory["EMERAC"].to_numpy(float)

    if raw_cumulative[anchor_idx] <= 1e-12 or median[anchor_idx] <= 0.01:
        valid = np.flatnonzero((raw_cumulative > 1e-12) & (median > 0.01))
        if not len(valid):
            return None, {
                "mode": "sin señal suficiente",
                "anchor_date": trajectory.at[anchor_idx, "Fecha"],
                "reference_progress": float(median[anchor_idx]),
            }
        anchor_idx = int(valid[0])

    seasonal_total = float(raw_cumulative[anchor_idx] / median[anchor_idx])
    if not np.isfinite(seasonal_total) or seasonal_total <= 1e-12:
        return None, {"mode": "sin señal suficiente"}
    return seasonal_total, {
        "mode": "referencia estacional histórica",
        "anchor_date": trajectory.at[anchor_idx, "Fecha"],
        "reference_progress": float(median[anchor_idx]),
        "reference_p10": float(p10[anchor_idx]),
        "reference_p90": float(p90[anchor_idx]),
        "seasonal_signal_total": seasonal_total,
    }
