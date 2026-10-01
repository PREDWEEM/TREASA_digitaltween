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

- **Configuración del gemelo:** panel desplegable dentro del cuerpo principal,
  organizado en lote y fecha, meteorología y cobertura, y parámetros. Todos los
  controles se encuentran allí; se elimina el panel lateral y su botón de apertura.
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

### Alerta preventiva de inicio (hasta 7 días)

Activada por defecto en **Configuración del gemelo**, con opción de desactivarla.
Consulta la trayectoria base desde el comienzo de la campaña y avisa cuando
`Primer_Pico_Habilitado` se activa entre mañana y el séptimo día, inclusive.
Muestra la fecha modelada y los días de anticipación disponibles para organizar
una recorrida. Funciona sin observaciones de campo. Si hay un conteo positivo
del lote hasta el corte, informa que ya había emergencia a más tardar en esa visita;
no trata esa fecha como el inicio biológico exacto.

La alerta **no desplaza curvas, no retrocede el origen del TT ni cambia los
umbrales térmicos o de intensidad**. Es un aviso visual en la app, no una
notificación externa. Puede anticipar hasta siete días si la meteorología y
el detector lo permiten; no garantiza detectar cada inicio. Si faltan días,
no informa ausencia de emergencia: indica horizonte incompleto. Una señal de
inicio dentro de los días disponibles sí genera vigilancia preventiva.

Las revisiones con meteorología histórica, sin procedencia verificable o con
emisiones posteriores al corte se identifican explícitamente. No equivalen a
pronósticos emitidos anticipadamente. La ausencia de señal no descarta nacimientos.
El detalle queda en Trazabilidad y en el estado guardado (`onset_alert`).

El gráfico de flujo muestra una **flecha vertical violeta** sobre el día exacto
de la alerta inicial de monitoreo: **inicio modelado menos siete días**, con
etiqueta `DD/MM/AAAA · estimada`. Se conserva al alternar entre flujo semanal y
diario, sin moverla al lunes o al centro de una semana. Esta referencia se
recalcula con el inicio disponible al corte; no acredita que se haya emitido
un aviso en esa fecha. Su valor queda en `onset_alert.monitoring_alert_date`.
Si aún no hay inicio modelado en el horizonte, la alerta está desactivada o
la fecha cae fuera del calendario visible, no se dibuja la flecha.
El origen del reloj térmico sigue siendo el primer pico modelado.

### Parámetros fisiológicos

La configuración inicial conserva cobertura 20 %, Wmax 18,81 mm, exponente Kr=0,
latencia JD 25, termoinhibición de cinco días a 24 °C y primer pico mayor que 0,20.
El choque hídrico usa 45 mm en tres días, hasta JD 110, con piso de emergencia
0,75 antes de aplicar los filtros hídricos. La ANN utiliza temperatura del aire;
la cobertura modifica Ke y el balance hídrico.

Desde el 15/04 aplica un techo del 50 % del máximo previo, con decaimiento
τ=60 días, β=1 e intensidad 0,75. Se conserva el reloj térmico triangular
2–20–30 °C y la banda de manejo 600–800 °Cd.

El indicador **TT desde primer pico** muestra el tiempo térmico y un semáforo:

- **🔴 FUERA DE CONTROL:** TT >800 °Cd.
- **🟠 ULTIMO PLAZO:** TT >700 y ≤800 °Cd.
- **🟡 CONTROL A TIEMPO:** TT ≥600 y ≤700 °Cd.
- **🟢 AUN NO CONTROLAR:** TT <600 °Cd.

Los valores exactos de 600 y 700 °Cd corresponden a CONTROL A TIEMPO; 800 °Cd
corresponde a ULTIMO PLAZO. La clasificación utiliza el TT sin redondear, aunque
el indicador lo presenta con un decimal. Si el TT no es válido, muestra SIN DATOS
en gris. La categoría se conserva en el estado como `thermal_control_stage`.
Este semáforo utiliza el reloj térmico existente y no modifica su cálculo.

