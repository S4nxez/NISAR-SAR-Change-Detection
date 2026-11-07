# Fractal Model Lab

TUI application in C (`ncursesw`) to design an AI schema shaped as a fractal
tree and estimate up front the resources it will need before implementing it
(the Python/TensorFlow part is left for a later phase).

- Every **leaf** of the tree is a **decider** model (`D`).
- Every **intermediate node** is a **voting** model (`V`) that aggregates its
  children.

## Requirements

```sh
sudo apt install build-essential libncurses-dev
make
./fractal_lab
```

Minimum terminal size: 60x16 (100x30 or more recommended).

## Quadrants

| # | Panel | Content |
|---|-------|---------|
| 1 | Fractal | Tree drawn with line connectors (`┌─┴─┐`). Levels that do not fit node by node are grouped by their visible ancestor and shown by density (`:` `+` `*` `#`). On the right, nodes per level; `*` marks the root of each fractal copy and the color changes per copy. |
| 2 | Parameters | `levels`, `depth`, `exponent` and their derived values: total levels, nodes, deciders, voters and nodes per level. |
| 3 | Resources | RAM (with breakdown and headroom), weights on disk, CPU per inference, vCPU for the target latency, estimated latency and recommended container (with its `docker run`), or a cluster if it does not fit in one. |
| 4 | Terminal / logs | Command line and message history. |

## Tree model

- **levels (L)**: levels of the base tree, counting the root.
- **depth (D)**: children per node (nodes per level are multiplied by D).
- **exponent (E)**: times the base tree is applied on its own leaves (fractal
  self-similarity).

Total levels = `(L-1)*E + 1`; level `k` (from 0) has `D^k` nodes.
Example `L=3 D=3 E=2`: 5 levels with 1, 3, 9, 27 and 81 nodes (121 models:
81 deciders and 40 voters). Calculations use 64-bit saturated arithmetic, so
extreme values are shown as `>1.8E` and never overflow.

## Keyboard

| Key | Action |
|-----|--------|
| `Tab` / `Shift-Tab`, `1`-`4` | Switch panel |
| `z` | Maximize or restore the active panel |
| `g` / `h` / `q` | Generate the report / help / quit |
| `:` | Go to the terminal (`Esc` returns to the previous panel) |
| Fractal: `↑` `↓` `Home` `End` | Scroll the displayed levels |
| Parameters: `↑` `↓` | Select the parameter |
| Parameters: `←` `→` or `-` `+` | Change its value |
| Parameters: `Enter` | Types `set <field> ` in the terminal |
| Terminal: `PgUp` `PgDn` `↑` `↓` | Scroll the logs |

## Commands

```
help                      help
generate | gen            report of the current schema
stats                     nodes per level
set <field> <n>           '<field> <n>' also works (e.g. 'depth 4')
profile [field n]         show or change the model profile
reset | clear | quit
focus <1-4> | zoom [1-4|off] | scroll <level>
```

Tree fields: `levels`, `depth`, `exponent`.

## Resource estimation

Based on a model profile editable with `profile <field> <n>`:

| Field | Default | Meaning |
|-------|---------|---------|
| `runtime_mib` | 512 | Base memory of the TensorFlow runtime |
| `leaf_mib` / `voter_mib` | 48 / 6 | RAM per decider / voter model |
| `disk_pct` | 40 | Size of the weights on disk, as % of the models' RAM |
| `leaf_us` / `voter_us` | 5000 / 200 | CPU per inference / vote |
| `target_ms` | 250 | Target latency, used to compute the vCPUs |
| `headroom_pct` | 25 | RAM headroom over the total |

The chosen container is the smallest one in the `src/container.c` table
(micro 1/1 GiB … 8xlarge 96 vCPU/384 GiB) that covers the RAM with headroom
and the vCPUs. If none is enough, a cluster of 8xlarge is proposed. These are
rough estimates, not real TensorFlow measurements.

## Structure and rules

```text
include/  headers per module (tree, cost, field, format, app, ui, view, command)
src/      tree*, cost/container   -> calculation
          fractal_*               -> tree rendering
          ui_*                    -> panels
          input*, command*        -> keyboard and terminal
```

All the code follows 42's Norminette 3 (`norminette src include`): 42 header,
at most 25 lines and 4 parameters per function, 5 variables per function and
5 functions per file, no `for`, `switch` or ternaries.
