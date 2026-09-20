# PREDWEEM Digital Twin · Tres Arroyos

Gemelo digital de *Lolium multiflorum* basado en
[PREDWEEM/loliumTA_2026](https://github.com/PREDWEEM/loliumTA_2026).
Integra meteorología, observaciones por lote y calibración local 2026 externa
a la red neuronal. El repositorio original y sus pesos se conservan sin cambios.

**PREDWEEM by Guillermo R. Chantre.** Copyright © 2026 Guillermo R. Chantre /
PREDWEEM. Todos los derechos reservados. Consulte [COPYRIGHT.md](COPYRIGHT.md).

## Ejecutar

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

En Streamlit Community Cloud, seleccione `PREDWEEM/TREASA_digitaltween`,
rama `main` y archivo principal `app.py`.

## Visitas periódicas para reducir la hibernación

El workflow [mantener_activo.yml](.github/workflows/mantener_activo.yml) abre
[la aplicación de Tres Arroyos](https://d67etg87zvgftlgckazzw6.streamlit.app/)
con Chromium cada cuatro horas: 00:11, 04:11, 08:11, 12:11, 16:11 y 20:11 UTC
(01:11, 05:11, 09:11, 13:11, 17:11 y 21:11 de Argentina).
También permite ejecución manual desde
**Actions → Mantener activo el gemelo Tres Arroyos → Run workflow** y se ejecuta
al modificar el workflow o su script.

Cuando aparece **Yes, get this app back up!**, la tarea hace clic en el botón
y espera la apertura, con un límite total de cinco minutos. Comprueba el
encabezado de Tres Arroyos, el indicador de emergencia, el panel principal y su
gráfico, incluso si están dentro de un iframe. Una respuesta HTTP 200 por sí
sola no cuenta como éxito. Si la app muestra una excepción o no termina de
cargar, la ejecución queda fallida; los avisos dependen de las preferencias
de notificaciones de GitHub Actions.

La tarea no requiere secretos ni modifica observaciones o parámetros del modelo.
Playwright se instala solamente en el ejecutor de Actions. Esto reduce el riesgo
de hibernación, pero **no garantiza disponibilidad continua**:
[Streamlit suspende las apps sin visitas durante 12 horas](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app#app-hibernation)
y [GitHub puede demorar tareas o desactivarlas tras 60 días sin actividad en un repositorio público](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
Si ocurre lo último, vuelva a habilitar el workflow desde Actions.

## Funcionamiento

- **Estado del lote:** emergencia acumulada, barras azules de flujo diario,
  curva base, curva calibrada, estado actualizado y banda amarilla 600–800 °Cd.
  El eje horizontal muestra fechas calendario.
- **Calibración local 2026:** activada por defecto, con interruptor sobre el
  gráfico principal. La selección se conserva durante la sesión y actualiza
  el gráfico, estado, escenarios y exportación.
- **Observaciones:** carga CSV/XLS/XLSX de flujos en plantas/m² o emergencia
  acumulada. Admite tres repeticiones y media por m² cuando están disponibles,
  y permite borrar los registros seleccionados del lote.
- **Cobertura:** constante o serie FECHA + COBERTURA_PCT (0–100 %), incluso en
  el archivo de emergencia. Interpola entre mediciones, conserva el último valor
  y utiliza el respaldo antes de la primera medición.
- **Escenarios:** cambios exploratorios de meteorología y comparación con el
  estado del lote sin modificar las observaciones guardadas.
- **Trazabilidad:** procedencia, parámetros, asimilación y descarga CSV de la
  trayectoria diaria auditable.

Observaciones y cobertura se guardan por lote en `data/twin_state.db`, que no
se versiona. En alojamientos con disco efímero, conserve los archivos originales
para recuperar los registros después de un reinicio o redespliegue.

## Motor de Tres Arroyos

La configuración inicial conserva cobertura 20 %, Wmax 18,81 mm, exponente Kr=0,
latencia JD 25, termoinhibición de cinco días a 24 °C y primer pico mayor que 0,20.
El choque hídrico usa 45 mm en tres días, hasta JD 110, con piso de emergencia
0,75 antes de aplicar los filtros hídricos. La ANN utiliza temperatura del aire;
la cobertura modifica Ke y el balance hídrico.

Desde el 15/04 aplica un techo del 50 % del máximo previo, con decaimiento
τ=60 días, β=1 e intensidad 0,75. Se conserva el reloj térmico triangular
2–20–30 °C y la banda de manejo 600–800 °Cd.

Las coordenadas del modelo son −38,4500, −60,2763; ET0 conserva la latitud
del motor original. La fuente meteorológica operativa corresponde a INTA
Barrow, −38,388, −60,346. Ambas ubicaciones se documentan por separado.

Para series parciales se utiliza la referencia local `test -emerel tresas
2025.xlsx` del clasificador original. Se mantienen las exclusiones de 2010 y
2015 y se excluyen explícitamente Balcarce y San Pedro. La selección sigue
conteniendo sólo Tres Arroyos 2025: ya utilizaba esta referencia local.
Al disponer de una sola campaña, sus percentiles no representan robustamente
la variabilidad entre años. El total observado parcial no se supone igual al
potencial estacional completo; con conteos cargados se estima el potencial
a partir de sus intervalos o se utiliza un valor previo aportado por el usuario.

La referencia se recarga en cada ejecución para evitar tablas de versiones
anteriores conservadas por Streamlit. La pestaña Trazabilidad muestra las
curvas utilizadas y excluidas. Aplicación, escenarios y calibración utilizan
la misma selección. Se regeneró el perfil 2026 con su nueva huella; los
parámetros y resultados numéricos del ajuste y evaluación permanecen iguales.

Consulte [MODEL_PROVENANCE.md](MODEL_PROVENANCE.md) para la revisión de origen,
los hashes y la correspondencia científica.

## Meteorología y actualización

La fuente predeterminada conserva la jerarquía del repositorio original:

1. **SIGA–INTA Barrow**, estación NH0216: observaciones publicadas.
2. **ECMWF IFS histórico**: puente provisional hasta que SIGA publique el dato.
3. **ECMWF IFS ENS 0,25°**: pronóstico operativo P50, con percentiles,
   probabilidades de precipitación y cantidad de miembros conservados.

`meteo_daily.csv` distingue Fuente, TipoDato, CalidadDato y Emision_UTC.
El gemelo utiliza el estado histórico más siete días disponibles. Al consultar
un corte pasado, los días posteriores se reconstruyen con la meteorología
actualmente archivada; no representan el pronóstico emitido en aquel corte.

El workflow `actualizar_meteo.yml` consulta SIGA y ECMWF a las 07:30 y 15:30 de
Argentina. El pronóstico se recorta al **01/10/2026 inclusive**. Después del
cierre sólo se completan o reemplazan datos históricos hasta esa fecha, sin
consultar nuevos pronósticos del ensamble. Un hueco interior en SIGA detiene la
actualización; no se inventan observaciones. Open-Meteo y un archivo aportado
son opciones adicionales explícitas en la interfaz.

## Calibración local 2026

Se incorporó `VALIDA (1) (4)(2).xlsx`, hoja `Hoja1`, columnas FECHA y PLM2:

| Dato | Valor |
|---|---|
| Muestreos | 17, del 05/02 al 16/09/2026 |
| Intervalos de ajuste | 16, de 7 a 29 días |
| Total registrado | 12.089,67 plantas/m² |
| Repeticiones | No informadas |
| Meteorología fija | 259 días, 01/01–16/09/2026 |
| Procedencia meteorológica | 258 observados SIGA y 1 provisional ECMWF (16/09) |

El cero inicial delimita el primer intervalo hasta el 12/02, también con cero.
No se infiere ausencia de emergencia antes del 05/02. Cada conteo se compara
con la suma simulada sobre su intervalo real. Se conservan los intervalos
largos de 26 y 29 días; no se convierten artificialmente en semanas.

La transformación externa `G(F) = logistic(offset + slope × logit(F))`
ajusta dos parámetros, conserva 0 y 1, mantiene la monotonía y no crea flujos
en días bloqueados por el motor. Los parámetros quedan registrados en el JSON.
No modifica los pesos ANN, el decaimiento ni el tiempo térmico. Cobertura y
Wmax son supuestos operativos originales: el adjunto no los informa.
Sin repeticiones se utiliza un piso común de ponderación, no un error de
muestreo medido.

| Evaluación | RMSE base | RMSE calibrado |
|---|---:|---:|
| Ajuste retrospectivo, 16 intervalos | 1.082,79 | 383,20 |
| Evaluación temporal, 10 intervalos posteriores | 716,33 | 683,27 |

RMSE en plantas/m² por intervalo. La reducción es del 64,6 % en el ajuste y
del 4,6 % en la evaluación temporal; mejoran 4 de 10 intervalos posteriores.
El perfil es **experimental**: un parámetro alcanza su límite, sólo se dispone
de una campaña de ajuste y se usa meteorología realizada, no pronósticos
archivados por emisión. Estos resultados no validan transferencia a otros
años ni precisión predictiva a siete días.

La capa se aplica al seleccionar Tres Arroyos, desde el 16/09/2026 y con el
mismo motor y referencia utilizados al ajustar. Si se asimilan conteos de
2026, utiliza la base para evitar reutilizar esa evidencia en calibración y
asimilación. El motivo aparece junto al interruptor. El ajuste no reduce
automáticamente la incertidumbre.

Los datos adjuntos se conservan como referencia de calibración; no se cargan
automáticamente en SQLite. Para asimilarlos en un lote, descargue el CSV desde
**Calibración por sitio** y cárguelo en **Observaciones**.

`data/calibration/` incluye el Excel original, conteos CSV, meteorología fija,
perfil JSON, resultados de ajuste y evaluación temporal, y procedencia con
hashes. Las actualizaciones meteorológicas diarias no modifican esa copia fija.

Para reproducir el ajuste sin acceso a la red:

```bash
python scripts/calibrate_site.py
```

## Verificación

```bash
python -m pytest -q
python -m compileall -q app.py predweem_twin scripts actualizar_meteo_tres_arroyos.py
```

Las pruebas comparan el motor con una extracción independiente del original y
verifican datos adjuntos, perfil reproducible, cortes temporales, calibración,
asimilación, cobertura, almacenamiento, fuentes y cierre meteorológico.
Se ejecutan automáticamente en GitHub Actions.