Las coordenadas del modelo son −38,4500, −60,2763; ET0 conserva la latitud
del motor original. La fuente meteorológica operativa corresponde a INTA
Barrow, −38,388, −60,346. Ambas ubicaciones se documentan por separado.

Para series parciales se utiliza un pool exclusivamente local de
**Tres Arroyos 2023, 2024, 2025 y 2026**, construido con:

| Campaña | Fuente | Alcance |
|---|---|---|
| 2023 | `data/reference/tres_arroyos_2023_counts.csv` | 29 visitas del 27/02 al 09/10, cinco réplicas y promedio en plantas/m² |
| 2024 | `data/reference/tres_arroyos_2024_counts.csv` | 10 conteos promedio del 15/02 al 30/07, total 7.946,67 plantas/m² |
| 2025 | `test -emerel tresas 2025.xlsx` | Curva procesada del clasificador original |
| 2026 | `data/calibration/tres_arroyos_2026_counts.csv` | 17 registros del 05/02 al 16/09, total 12.089,67 plantas/m² |

Cada curva de conteos usa **suma acumulada de PLM2 / suma de PLM2 registrada**.
Se interpola el acumulado entre visitas, preservando la masa de cada intervalo.
Cada campaña tiene el mismo peso en los cuantiles, sin ponderar por densidad,
número de fechas o cantidad de réplicas. La mediana del pool no es
el promedio aritmético de todos los años. Tanto el histórico del gráfico como el ancla de la
normalización y el máximo semanal del semáforo se obtienen del mismo pool.

**Disponibilidad temporal:** 2023 desde el último conteo del 09/10/2023;
2024 desde el último conteo del 30/07/2024;
2025 desde el 01/01/2026 como referencia previa a la campaña operativa;
2026 desde el 16/09/2026. Las revisiones de 2026 anteriores al 16/09 usan
2023, 2024 y 2025. Desde el 16/09, y para el calendario de referencia 2027,
participan los cuatro años. Esta incorporación ocurrió el 30/09/2026: una
revisión pasada no reproduce la información efectivamente cargada entonces.
Se conservan las exclusiones de 2010, 2015, Balcarce, San Pedro y todas las
curvas del clasificador salvo Tres Arroyos 2025. Las curvas genéricas
`2023.xlsx` y `2024.xlsx` del clasificador continúan excluidas: las nuevas
referencias utilizan exclusivamente los adjuntos locales de Tres Arroyos.

Antes del 27/02, 2023 permanece desconocido; antes del 15/02 sucede lo mismo
con 2024 y antes del 05/02 con 2026. El resumen usa las curvas disponibles en cada día y conserva su
máximo acumulado para evitar retrocesos cuando cambia el número de campañas.
La tabla incluye los cuantiles `Empirico` sin esa regularización y las cuatro
curvas individuales para auditoría. Tras el último conteo se mantiene el total
de la ventana como supuesto de normalización, sin certificar cierre biológico
ni agotamiento del banco de semillas. El eje de referencia conserva los datos
hasta el 09/10; el gráfico principal sigue recortado al **01/10**.

Cuatro campañas aportan contexto local, pero sus P10 y P90 son descripciones,
no intervalos de confianza ni probabilidades robustas. El pool cambia el ancla
del denominador estacional; no reentrena la ANN ni modifica el flujo sin
normalizar o el reloj térmico. Las revisiones de campañas incluidas en el pool
son retrospectivas y no demuestran precisión predictiva independiente.

### Fuentes incorporadas de 2024

- `tres_arroyos_2024_counts_original.xlsx`: copia íntegra de **emergencia 2024.xlsx**,
  hoja Hoja1, FECHA y pl.m2 en A2:B11. Los diez valores son promedios de nacimientos
  por visita/intervalo, del **15/02 al 30/07/2024**, y suman **7.946,67 plantas/m²**.
  No se aportan réplicas individuales: no se calcula ni inventa SD/EE.
