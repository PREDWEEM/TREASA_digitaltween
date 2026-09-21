"""Gráfico operativo con referencia histórica anual orientativa."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .state import thermal_window_dates


def annual_historical_reference(reference, as_of):
    """Traslada el pool al calendario consultado sin inventar una cola anual.

    Las referencias locales proceden de 2025 y 2026 (años no bisiestos).
    En un año bisiesto se conserva mes/día y se interpola el 29 de febrero.
    Fuera del eje histórico se deja NaN, no un supuesto de emergencia nula.
    El flujo diario es derivado del acumulado, no un conteo diario observado.
    """
    year = pd.Timestamp(as_of).year
    dates = pd.date_range(f"{year}-01-01", f"{year}-12-31")
    frame = pd.DataFrame({"Fecha": dates})
    days = dates.dayofyear.to_numpy(dtype=float)
    days[(dates.is_leap_year) & (dates.month > 2)] -= 1
    days[(dates.month == 2) & (dates.day == 29)] = 59.5
    axis = reference["Julian_days"].to_numpy(float)
    columns = ["Progreso_Mediano"] + [
        column for column in ("Progreso_2025", "Progreso_2026")
        if column in reference
    ]
    for column in columns:
        frame[column] = np.interp(
            days, axis, reference[column].to_numpy(float),
            left=np.nan, right=np.nan,
        )
    # El resumen operativo conserva su supuesto de normalización hasta el
    # final del eje; la curva individual 2026 muestra sólo su ventana real.
    source_2026 = reference.attrs.get("source_2026", {})
    if "Progreso_2026" in frame and source_2026.get("end"):
        end_day = pd.Timestamp(source_2026["end"]).dayofyear
        frame.loc[days > end_day, "Progreso_2026"] = np.nan
    frame["Flujo_Diario"] = frame["Progreso_Mediano"].diff().clip(lower=0)
    if axis[0] == 1:
        frame.loc[0, "Flujo_Diario"] = frame.loc[0, "Progreso_Mediano"]
    frame.attrs["campaigns"] = reference["Campanas_Anos"].iloc[0]
    return frame


def trajectory_chart(
    df,
    observations,
    as_of,
    audit=None,
    lower_thermal_time=600.0,
    upper_thermal_time=800.0,
    seasonal_reference=None,
):
    cutoff = pd.Timestamp(as_of).normalize()
    year_start = pd.Timestamp(cutoff.year, 1, 1)
    display_end = pd.Timestamp(cutoff.year, 10, 1)
    # La referencia anual sólo se dibuja: no extiende la meteorología ni
    # modifica el estado, las métricas, los hitos o los datos exportados.
    df = df.loc[
        (pd.to_datetime(df["Fecha"]) >= year_start)
        & (pd.to_datetime(df["Fecha"]) <= min(cutoff + pd.Timedelta(days=7), display_end))
    ].copy()
    if observations is not None and not observations.empty:
        observation_dates = pd.to_datetime(observations["Fecha"])
        observations = observations.loc[
            observation_dates.between(year_start, cutoff)
        ].copy()
    if audit is not None and not audit.empty and "Fecha_asimilada" in audit:
        audit_dates = pd.to_datetime(audit["Fecha_asimilada"])
        audit = audit.loc[audit_dates.between(year_start, cutoff)].copy()
    figure = make_subplots(specs=[[{"secondary_y": True}]])
    historical = None
    if seasonal_reference is not None:
        historical = annual_historical_reference(seasonal_reference, cutoff)
        historical = historical.loc[historical["Fecha"] <= display_end]
        figure.add_trace(
            go.Bar(
                x=historical["Fecha"], y=historical["Flujo_Diario"] * 100,
                name="Flujo histórico · orientativo",
                marker_color="rgba(144,158,167,.24)",
                hovertemplate=("%{x|%d/%m/%Y}<br>Flujo histórico orientativo: "
                               "%{y:.2f}%<br>Derivado de curvas históricas<extra></extra>"),
            ), secondary_y=False,
        )
        for year, color in [(2025, "rgba(150,154,168,.48)"), (2026, "rgba(167,176,151,.48)")]:
            column = f"Progreso_{year}"
            if column in historical:
                figure.add_trace(
                    go.Scatter(
                        x=historical["Fecha"], y=historical[column] * 100,
                        name=f"Histórico {year} · orientativo",
                        mode="lines", line=dict(color=color, width=1.4),
                        connectgaps=False,
                        hovertemplate=(f"%{{x|%d/%m/%Y}}<br>Referencia {year}: "
                                       "%{y:.1f}%<extra>Solo orientativa</extra>"),
                    ), secondary_y=True,
                )
        figure.add_trace(
            go.Scatter(
                x=historical["Fecha"], y=historical["Progreso_Mediano"] * 100,
                name="Pool histórico · orientativo", mode="lines",
                line=dict(color="rgba(131,161,142,.65)", width=2.2, dash="dash"),
                connectgaps=False,
                hovertemplate=("%{x|%d/%m/%Y}<br>Acumulado histórico orientativo: "
                               "%{y:.1f}%<extra>No es pronóstico</extra>"),
            ), secondary_y=True,
        )
    figure.add_trace(
        go.Bar(
            x=df["Fecha"],
            y=df["EMERREL_TWIN"] * 100,
            name="Flujo diario del gemelo",
            marker_color="#3b82f6",
            opacity=0.62,
        ),
        secondary_y=False,
    )
    figure.add_trace(
        go.Scatter(
            x=df["Fecha"],
            y=df.get("EMERAC_BASE_SIN_CALIBRAR", df["EMERAC_NORMALIZADA"]) * 100,
            name="Acumulado PREDWEEM base",
            line=dict(color="#83938b", width=2, dash="dot"),
        ),
        secondary_y=True,
    )
    if "Calibracion_Aplicada" in df and df["Calibracion_Aplicada"].any():
        figure.add_trace(
            go.Scatter(
                x=df["Fecha"], y=df["EMERAC_CALIBRADA"] * 100,
                name="Calibración Tres Arroyos", line=dict(color="#9260bd", width=2),
            ),
            secondary_y=True,
        )
    figure.add_trace(
        go.Scatter(
            x=df.loc[df["Fecha"] <= cutoff, "Fecha"],
            y=df.loc[df["Fecha"] <= cutoff, "EMERAC_TWIN"] * 100,
            name="Estado actualizado",
            line=dict(color="#155d3e", width=4),
            fill="tozeroy",
            fillcolor="rgba(66,137,87,.10)",
        ),
        secondary_y=True,
    )
    if (df["Fecha"] > cutoff).any():
        projection = df.loc[df["Fecha"] >= cutoff]
        figure.add_trace(
            go.Scatter(
                x=projection["Fecha"], y=projection["EMERAC_TWIN"] * 100,
                name="Proyección meteorológica · hasta 7 días",
                mode="lines", line=dict(color="#155d3e", width=3, dash="dash"),
                hovertemplate="%{x|%d/%m/%Y}<br>Proyección: %{y:.1f}%<extra></extra>",
            ), secondary_y=True,
        )
    if audit is not None and not audit.empty and "Estado_campo_estimado" in audit:
        figure.add_trace(
            go.Scatter(
                x=audit["Fecha_asimilada"],
                y=audit["Estado_campo_estimado"] * 100,
                name="Estado estimado desde campo",
                mode="markers",
                marker=dict(color="#df5b3f", size=11, line=dict(color="white", width=2)),
            ),
            secondary_y=True,
        )
    elif observations is not None and not observations.empty:
        figure.add_trace(
            go.Scatter(
                x=observations["Fecha"],
                y=observations["Observado"] * 100,
                name="Conteo de campo",
                mode="markers",
                marker=dict(color="#df5b3f", size=11, line=dict(color="white", width=2)),
            ),
            secondary_y=True,
        )
    thermal_start, thermal_end = thermal_window_dates(
        df, lower_thermal_time, upper_thermal_time
    )
    if thermal_start is not None:
        displayed_thermal_end = thermal_end or pd.Timestamp(df["Fecha"].max())
        figure.add_vrect(
            x0=thermal_start,
            x1=displayed_thermal_end,
            fillcolor="rgba(255,193,7,.22)",
            line_width=0,
            annotation_text=(
                f"Ventana fenológica {lower_thermal_time:.0f}–"
                f"{upper_thermal_time:.0f} °Cd"
            ),
            annotation_position="top right",
            annotation_font_color="#6f5200",
        )
        figure.add_vline(
            x=thermal_start.timestamp() * 1000,
            line_color="#c48a00",
            line_dash="dot",
            line_width=1.5,
        )
        if thermal_end is not None:
            figure.add_vline(
                x=thermal_end.timestamp() * 1000,
                line_color="#c48a00",
                line_dash="dot",
                line_width=1.5,
            )
    figure.add_vline(x=cutoff.timestamp() * 1000, line_color="#162f25", line_dash="dash")
    figure.add_annotation(
        x=cutoff, y=1.06, xref="x", yref="paper", showarrow=False,
        text=f"Fecha de consulta · {cutoff:%d/%m/%Y}",
        font=dict(color="#162f25", size=12),
    )
    forecast_start = pd.Timestamp(as_of) + pd.Timedelta(days=1)
    if pd.Timestamp(df["Fecha"].max()) >= forecast_start:
        figure.add_vrect(
            x0=forecast_start,
            x1=pd.Timestamp(df["Fecha"].max()),
            fillcolor="rgba(223,127,52,.10)",
            line_width=0,
            annotation_text="Pronóstico 7 días",
            annotation_position="top left",
        )
    if historical is not None:
        supported = historical.loc[historical["Progreso_Mediano"].notna(), "Fecha"]
        if not supported.empty:
            support_end = supported.iloc[-1]
            orientative_start = max(cutoff, pd.Timestamp(df["Fecha"].max())) + pd.Timedelta(days=1)
            if orientative_start < support_end:
                figure.add_vrect(
                    x0=orientative_start, x1=support_end,
                    fillcolor="rgba(131,161,142,.04)", line_width=0,
                    layer="below", annotation_text="Solo referencia histórica orientativa",
                    annotation_position="bottom right",
                    annotation_font_color="#77877b",
                )
            if support_end < display_end:
                figure.add_vrect(
                    x0=support_end + pd.Timedelta(days=1), x1=display_end,
                    fillcolor="rgba(150,158,167,.08)", line_width=0,
                    layer="below", annotation_text="Sin referencia disponible",
                    annotation_position="top right",
                    annotation_font_color="#7c8580",
                )
    months = pd.date_range(year_start, display_end, freq="MS")
    figure.update_xaxes(
        range=[year_start, display_end], title_text=f"Calendario {cutoff.year}",
        tickmode="array", tickvals=months,
        ticktext=["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "01 Oct"],
    )
    figure.update_yaxes(title_text="Flujo diario (%)", rangemode="tozero", secondary_y=False)
    figure.update_yaxes(
        title_text="Emergencia acumulada (%)", range=[0, 105],
        showgrid=False, secondary_y=True,
    )
    figure.update_layout(
        height=570,
        margin=dict(l=10, r=10, t=50, b=105),
        legend=dict(orientation="h", y=-.22, x=0, font=dict(size=11)),
        hovermode="x unified",
        plot_bgcolor="white",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.15,
        barmode="overlay",
    )
    return figure
