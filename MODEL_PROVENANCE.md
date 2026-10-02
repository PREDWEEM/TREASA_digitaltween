# Procedencia científica del gemelo de Tres Arroyos

Motor original: [PREDWEEM/loliumTA_2026](https://github.com/PREDWEEM/loliumTA_2026/tree/5b52fef47ed2c97aefe45b8939e751141db5216e),
revisión `5b52fef47ed2c97aefe45b8939e751141db5216e`. El repositorio fuente no se modificó.

La interfaz, persistencia, asimilación y calibración externa se adaptaron del
[gemelo Lartigau](https://github.com/PREDWEEM/larti_digitaltween/tree/b14687448c63c538d28ca17fe58f58ecaf01573b).
Los activos neuronales, parámetros fisiológicos y meteorología proceden de
Tres Arroyos. No se trasladó el perfil calibrado de otra localidad.

## Activos originales

| Archivo | SHA-256 |
|---|---|
| `models/IW.npy` | `8614f90cd5f1337ae746690e474587b6fb22cf81652e694573cbfe4573f406d5` |
| `models/LW.npy` | `13cb012d7f4fe8e9e8399b31226e160ed60690cd4fb225a2de40375d250eb97b` |
| `models/bias_IW.npy` | `69423ba136a4caad97bed6b3aae2e7a387d87851a32eb5b2ab8de74dbcae3788` |
| `models/bias_out.npy` | `53451c25cc92da6bff25404a1e47815e38dfe58f7d83bb87c2d471298ec8a12d` |
| `models/modelo_clusters_k3.pkl` | `29f0508543bdda4b2520038c678a9df80ff9be555e0c15d5fa1f4da16a499d30` |

## Correspondencia del motor

Se extrajeron las funciones de `app_emergencia_core.py`, incorporando el parche
activo `modelo_decaimiento_15abril.py`. Las pruebas comparan la trayectoria con
una extracción independiente de esas funciones en
`tests/fixtures/tres_arroyos_original.py`, con distintas coberturas, Wmax y Kr.

- ANN original de cuatro entradas: día juliano, TMAX, TMIN y precipitación.
- Cobertura inicial 20 %; Wmax 18,81 mm; exponente Kr=0.
- Coordenadas del modelo −38,4500, −60,2763; ET0 Hargreaves con esa latitud.
- Latencia hasta JD 25 y primer pico estrictamente mayor que 0,20.
- Choque hídrico: 45 mm en tres días, hasta JD 110, piso 0,75 antes de filtros
  (original; v2: 60 mm y piso 0,5, ver la sección «Reglas v2»).
- Termoinhibición: media móvil de cinco días mayor o igual que 24 °C (original; v2: 26 °C).
- Factor hídrico sigmoide, corte de humedad relativa menor que 0,20 y recarga
  habilitada por una lluvia diaria mayor o igual que Wmax.
- Desde el 15/04: techo inicial del 50 % del máximo previo, multiplicado por
  `(1 − I) + I × exp(−(días/τ)^β)`, con τ=60 días, β=1 e I=0,75.
  Sin emergencia positiva previa al 15/04, el original no impone un techo.
- Reloj térmico triangular 2–20–30 °C; ventana de manejo 600–800 °Cd.

La cobertura diaria, la normalización parcial, la asimilación y la calibración
externa son extensiones del gemelo. La cobertura sólo afecta el balance hídrico
y el diagnóstico de suelo, no las entradas neuronales. La calibración no
modifica el reloj térmico ni los pesos.

## Reglas v2 (validación 2008–2026)

Cambios respecto del motor original, validados contra los conteos de campo con la
métrica de **masa mal ubicada** (diferencia de variación total entre la
distribución observada y la modelada de la emergencia entre conteos):

| Regla | Original | v2 |
|---|---|---|
| Termoinhibición (media de 5 días) | 24 °C | **26 °C** |
| Umbral de choque hídrico (3 días) | 45 mm | **60 mm** |
| Piso del choque hídrico | 0,75 | **0,5** |
| Techo desde el 15/04 | 50 %, τ=60 d | **10 % del máximo previo, τ=40 d, I=0,75** |
| Condición del techo | siempre | **sólo si hubo ≥1 día con flujo ≥0,5 antes del 15/04** |

La condición evita recortar los años de emergencia tardía (en Bordenave 2010 y
2015, más del 80 % de la emergencia ocurrió después del 10/04).

Evidencia (Tres Arroyos 2023–2026 (4 campañas)): masa mal ubicada media 41,4 % → 22,0 %. En las 14 campañas
disponibles (Tres Arroyos, Lartigau, Bordenave 2026 y Bordenave 2008–2015) el
promedio bajó de 43,8 % a ~33 %; el error medio de la curva acumulada, de 7,4 a
5,6 puntos porcentuales; y el tamaño de los tres pulsos mayores pasó de 0,61 a
0,96 del observado (mediana). Límites: pocas campañas, parte del clima de
2026 proviene de pronósticos archivados, y los parámetros se eligieron en parte
con las mismas campañas. El efecto del piso y del umbral del choque hídrico no
es estable entre años; Bordenave 2010 sigue mal ubicada (65 %). No se evaluó la
magnitud absoluta (plantas por m²).

**Interruptor de retorno:** `ModelParameters.legacy()` devuelve los valores
anteriores (por ejemplo, `run_predweem(weather, model, ModelParameters.legacy())`).
El perfil de calibración se recalcula porque la huella del modelo incluye
`core.py`; el perfil anterior queda invalidado por diseño.

## Referencia estacional

El pool utiliza exclusivamente **Tres Arroyos 2023, 2024, 2025 y 2026**. La única
curva seleccionada del clasificador original sigue siendo
`test -emerel tresas 2025.xlsx`. El binario permanece intacto; todas sus otras
curvas, incluidas `2023.xlsx` y `2024.xlsx`, quedan fuera de este pool local.

- 2023: adjunto de Ramón, 29 fechas entre 27/02 y 09/10, cinco réplicas y media
  verificada en plantas/m². Total 2.658,8 plantas/m², sin cero inicial informado.
- 2024: adjunto **emergencia 2024.xlsx**, diez promedios entre 15/02 y 30/07,
  total 7.946,67 plantas/m². Sin réplicas individuales ni cero inicial.
- 2025: acumulado de la curva procesada dividido por su total.
- 2026: 17 registros entre 05/02 y 16/09, acumulados y divididos por su total.

Los conteos se interpolan como acumulados, conservando cada masa por intervalo.
No se infieren nacimientos diarios observados. Se desconocen las fechas previas
al primer conteo de cada archivo. Los primeros acumulados positivos de 2023 y 2024 se conservan;
el salto de composición al ingresar esa referencia no se representa como flujo
diario ni determina el máximo semanal. Las semanas incompletas quedan señaladas.

Las campañas aportan igual peso a los cuantiles. La envolvente de máximo
acumulado mantiene el ancla no decreciente; se conservan cuantiles empíricos y
curvas individuales para auditoría. Tras el último conteo se mantiene 1 como
supuesto de referencia de la ventana, sin afirmar cierre biológico.

2023 está disponible desde el 09/10/2023, 2024 desde el 30/07/2024,
2025 desde el 01/01/2026 y 2026 desde
el 16/09/2026. La incorporación de los adjuntos 2023 y 2024 al sistema ocurrió el
30/09/2026. Las revisiones retrospectivas no reproducen pronósticos emitidos.
El ajuste adicional 2026 se regeneró con la nueva huella y el pool de cuatro años;
los cortes previos al 16/09 usan 2023, 2024 y 2025. Los pesos ANN y las reglas fisiológicas no cambian.
El núcleo pasa las fechas al cálculo del progreso histórico para alinear el
calendario bisiesto con los gráficos, sin cambiar el flujo bruto ni el reloj térmico.

Los Excel originales 2023 se conservan en `data/reference/`, con CSV extraídos,
réplicas, SD/EE y manifiesto `tres_arroyos_2023_source.json`. La extracción es
reproducible mediante `scripts/import_reference_2023.py`.

| Original 2023 | SHA-256 |
|---|---|
| `tres_arroyos_2023_counts_original.xlsx` | `51eae9e32c3544a1688a7c45cf8343b3486c5af29a168aea30ce9abc52244425` |
| `tres_arroyos_2023_weather_original.xls` | `a915f3eb6d939e24b0a7cb1b1c9d88c956cc5849b22743ddb322fc55f4f187d6` |

La meteorología adjunta tiene 283 fechas del 01/01 al 10/10, sin fechas
faltantes. TMAX y TMIN del 17/06 están vacías y no se imputan. La fuente no
identifica estación ni coordenadas. Se archiva para análisis históricos y no
sustituye la meteorología operativa ni participa en el cálculo del acumulado
observado. No se usa para reentrenar la ANN ni ajustar una capa 2023.

Los originales 2024 se conservan en `data/reference/`, junto con conteos,
meteorología extraída y `tres_arroyos_2024_source.json`. La extracción se reproduce
con `scripts/import_reference_2024.py`.

| Original 2024 | SHA-256 |
|---|---|
| `tres_arroyos_2024_counts_original.xlsx` | `b480daf0dd201b52945b5a70b695c27f240ab8cc96d16af81d759f15cf58fb33` |
| `tres_arroyos_2024_weather_original.csv` | `42d534e9863f59fe238af080ff204857c02c9ce73962f309c7ff49661dd5088a` |

La meteorología 2024 contiene 335 registros fechados completos del 01/01 al
30/11, incluido el 29/02. De las 23.705 filas originales, 23.370 no tienen fecha:
885 vacías y 22.485 sólo con precipitación. Se excluyen del CSV procesado, sin
asignar fechas ni alterar el original. No se identifica estación ni se reemplaza
la meteorología operativa. No se reentrena la ANN ni se calibra una capa 2024.

El calendario del pool conserva mes/día. El conteo 29/02/2024 ocupa la coordenada
59.5 de un eje común no bisiesto; los días de marzo en adelante no se desplazan.
Las curvas conservan los acumulados en todas las fechas muestreadas; los valores
intermedios se interpolan en ese eje. En una vista no bisiesta se integra el
incremento del 29/02 en el paso al 01/03. El primer conteo 2024 (346,67 plantas/m²)
no se reparte en días desconocidos. El 100 % se refiere a la ventana del archivo:
la prolongación después del 30/07 no acredita el fin de la emergencia anual.

## Meteorología y calibración

El actualizador, postprocesador P50, workflow y datos operativos se toman de
la misma revisión fuente. Se distingue la ubicación meteorológica INTA Barrow
(−38,388, −60,346) de las coordenadas utilizadas por el motor. Se conserva el
cierre inclusivo del 01/10/2026 y la prioridad SIGA sobre ECMWF provisional.

El ajuste utiliza 259 días fijos del 01/01 al 16/09/2026: 258 observados SIGA y
un dato ECMWF provisional el 16/09. Se incluyen el Excel original aportado y
su CSV de 17 muestreos. La hoja contiene FECHA y PLM2, sin repeticiones ni
cobertura; la localidad se asigna por la instrucción del usuario.

El origen, revisión, coordenadas y hashes están en
`data/calibration/tres_arroyos_2026_source.json` y en el perfil JSON.
Los resultados de ajuste se separan de la evaluación temporal sobre diez
intervalos posteriores. Se usa meteorología realizada; no se presenta como
validación independiente de pronósticos emitidos ni de una campaña distinta.
