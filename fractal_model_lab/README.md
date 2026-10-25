# Fractal Model Lab

Aplicación TUI en C (`ncursesw`) para diseñar un esquema de IA en forma de
árbol fractal y estimar por adelantado los recursos que necesitará antes de
implementarlo (la parte Python/TensorFlow queda para una fase posterior).

- Cada **hoja** del árbol es un modelo **decisor** (`D`).
- Cada **nodo intermedio** es un modelo de **votación** (`V`) que agrega a
  sus hijos.

## Requisitos

```sh
sudo apt install build-essential libncurses-dev
make
./fractal_lab
```

Tamaño mínimo de terminal: 60x16 (recomendado 100x30 o más).

## Cuadrantes

| # | Panel | Contenido |
|---|-------|-----------|
| 1 | Fractal | Árbol dibujado con conectores de línea (`┌─┴─┐`). Los niveles que no caben nodo a nodo se agrupan por su ancestro visible y se muestran por densidad (`:` `+` `*` `#`). A la derecha, nodos por nivel; `*` marca la raíz de cada copia fractal y el color cambia por copia. |
| 2 | Parámetros | `niveles`, `profundidad`, `exponencial` y sus derivados: niveles totales, nodos, decisores, votantes y nodos por nivel. |
| 3 | Recursos | RAM (con desglose y margen), disco de pesos, CPU por inferencia, vCPU para la latencia objetivo, latencia estimada y contenedor recomendado (con su `docker run`), o clúster si no cabe en uno. |
| 4 | Terminal / logs | Línea de comandos e historial de mensajes. |

## Modelo del árbol

- **niveles (L)**: niveles del árbol base, contando la raíz.
- **profundidad (D)**: hijos por nodo (los nodos por nivel se multiplican por D).
- **exponencial (E)**: veces que el árbol base se aplica sobre sus propias
  hojas (autosemejanza fractal).

Niveles totales = `(L-1)*E + 1`; el nivel `k` (desde 0) tiene `D^k` nodos.
Ejemplo `L=3 D=3 E=2`: 5 niveles con 1, 3, 9, 27 y 81 nodos (121 modelos:
81 decisores y 40 votantes). Los cálculos usan aritmética saturada de 64 bits,
así que los valores extremos se muestran como `>1.8E` y no se desbordan.

## Teclado

| Tecla | Acción |
|-------|--------|
| `Tab` / `Shift-Tab`, `1`-`4` | Cambiar de panel |
| `z` | Maximizar o restaurar el panel activo |
| `g` / `h` / `q` | Generar el informe / ayuda / salir |
| `:` | Ir al terminal (`Esc` vuelve al panel anterior) |
| Fractal: `↑` `↓` `Inicio` `Fin` | Desplazar los niveles mostrados |
| Parámetros: `↑` `↓` | Seleccionar el parámetro |
| Parámetros: `←` `→` o `-` `+` | Cambiar su valor |
| Parámetros: `Enter` | Escribe `set <campo> ` en el terminal |
| Terminal: `RePág` `AvPág` `↑` `↓` | Desplazar los logs |

## Comandos

```
help                      ayuda
generate | gen            informe del esquema actual
stats                     nodos por nivel
set <campo> <n>           también vale '<campo> <n>' (p. ej. 'depth 4')
profile [campo n]         ver o cambiar el perfil de modelo
reset | clear | quit
focus <1-4> | zoom [1-4|off] | scroll <nivel>
```

Campos del árbol: `levels`/`niveles`, `depth`/`profundidad`,
`exponent`/`exponencial`.

## Estimación de recursos

Se basa en un perfil de modelo editable con `profile <campo> <n>`:

| Campo | Por defecto | Significado |
|-------|-------------|-------------|
| `runtime_mib` | 512 | Memoria base del runtime de TensorFlow |
| `leaf_mib` / `voter_mib` | 48 / 6 | RAM por modelo decisor / votante |
| `disk_pct` | 40 | Tamaño de los pesos en disco, en % de la RAM de los modelos |
| `leaf_us` / `voter_us` | 5000 / 200 | CPU por inferencia / voto |
| `target_ms` | 250 | Latencia objetivo, usada para calcular las vCPU |
| `headroom_pct` | 25 | Margen de RAM sobre el total |

El contenedor elegido es el más pequeño de la tabla de `src/container.c`
(micro 1/1 GiB … 8xlarge 96 vCPU/384 GiB) que cubra la RAM con margen y las
vCPU. Si ninguno basta, se propone un clúster de 8xlarge. Son estimaciones
orientativas, no medidas reales de TensorFlow.

## Estructura y normas

```text
include/  cabeceras por módulo (tree, cost, field, format, app, ui, view, command)
src/      tree*, cost/container   -> cálculo
          fractal_*               -> renderizado del árbol
          ui_*                    -> paneles
          input*, command*        -> teclado y terminal
```

Todo el código cumple la Norminette 3 de 42 (`norminette src include`):
cabecera 42, como mucho 25 líneas y 4 parámetros por función, 5 variables por
función y 5 funciones por fichero, sin `for`, `switch` ni ternarios.
