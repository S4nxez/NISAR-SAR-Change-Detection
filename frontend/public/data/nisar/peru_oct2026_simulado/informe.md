# Informe de cambios NISAR · Amazonía peruana · Marañón y Huallaga

2026-10-05 → 2026-10-17 · umbral ±3 dB · agua < -15 dB

> **Aviso.** La fecha 'después' es SIMULADA: escena real del 5 oct 2026 con cambios conocidos añadidos para probar el sistema. Sustituir por la pasada real del 17 oct.

## Resumen

Entre el 2026-10-05 y el 2026-10-17 (12 días) se han comparado 60 310 km² con datos válidos en las dos fechas (pista 83, frame 91, órbita descendente), con el radar NISAR en banda L, polarización HH, a 20 m.

Antes de comparar se ha quitado un desplazamiento global de +1,03 dB, que afecta a toda la escena por igual (humedad general o calibración). Después, el 0,07 % del área (39,4 km²) cambia más de ±3,0 dB. Agrupado, eso da 10 zonas de al menos 0,05 km² que suman 38,5 km².

La clase con más superficie es «Agua nueva» (17,3 km², 1 zona). Superficie que pasa a reflejar como agua lisa: posible inundación o crecida.

La zona más grande (z001) es de tipo «Agua nueva»: 17,31 km² con un cambio medio de −17,7 dB (de −4,9 a −21,6 dB), centrada en -4.9932, -75.9904. Confianza alta.

La superficie con aspecto de agua pasa de 760,1 a 689,1 km² (−71,0 km²): 17,4 km² se vuelven agua y 88,4 km² dejan de serlo.

La correlación entre las dos imágenes es 0,97, es decir, son muy parecidas: la mayor parte de la escena no cambia.

AVISO: la segunda fecha de este par es simulada; los cambios se han inyectado a propósito para validar el método.

Un cambio de radar es una señal, no una prueba: conviene contrastarlo con imagen óptica o conocimiento del terreno.

| Indicador | Valor | Detalle |
|---|---|---|
| Área analizada | 60 310 km² | con datos válidos en las dos fechas |
| Área con cambio | 39,4 km² | 0,06 % del área, |Δ| > 3 dB |
| Zonas de cambio | 10 | de al menos 0.05 km² |
| Días entre pasadas | 12 | 2026-10-05 → 2026-10-17 |
| Desplazamiento global | +1,03 dB | restado antes de clasificar |
| Correlación | 0,97 | 1 = imágenes idénticas |
| Agua | 760,1 → 689,1 km² | +17,4 / −88,4 km² |

## Cambios por clase

| Clase | km² | % | Zonas | km² en zonas | Lectura |
|---|--:|--:|--:|--:|---|
| Agua nueva | 17,32 | 0,029 | 1 | 17,31 | Superficie que pasa a reflejar como agua lisa: posible inundación o crecida. |
| Agua que desaparece | 4,92 | 0,008 | 1 | 4,95 | Superficie que deja de ser agua: retirada de una crecida o lago que mengua. |
| Descenso del eco | 11,79 | 0,020 | 7 | 11,02 | Menos retrodispersión: posible tala, cosecha o suelo más seco. |
| Aumento del eco | 5,37 | 0,009 | 1 | 5,25 | Más retrodispersión: vegetación que crece, estructuras o suelo más húmedo. |

## Coberturas radar (km², antes en filas, después en columnas)

| | Agua lisa | Superficie lisa o vegetación baja | Vegetación densa | Muy brillante |
|---|--:|--:|--:|--:|
| Agua lisa | 671,7 | 83,7 | 4,7 | 0,0 |
| Superficie lisa o vegetación baja | 0,1 | 617,0 | 297,7 | 0,0 |
| Vegetación densa | 17,2 | 7,9 | 53 613,9 | 3 542,3 |
| Muy brillante | 0,1 | 0,0 | 0,2 | 1 453,4 |

Agua: 760,1 → 689,1 km² (aparece 17,4, desaparece 88,4).

## Zonas (10)

| Zona | Clase | km² | Δ dB | dB antes → después | Confianza | Lat, lon |
|---|---|--:|--:|--:|---|---|
| z001 | Agua nueva | 17,31 | -17,7 | -4,9 → -21,6 | alta | -4.9932, -75.9904 |
| z002 | Descenso del eco | 6,39 | -4,8 | -5,5 → -9,3 | media | -5.8435, -75.8887 |
| z003 | Aumento del eco | 5,25 | +4,9 | -5,4 → 0,5 | media | -5.2351, -76.8619 |
| z004 | Agua que desaparece | 4,95 | +9,5 | -18,5 → -8,0 | alta | -4.4353, -76.7195 |
| z005 | Descenso del eco | 2,46 | -4,9 | -6,0 → -9,9 | media | -5.9065, -75.9980 |
| z006 | Descenso del eco | 1,17 | -4,8 | -5,3 → -9,1 | media | -5.7901, -75.8032 |
| z007 | Descenso del eco | 0,81 | -4,7 | -5,4 → -9,1 | media | -5.7828, -75.7894 |
| z008 | Descenso del eco | 0,08 | -7,0 | -4,5 → -10,5 | baja | -4.9798, -76.0056 |
| z009 | Descenso del eco | 0,05 | -6,9 | -4,5 → -10,3 | baja | -4.9715, -75.9893 |
| z010 | Descenso del eco | 0,05 | -6,8 | -4,3 → -10,1 | baja | -4.9918, -75.9793 |

## Escena

- **Sensor:** NISAR L-SAR (banda L), producto L2 GCOV, polarización HH
- **Pista / frame / órbita:** 83 / 91 / Descending
- **Mirada del radar:** Left
- **Polarizaciones (antes / después):** HHHH / HHHH
- **Gránulo antes:** NISAR_L2_PR_GCOV_032_083_D_091_2005_SHSH_A_20261005T232338_20261005T232413_P05023_N_F_J_001.h5
- **Gránulo después:** SIMULADO a partir de NISAR_L2_PR_GCOV_032_083_D_091_2005_SHSH_A_20261005T232338_20261005T232413_P05023_N_F_J_001.h5
- **Píxel / proyección:** 20 m / EPSG:32718
- **Extensión (lat, lon):** -6.5520, -77.6786 — -3.6041, -74.6577
- **Generado:** 2026-11-01T16:41:38Z