- `tres_arroyos_2024_weather_original.csv`: copia íntegra de **meteo TRES ARROYOS 2024.csv**,
  separador punto y coma y decimal coma. El CSV extraído contiene **335 fechas
  consecutivas del 01/01 al 30/11/2024**, con TMAX, TMIN y precipitación completas.
  Se excluyen del procesamiento **23.370 filas sin fecha** (885 vacías y 22.485
  con sólo precipitación); se conservan en el original y se documenta su exclusión.
  No se asignan a fechas, no se suman ni se imputan datos. Estación no informada.
- `tres_arroyos_2024_source.json`: procedencia, ventanas, unidades, limpieza,
  limitaciones y hashes de originales y CSV. La meteorología asociada se archiva
  para análisis históricos; no reemplaza la meteorología operativa ni se necesita
  para construir el acumulado observado. Los conteos no se cargan como observaciones
  de la campaña actual y no se ajusta una nueva calibración 2024.

El primer conteo es **346,67 plantas/m² (4,36 % del total)** y no tiene inicio
conocido. Se conserva sin cero inicial inventado y se aplica el mismo criterio
para cambios de composición y semanas parciales que en 2023. Mantener el 100 %
después del 30/07 es un supuesto de referencia: no demuestra ausencia de
nacimientos posteriores ni que la campaña haya finalizado biológicamente.

**Calendario bisiesto:** las curvas se alinean por mes/día, con una coordenada
común no bisiesta. El conteo real del **29/02/2024** se conserva en `Julian_days=59.5`,
entre 28/02 (59) y 01/03 (60); marzo–diciembre no se desplazan un día. La
interpolación se realiza en ese calendario común. En años no bisiestos no se
crea una fecha 29/02: su incremento queda integrado en el intervalo al 01/03.
En años bisiestos el punto se muestra el 29/02. El ancla operativa y los gráficos
utilizan esta misma correspondencia. `Julian_days` es aquí una coordenada del
pool, no el ordinal real de 2024; las fechas originales se mantienen intactas.

Extracción reproducible: `python scripts/import_reference_2024.py`.
Los CSV y la procedencia se pueden descargar en
**Trazabilidad → Fuentes de Tres Arroyos 2024**.

### Fuentes incorporadas de 2023

Los archivos originales se conservan sin cambios en `data/reference/`:

- `tres_arroyos_2023_counts_original.xlsx`: hoja Emergencias, encabezado en fila 2,
  fechas en A3:A31, réplicas en B3:F31 y promedios en G3:G31. Los 29 promedios
  coinciden con las cinco réplicas. Suman **2.658,8 plantas/m²**. El CSV conserva
  REP1–REP5, PLM2, N_REPLICAS, SD muestral y EE = SD / raíz de 5.
- `tres_arroyos_2023_weather_original.xls`: hoja Datos diarios, **283 fechas**
  consecutivas entre 01/01 y 10/10/2023, TMAX, TMIN y precipitación. El CSV
  asociado conserva **TMAX y TMIN faltantes el 17/06/2023**, sin imputación ni
  sustitución por cero. El adjunto no identifica estación ni coordenadas.
- `tres_arroyos_2023_source.json`: procedencia, unidades, transformaciones,
  ventanas, limitaciones y hashes SHA-256 de originales y CSV.

La meteorología se archiva como fuente asociada para análisis históricos.
La curva observada se construye con los conteos; no necesita rellenar la
meteorología faltante ni ejecutar el modelo sobre ese archivo. No reemplaza
la meteorología operativa, no se asimilan esos conteos como observaciones de
la campaña actual ni se ajusta una nueva capa de calibración 2023.

