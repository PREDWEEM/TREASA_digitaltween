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
- Choque hídrico: 45 mm en tres días, hasta JD 110, piso 0,75 antes de filtros.
- Termoinhibición: media móvil de cinco días mayor o igual que 24 °C.
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

## Referencia estacional

Se selecciona `test -emerel tresas 2025.xlsx` del clasificador original mediante
el filtro `tresas`, manteniendo la exclusión de 2010 y 2015 y excluyendo
explícitamente Balcarce y San Pedro. El archivo binario no se modifica.
`load_local_seasonal_reference` incorpora además los conteos originales
`data/calibration/tres_arroyos_2026_counts.csv` desde su última fecha,
16/09/2026. Antes de ese corte, incluso en evaluaciones temporales, utiliza
exclusivamente 2025. El perfil JSON registra las fuentes y sus hashes.

La curva 2026 es el acumulado de los 17 registros dividido por el total
observado del 05/02 al 16/09, con interpolación lineal del acumulado entre
visitas. Conserva las masas por intervalo, no atribuye observaciones diarias
ni ceros previos al inicio. Cada campaña tiene igual peso en los cuantiles.
La envolvente de máximo acumulado evita un retroceso del ancla al cambiar
la disponibilidad de curvas; se conservan cuantiles empíricos sin modificar
para auditoría. Tras el último conteo se mantiene 1 como referencia de esa
ventana, sin afirmar ausencia de nacimientos posteriores ni cierre biológico.
Dos campañas no permiten estimar probabilidades robustas.

El perfil 2026 registra los filtros y nombres incluidos/excluidos y se regenera
para actualizar su huella, incluyendo el CSV 2026. El ajuste final utiliza
ambas referencias y los cortes temporales anteriores al 16/09 sólo 2025.
Esta revisión conserva los parámetros y las métricas redondeadas del ajuste
y evaluación temporal, porque al cierre ambas referencias alcanzan 1.
La referencia se lee en cada ejecución de la interfaz, evitando resultados
obsoletos de la caché de Streamlit. Se conservan el anclaje estacional, la ANN,
el motor fisiológico y los datos de campo y meteorología originales.

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
