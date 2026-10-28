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
make test        # pruebas de la línea de comandos (tests/cli.sh)
```

Tamaño mínimo de terminal: 60x16 (recomendado 100x30 o más). Con argumentos
funciona sin TUI, ver [Línea de comandos](#línea-de-comandos).

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

## Línea de comandos

Sin argumentos `./fractal_lab` abre la TUI. Con argumentos genera el esquema
sin interfaz y lo escribe en la salida estándar: no necesita terminal, así que
otro programa (la web, en el futuro) puede invocarlo y leer el resultado.

```sh
./fractal_lab --text                            # informe con los valores por defecto
./fractal_lab --depth 4 --exponent=3            # el informe de 'gen' y 'stats'
./fractal_lab --json --niveles 4 --leaf_mib 64  # el esquema completo en JSON
./fractal_lab --help                            # campos, alias, rangos y valores por defecto
```

| Opción | Efecto |
|--------|--------|
| `--text` | Informe en texto, el mismo de `gen` y `stats` (por defecto) |
| `--json` | Esquema completo en JSON |
| `--<campo> <n>`, `--<campo>=<n>` | Fija un campo del árbol o del perfil, por nombre o alias, con los mismos rangos que `set` |
| `-h`, `--help` | Ayuda |

Los campos que no se indican toman su valor por defecto y, si una opción se
repite, vale la última. Con un argumento no válido (opción desconocida, valor
que no es un entero o fuera de rango) no escribe nada en la salida estándar y
explica el error en la de error. Códigos de salida: `0` correcto, `1` error al
escribir la salida, `2` argumentos no válidos.

Salida de `./fractal_lab --json` con los valores por defecto:

```json
{
  "params": {"levels": 3, "depth": 3, "exponent": 2},
  "profile": {"runtime_mib": 512, "leaf_mib": 48, "voter_mib": 6, "disk_pct": 40, "leaf_us": 5000, "voter_us": 200, "target_ms": 250, "headroom_pct": 25},
  "tree": {"total_levels": 5, "nodes": 121, "leaves": 81, "voters": 40, "saturated": false,
    "levels": [
      {"level": 1, "nodes": 1, "role": "voter", "copy": 1, "copy_root": false},
      {"level": 2, "nodes": 3, "role": "voter", "copy": 1, "copy_root": false},
      {"level": 3, "nodes": 9, "role": "voter", "copy": 2, "copy_root": true},
      {"level": 4, "nodes": 27, "role": "voter", "copy": 2, "copy_root": false},
      {"level": 5, "nodes": 81, "role": "leaf", "copy": 2, "copy_root": false}
    ]},
  "resources": {"leaves_mib": 3888, "voters_mib": 240, "runtime_mib": 512,
    "ram_mib": 4640, "required_mib": 5800, "disk_mib": 1652,
    "cpu_us": 413000, "path_us": 5800, "vcpus": 2, "latency_us": 103250},
  "container": {"tier": "medium", "vcpus": 4, "ram_gib": 8, "replicas": 1, "cluster": false}
}
```

| Clave | Contenido |
|-------|-----------|
| `params`, `profile` | Valor de cada campo del árbol y del perfil de modelo |
| `tree` | `total_levels`, `nodes`, `leaves` (decisores), `voters` y `saturated`; en `levels`, por cada nivel (desde 1): `nodes`, `role` (`voter` o `leaf`), `copy` (copia fractal a la que pertenece, desde 1) y `copy_root` (raíz de una copia, el `*` del panel) |
| `resources` | RAM en MiB de los decisores (`leaves_mib`), los votantes (`voters_mib`) y el runtime, total (`ram_mib`) y con margen (`required_mib`); pesos en disco (`disk_mib`); CPU por inferencia (`cpu_us`) y de un camino raíz-hoja (`path_us`) en µs; `vcpus` para la latencia objetivo y latencia estimada (`latency_us`) |
| `container` | Contenedor recomendado (`tier`, `vcpus`, `ram_gib`); si no cabe en uno, `cluster: true` y `replicas` del mayor |

Los números son enteros sin signo de 64 bits. Los saturados (ver *Modelo del
árbol*) valen `18446744073709551615` (2^64-1) y `tree.saturated` indica si lo
están los nodos. Por encima de 2^53 un `Number` de JavaScript pierde precisión.

## Estructura y normas

```text
include/  cabeceras por módulo (tree, cost, field, format, app, ui, view, command, cli)
src/      tree*, cost/container   -> cálculo
          fractal_*               -> renderizado del árbol
          ui_*                    -> paneles
          input*, command*        -> teclado y terminal
          cli*                    -> línea de comandos (sin TUI)
tests/    cli.sh                  -> pruebas de la línea de comandos (make test)
```

Todo el código cumple la Norminette 3 de 42 (`norminette src include`):
cabecera 42, como mucho 25 líneas y 4 parámetros por función, 5 variables por
función y 5 funciones por fichero, sin `for`, `switch` ni ternarios.