El primer conteo, **570 plantas/m² el 27/02**, equivale al 21,44 % del total
registrado y no tiene fecha inicial de intervalo. Se conserva el acumulado,
sin inventar un cero previo ni repartirlo entre días desconocidos. Al ingresar
esa curva al pool puede cambiar la mediana: ese salto se marca
`Flujo_No_Comparable` y se excluye del flujo diario y del máximo semanal.
La semana afectada queda parcial y rayada. `Incremento_No_Distribuido` registra
ese cambio de composición; no es evidencia de un nacimiento diario ni flujo cero.
La suma de los flujos históricos evaluables no tiene por qué alcanzar 100 %
cuando parte del incremento no puede distribuirse temporalmente.

Para reproducir la extracción desde los originales:

```bash
python scripts/import_reference_2023.py
```

Los archivos y sus limitaciones también se pueden consultar y descargar en
**Trazabilidad → Fuentes de Tres Arroyos 2023**.

La referencia se recarga en cada ejecución para evitar tablas de versiones
anteriores conservadas por Streamlit. La pestaña Trazabilidad muestra las
curvas utilizadas y excluidas y permite descargar la referencia activa.
Aplicación, escenarios y calibración utilizan el mismo criterio de fecha.

### Contexto histórico en dos gráficos a la par

El eje temporal muestra del **1 de enero al 1 de octubre** del año consultado.
El recorte es visual y no vuelve a normalizar las series por el período visible.
El **flujo de emergencia** se muestra en el gráfico izquierdo y la **emergencia acumulada**
en el derecho. Cada gráfico tiene su propio eje Y, con el mismo calendario y la
misma fecha de consulta. El flujo conserva las barras y el acumulado, las curvas
y puntos de campo.
El selector **Mostrar flujo** ofrece **Semanal** (por defecto) y **Diario**.
La vista semanal suma los porcentajes diarios en las mismas semanas de lunes a
domingo para ambas series; no calcula promedios, no divide por el pico y no
modifica la curva acumulada, el estado del gemelo ni las exportaciones diarias.
Las semanas incompletas aparecen grises y rayadas; el detalle indica los días disponibles
y cuántos pertenecen a la proyección. No se extrapolan los días faltantes ni se
incluyen datos posteriores al horizonte meteorológico. Para comparar magnitudes,
se deben usar semanas completas en ambas series. Los límites del 1 de enero y
1 de octubre también pueden producir semanas parciales.
Las columnas completas se colorean con la misma clasificación del indicador:
**rojo** (>75 % del máximo semanal histórico), **naranja** (25–75 % inclusive),
**amarillo** (>0 y <25 %) y **verde** (flujo cero). El denominador es el máximo
de las semanas completas del pool visible, en la misma escala que el flujo del
gemelo. Se calcula con la referencia disponible para la fecha consultada.
Esta comparación solo determina el color: la altura sigue siendo el porcentaje
del total estacional, sin renormalizar por el máximo. El histórico usa los mismos
colores con menor opacidad. Las semanas completas sin flujo del gemelo se señalan
con marcas verdes en y=0. Una semana parcial, inválida o un flujo positivo sin
máximo histórico disponible queda sin categoría, en gris.
El detalle al pasar el cursor muestra la categoría y el porcentaje del máximo.
El indicador de los próximos siete días y las barras comparten los umbrales;
sus ventanas son diferentes: mañana–día 7 frente a lunes–domingo.
La agregación facilita comparar la distribución temporal, pero no elimina las
diferencias entre el pool y el gemelo ni demuestra una mejora predictiva.
El fondo tenue muestra el resumen del pool histórico local,
junto con el flujo diario derivado de ese resumen. Es una referencia
**orientativa**, no una predicción meteorológica ni una serie de conteos diarios.
Ambos flujos comparten el eje Y del gráfico izquierdo y se expresan como incremento del
acumulado multiplicado por 100, diario o sumado por semana. El histórico se refiere al total de sus ventanas
registradas; el gemelo, al total estacional estimado. No se dividen por el máximo
diario de cada serie: un valor de 2 equivale a un avance de 2 puntos porcentuales.
El eje del flujo y los cuadros al pasar el cursor muestran explícitamente `%`
para las dos series. Los valores menores del histórico no son proporciones sin
convertir: la interpolación entre visitas y la combinación de campañas suavizan
sus picos respecto de una trayectoria con pulsos diarios concentrados.
Las campañas 2023, 2024, 2025 y 2026 siguen formando parte del pool cuando corresponde por
fecha, pero no se dibujan como curvas individuales. Sus datos siguen
disponibles en Trazabilidad. El resumen conserva los supuestos de normalización
descritos arriba.

