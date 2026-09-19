"""Funciones científicas extraídas de loliumTA_2026, commit 5b52fef47ed2c97aefe45b8939e751141db5216e.
Incluye el parche operativo de decaimiento desde 15/04, sin interfaz.
Referencia independiente para pruebas de equivalencia.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

UMBRAL_PRIMER_PICO = 0.20

def calcular_et0_hargreaves(jday, tmax, tmin, latitud=-38.45):
    lat_rad = np.radians(latitud)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * jday)
    dec = 0.409 * np.sin(2 * np.pi / 365 * jday - 1.39)
    ws = np.arccos(-np.tan(lat_rad) * np.tan(dec))
    ra = (24 * 60 / np.pi) * 0.0820 * dr * (ws * np.sin(lat_rad) * np.sin(dec) + np.cos(lat_rad) * np.cos(dec) * np.sin(ws))
    ra_mm = ra / 2.45
    tmean = (tmax + tmin) / 2.0
    trange = np.maximum(tmax - tmin, 0)
    return np.maximum(0.0023 * ra_mm * (tmean + 17.8) * np.sqrt(trange), 0)

def balance_hidrico_superficial(
    prec,
    et0,
    w_max=15.0,
    ke_suelo=0.4,
    exponente_kr=0.0,
    devolver_kr=False,
):
    prec = np.asarray(prec, dtype=float)
    et0 = np.asarray(et0, dtype=float)
    n = len(prec)
    w = np.zeros(n, dtype=float)
    kr_diario = np.ones(n, dtype=float)

    if n == 0:
        return (w, kr_diario) if devolver_kr else w
    if w_max <= 0:
        raise ValueError("Wmax debe ser mayor que cero.")

    exponente = max(float(exponente_kr), 0.0)
    w[0] = float(w_max) / 2.0
    for i in range(1, n):
        fraccion_agua = float(np.clip(w[i - 1] / float(w_max), 0.0, 1.0))
        kr = 1.0 if exponente == 0.0 else fraccion_agua ** exponente
        kr_diario[i] = kr
        evaporacion_real = et0[i] * float(ke_suelo) * kr
        w[i] = np.clip(
            w[i - 1] + prec[i] - evaporacion_real,
            0.0,
            float(w_max),
        )

    return (w, kr_diario) if devolver_kr else w

def aplicar_filtro_primer_pico(df, umbral=UMBRAL_PRIMER_PICO):
    """
    Habilita la campaña desde el primer valor de EMERREL
    estrictamente superior al umbral. Los pulsos anteriores
    se guardan para auditoría y se cancelan en EMERREL.
    """
    df = df.copy()
    df["EMERREL_ANTES_FILTRO_PRIMER_PICO"] = df["EMERREL"].copy()

    candidatos = df.index[df["EMERREL"] > umbral].tolist()

    if candidatos:
        idx_primer_pico = candidatos[0]
        df["Primer_Pico_Habilitado"] = df.index >= idx_primer_pico
        df.loc[df.index < idx_primer_pico, "EMERREL"] = 0.0
    else:
        idx_primer_pico = None
        df["Primer_Pico_Habilitado"] = False
        df["EMERREL"] = 0.0

    return df, idx_primer_pico

class PracticalANNModel:
    def __init__(self, IW, bIW, LW, bLW):
        self.IW, self.bIW, self.LW, self.bLW = IW, bIW, LW, bLW
        self.input_min = np.array([1, 0, -7, 0])
        self.input_max = np.array([300, 41, 25.5, 84])
    def normalize(self, X): return 2 * (X - self.input_min) / (self.input_max - self.input_min) - 1
    def predict(self, Xreal):
        Xn = self.normalize(Xreal)
        a1 = np.tanh(Xn @ self.IW + self.bIW)
        emerrel = (np.tanh((a1 @ self.LW.T).flatten() + self.bLW) + 1) / 2
        return emerrel, np.cumsum(emerrel)

def parametros_superficie(cobertura_pct):
    """Deriva Ke y el modulador térmico únicamente desde cobertura física."""
    cobertura = float(np.clip(cobertura_pct, 0.0, 100.0))
    puntos_cobertura = [0.0, 30.0, 70.0, 100.0]
    ke_suelo = float(
        np.interp(cobertura, puntos_cobertura, [0.85, 0.50, 0.25, 0.10])
    )
    modulador_termico = float(
        np.interp(cobertura, puntos_cobertura, [0.95, 0.90, 0.85, 0.80])
    )
    return ke_suelo, modulador_termico

def simular_emergencia_ta(
    df_meteo,
    modelo_ann,
    cobertura_pct,
    w_max,
    umbral_termoinhibicion=24.0,
    umbral_choque_hidrico=45.0,
    exponente_kr=0.0,
    latitud=-38.4500,
):
    """Motor único usado por la aplicación y por el optimizador 2D."""
    df = df_meteo.copy()
    df.columns = [str(c).upper().strip() for c in df.columns]
    df = df.rename(
        columns={
            "FECHA": "Fecha",
            "DATE": "Fecha",
            "DATETIME": "Fecha",
            "PREC": "Prec",
            "PRECIPITACION": "Prec",
            "PRECIPITACIÓN": "Prec",
            "LLUVIA": "Prec",
        }
    )
    requeridas = ["Fecha", "TMAX", "TMIN", "Prec"]
    faltantes = [c for c in requeridas if c not in df.columns]
    if faltantes:
        raise ValueError(
            "Faltan columnas meteorológicas: " + ", ".join(faltantes)
        )

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    for columna in ("TMAX", "TMIN", "Prec"):
        df[columna] = pd.to_numeric(df[columna], errors="coerce")
    df = (
        df.dropna(subset=requeridas)
        .sort_values("Fecha")
        .drop_duplicates("Fecha", keep="last")
        .reset_index(drop=True)
    )
    if df.empty:
        raise ValueError("No hay datos meteorológicos válidos.")
    df["Prec"] = df["Prec"].clip(lower=0.0)
    df["Julian_days"] = df["Fecha"].dt.dayofyear

    ke_suelo, modulador_termico = parametros_superficie(cobertura_pct)
    df["Cobertura_Rastrojo"] = float(cobertura_pct)
    df["Ke_Suelo"] = ke_suelo
    df["Exponente_Kr"] = float(exponente_kr)

    df["Tmedia_aire"] = (df["TMAX"] + df["TMIN"]) / 2.0
    amplitud_termica = (df["TMAX"] - df["TMIN"]) / 2.0
    df["TMAX_suelo"] = (
        df["Tmedia_aire"] + amplitud_termica * modulador_termico
    )
    df["TMIN_suelo"] = (
        df["Tmedia_aire"] - amplitud_termica * modulador_termico
    )
    df["Tmedia"] = df["Tmedia_aire"]

    entradas_ann = df[
        ["Julian_days", "TMAX", "TMIN", "Prec"]
    ].to_numpy(float)
    emerrel_raw, _ = modelo_ann.predict(entradas_ann)
    df["EMERREL_RAW_ANN"] = np.clip(emerrel_raw, 0.0, 1.0)
    df["EMERREL"] = df["EMERREL_RAW_ANN"].copy()

    df["Prec_3d"] = df["Prec"].rolling(window=3, min_periods=1).sum()
    choque_hidrico = (
        (df["Julian_days"] > 25)
        & (df["Julian_days"] <= 110)
        & (df["Prec_3d"] >= float(umbral_choque_hidrico))
    )
    df.loc[choque_hidrico, "EMERREL"] = np.maximum(
        df.loc[choque_hidrico, "EMERREL"],
        0.75,
    )
    df["Choque_Hidrico"] = choque_hidrico

    df["ET0"] = calcular_et0_hargreaves(
        df["Julian_days"].values,
        df["TMAX"].values,
        df["TMIN"].values,
        latitud=latitud,
    )
    agua, kr_diario = balance_hidrico_superficial(
        df["Prec"].values,
        df["ET0"].values,
        w_max=float(w_max),
        ke_suelo=ke_suelo,
        exponente_kr=float(exponente_kr),
        devolver_kr=True,
    )
    df["W_superficial"] = agua
    df["Kr_Diario"] = kr_diario
    humedad_relativa = df["W_superficial"] / max(float(w_max), 1e-12)
    df["Humedad_Relativa"] = humedad_relativa
    df["Hydric_Factor"] = 1.0 / (
        1.0 + np.exp(-10.0 * (humedad_relativa - 0.30))
    )
    df["EMERREL"] *= df["Hydric_Factor"]
    df.loc[humedad_relativa < 0.20, "EMERREL"] = 0.0

    df["Lluvia_Recarga"] = (df["Prec"] >= float(w_max)).cummax()
    df.loc[~df["Lluvia_Recarga"], "EMERREL"] = 0.0

    df["Tmedia_5d"] = df["Tmedia_aire"].rolling(
        window=5,
        min_periods=1,
    ).mean()
    df["Termoinhibida"] = (
        df["Tmedia_5d"] >= float(umbral_termoinhibicion)
    )
    df.loc[df["Termoinhibida"], "EMERREL"] = 0.0
    df.loc[df["Julian_days"] <= 25, "EMERREL"] = 0.0

    df["EMERREL"] = np.clip(df["EMERREL"], 0.0, 1.0)
    df, idx_primer_pico = aplicar_filtro_primer_pico(
        df,
        umbral=UMBRAL_PRIMER_PICO,
    )

    # Decaimiento tardío Tres Arroyos: hasta 14-abr EMERREL queda intacto.
    df["EMERREL_ANTES_DECAIMIENTO_15ABR"] = df["EMERREL"].copy()
    df["Dias_Desde_15Abr"] = 0.0
    df["Factor_Decaimiento_15Abr"] = 1.0
    df["Techo_EMERREL_15Abr"] = np.nan

    tau_d = 60.0
    beta_d = 1.0
    intensidad_d = 0.75
    fraccion_max_d = 0.50

    inicio_decaimiento = pd.to_datetime({
        "year": df["Fecha"].dt.year,
        "month": np.full(len(df), 4),
        "day": np.full(len(df), 15),
    })
    mascara_decay = df["Fecha"] >= inicio_decaimiento
    dias_decay = (df["Fecha"] - inicio_decaimiento).dt.days.clip(lower=0).astype(float)

    max_pre_por_anio = {}
    for anio in sorted(df["Fecha"].dt.year.dropna().unique()):
        fecha_inicio_anio = pd.Timestamp(year=int(anio), month=4, day=15)
        mascara_pre = (df["Fecha"].dt.year == anio) & (df["Fecha"] < fecha_inicio_anio)
        max_pre = (
            float(df.loc[mascara_pre, "EMERREL"].clip(lower=0.0).max())
            if mascara_pre.any()
            else 0.0
        )
        max_pre_por_anio[int(anio)] = max_pre

    factor_decay = np.ones(len(df), dtype=float)
    factor_decay[mascara_decay.to_numpy()] = (
        (1.0 - intensidad_d)
        + intensidad_d * np.exp(
            -((dias_decay[mascara_decay].to_numpy() / tau_d) ** beta_d)
        )
    )

    techo_decay = np.full(len(df), np.nan, dtype=float)
    for pos, (_, fila) in enumerate(df.iterrows()):
        if bool(mascara_decay.iloc[pos]):
            max_pre = max_pre_por_anio.get(int(fila["Fecha"].year), 0.0)
            if max_pre > 0.0:
                techo_decay[pos] = fraccion_max_d * max_pre * factor_decay[pos]

    df["Dias_Desde_15Abr"] = dias_decay
    df["Factor_Decaimiento_15Abr"] = np.clip(factor_decay, 0.0, 1.0)
    df["Techo_EMERREL_15Abr"] = techo_decay

    mascara_con_techo = mascara_decay & df["Techo_EMERREL_15Abr"].notna()
    if mascara_con_techo.any():
        valores_originales = df.loc[mascara_con_techo, "EMERREL"].clip(lower=0.0).to_numpy()
        techos_activos = df.loc[mascara_con_techo, "Techo_EMERREL_15Abr"].to_numpy()
        df.loc[mascara_con_techo, "EMERREL"] = np.minimum(
            valores_originales,
            techos_activos,
        )

    df["Tau_Decaimiento_15Abr_d"] = tau_d
    df["Beta_Decaimiento_15Abr"] = beta_d
    df["Intensidad_Decaimiento_15Abr"] = intensidad_d
    df["Fraccion_Maxima_15Abr"] = fraccion_max_d

    df["EMERAC"] = df["EMERREL"].cumsum()
    total_emergencia = float(df["EMERREL"].sum())
    df["EMERAC_NORMALIZADA"] = (
        df["EMERAC"] / total_emergencia
        if total_emergencia > 0.0
        else 0.0
    )
    return df, idx_primer_pico, ke_suelo, modulador_termico