Una línea vertical identifica la fecha de consulta. El estado actualizado se
muestra hasta esa fecha y su proyección discontinua alcanza sólo la meteorología
disponible, como máximo siete días. Después sigue visible el contexto histórico.
El calendario posterior al final del eje histórico se marca **«Sin referencia
disponible»**: no se agregan ceros ni se extiende el acumulado al resto del año.
La leyenda bajo el gráfico separa el remanente histórico orientativo del remanente
estimado por el gemelo. El fondo no extiende la meteorología ni la trayectoria:
el mismo pool se utiliza como referencia de la intensidad semanal descrita abajo.

### Intensidad de emergencia y semáforo

La intensidad de emergencia compara **la suma del flujo diario del gemelo de t+1 a t+7** con
**el máximo semanal del pool histórico local disponible en la fecha de consulta**.
El denominador usa el mismo resumen histórico del gráfico, trasladado al calendario
consultado y agregado de lunes a domingo, dentro del 1 de enero al 1 de octubre.
Sólo participan semanas completas con siete días válidos. No se usa el máximo
diario, el máximo individual de una campaña ni el flujo histórico de esa misma fecha.

`Índice = flujo previsto en los próximos 7 días / máximo semanal histórico`.

- **🔴 Alta:** índice mayor que 0,75 (más del 75 % del máximo).
- **🟠 Media:** índice entre 0,25 y 0,75 inclusive.
- **🟡 Baja:** flujo positivo e índice menor que 0,25 (menos del 25 % del máximo).
- **🟢 Nula:** flujo semanal exactamente igual a cero, con siete días válidos.

El indicador principal muestra la luz del semáforo junto al nombre de la intensidad,
el horizonte de siete días y el porcentaje del máximo histórico. Los escenarios usan
las mismas denominaciones y colores. El color se acompaña siempre con texto.

Ejemplo ilustrativo: si el máximo histórico es 20 % del total por semana y el
flujo previsto es 12 % del total en los próximos siete días, el índice es 60 %:
intensidad Media. Un flujo previsto exactamente igual a cero, con siete días válidos,
corresponde a Nula. Los flujos positivos pequeños siguen siendo Baja aunque el
porcentaje redondeado mostrado sea 0,0 %; el redondeo no determina la categoría.
El índice puede superar el 100 %; no es una probabilidad ni un umbral de daño económico.

Ambos flujos se comparan en la misma escala fraccional (o ambos en porcentaje),
conservando sus respectivos denominadores: total de las ventanas históricas
y total estacional estimado del gemelo. Se mantienen los criterios de disponibilidad
de campañas: 2023, 2024 y 2025 en cortes de 2026 anteriores al 16/09; los cuatro años desde esa fecha.

El horizonte futuro es móvil desde la fecha elegida, por lo que puede abarcar
partes de dos barras de semanas calendario. El selector Diario/Semanal no cambia
la intensidad. Se exige el flujo de las siete fechas consecutivas; datos ausentes,
inválidos o duplicados no se rellenan con cero. Sin los siete días se informa
«Sin pronóstico» o «Pronóstico incompleto», con luz gris, sin asignar intensidad.
Para un flujo positivo sin máximo histórico válido se indica «Sin referencia»
en gris. Con siete flujos válidos iguales a cero, la intensidad es Nula aunque
no haya referencia histórica; no se calcula un cociente con denominador cero.
La regla también
se aplica al acercarse al cierre meteorológico del 1 de octubre.
El indicador, los escenarios y el estado exportado (`intensity_7d`) conservan el cociente,
el flujo previsto, el máximo de referencia y la cantidad de días disponibles.

La vista admite el calendario de 2027 (y conserva mes/día en años bisiestos),
pero no altera la campaña meteorológica operativa, cuyo cierre continúa siendo
01/10/2026. Para una consulta real del 05/05/2027 se necesita habilitar esa campaña
y disponer de su meteorología. Las pruebas del gráfico usan series sintéticas;
no constituyen un pronóstico real de 2027.

El perfil adicional 2026 se regeneró con una huella que incluye las fuentes
2023 y 2024 y la alineación del calendario. El ajuste al cierre utiliza los cuatro años; sus evaluaciones temporales
anteriores al 16/09 usan 2023, 2024 y 2025. Se conservan la ANN, los parámetros
fisiológicos y los conteos y la meteorología de ajuste 2026. Las métricas
actualizadas de la evaluación retrospectiva aparecen a continuación.

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
| Evaluación temporal, 10 intervalos posteriores | 692,35 | 509,50 |

RMSE en plantas/m² por intervalo. La reducción es del 64,6 % en el ajuste y
del 26,4 % en la evaluación temporal; mejoran 4 de 10 intervalos posteriores.
El perfil es **experimental**: un parámetro alcanza su límite, sólo se dispone
de una campaña de ajuste y se usa meteorología realizada, no pronósticos
archivados por emisión. Estos resultados no validan transferencia a otros
años ni precisión predictiva a siete días.

La capa se aplica al seleccionar Tres Arroyos, desde el 16/09/2026 y con el
mismo motor y referencia utilizados al ajustar. Si se asimilan conteos de
2026, utiliza la base para evitar reutilizar esa evidencia en calibración y
asimilación. El motivo aparece junto al interruptor. El ajuste no reduce
automáticamente la incertidumbre.

Los datos adjuntos se utilizan para calibración y para la referencia estacional
local, según la fecha del estado; no se cargan
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


## Disponibilidad operativa de porcentajes (01/10/2026)

Durante una actualización de Streamlit, la app recarga los módulos locales en
orden de dependencia si cambia el código del paquete. Así evita mezclar una
interfaz nueva con un constructor de estado antiguo sin
`normalization_available`. La misma revisión identifica el modelo en caché;
los cambios normales de fecha no vuelven a cargar los módulos ni borran conteos.

**Normalización inicial:** el ancla usa exclusivamente el último estado hasta
la fecha de corte. Nunca se busca un ancla en los días futuros ni se utiliza el
total del período parcial como sustituto estacional. Se requiere señal
acumulada mayor a 1e-12 y progreso mediano histórico mayor al 1%. Si falta esa
información se muestra **“porcentaje aún no estimable”**: acumulado, remanente,
flujos porcentuales, potencial y densidades modeladas quedan sin estimar.
Esto no equivale a cero ni a intensidad Nula. La alerta inicial y el tiempo
térmico siguen utilizando el motor biofísico original; el histórico permanece
visible como orientación. Al extender el pronóstico no cambia el porcentaje
del pasado para un mismo corte y referencia.

Los conteos pueden cargarse y conservarse en plantas/m² mientras la asimilación
porcentual está pendiente. Cuando existe una normalización válida se vuelven a
utilizar esos conteos originales. La base SQLite admite porcentaje nulo para
estos registros y migra automáticamente las tablas previas conservando sus
filas. Los CSV exportan el indicador `Normalizacion_Disponible` y el motivo.
La llamada al motor **sin fecha de corte** conserva el cálculo retrospectivo
por total del período para diagnósticos; no es la ruta operativa de la app.
