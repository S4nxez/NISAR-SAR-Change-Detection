# River monitor: results of exam 3

Latest run: `v3-darkest-sentinel1`, 2026-11-13, commit `7a3d95e`, exam version 3. The full report is
[processing/benchmark/history/20261113T192855Z_v3-darkest-sentinel1.md](../processing/benchmark/history/20261113T192855Z_v3-darkest-sentinel1.md);
the method is in [ADR-007](decisions/ADR-007-river-monitor-low-water-beds.md) and the exam in
[river-monitor-benchmark.md](river-monitor-benchmark.md).

Exam 3 scores NISAR against the two optical references (Sentinel-2 and OPERA DSWx-HLS). Sentinel-1 is part of the
method, so it is not a reference: it is checked against NISAR in a section that is not scored. Exam 3 numbers are
not comparable with exam 2.

## Main results

The first exam 3 run (`v3-sentinel1-mud-veto`) used the closest Sentinel-1 scene. The latest one takes the darkest
of the usable scenes on each pixel, after the manual review found that wind on open water made Sentinel-1 read it
as land.

| Metric | First run (closest scene) | Latest run (darkest scene) | Meaning |
|---|---|---|---|
| Water IoU vs consensus | 0.929 | 0.929 | agreement of the NISAR water mask with the optical references |
| Recall of channels < 60 m | 0.388 | 0.388 | share of narrow reference channels mapped as water |
| Status agreement | 0.961 | 0.957 | community status equal to the one from the reference water (463 decided pairs) |
| False routes | 0 | 1 | route shown that the reference does not have: the dangerous error |
| Confirmed false routes | – | 0 | false routes a person confirmed |
| False isolated | 15 | 14 | shown isolated while the reference links it |
| Undecided pairs | 47 | 47 | the references disagree, not scored |
| Cases to review | 1 | 2 (1 place) | disagreements a person has to check |
| Gauge rho (lost routes vs level) | −0.759 | −0.757 | more negative: routes are lost as the river falls |
| Field checks | 1.000 | 1.000 | known places the record gets right |
| NISAR / Sentinel-1 agreement | 0.983 | 0.985 | share of pixels both radars judged on which they agree (not scored) |
| NISAR / Sentinel-1 status cases | 227 | 170 | community-pass pairs where the two radars disagree (not scored) |
| NISAR / Sentinel-1 places | 67 | 62 | places those cases come from |

Per pass, latest run:

| Pass | Sentinel-2 | River change (cm) | IoU | Status agreement | False routes | Cases | Sentinel-1 scenes | Radar agreement | Radar status cases |
|---|---|---|---|---|---|---|---|---|---|
| 2025-11-04_t097D | 2025-11-05 | −7 | 0.924 | 1.000 | 0 | 0 | 2025-11-04 | 0.966 | 88 |
| 2026-07-07_t161A | 2026-07-06 | −2 | 0.956 | 1.000 | 0 | 0 | 2026-07-09 | 0.986 | 58 |
| 2026-08-19_t097D | 2026-08-20 | +17.5 | 0.948 | 0.868 | 0 | 12 | – | – | – |
| 2026-08-24_t161A | 2026-08-25 | +14.5 | 0.943 | 0.990 | 0 | 1 | 2026-08-26 | 0.992 | 7 |
| 2026-08-31_t097D | 2026-08-30 | −23 | 0.935 | 0.975 | 0 | 4 | 2026-09-02 | 0.993 | 1 |
| 2026-10-11_t161A | 2026-10-11 | 0 | 0.899 | 0.919 | 1 | 3 | 2026-10-13, 2026-10-08 | 0.989 | 5 |
| 2026-10-23_t161A | 2026-10-21 | −14 | 0.836 | 1.000 | 0 | 0 | 2026-10-25, 2026-10-20 | 0.983 | 11 |

The scored false isolated are mostly the ten communities behind one narrow channel near Caiambé on 2026-08-19
(the reference sees a channel under 60 m, at risk; NISAR sees it cut) and Jaguarí, where the river changed between
the pass and the reference.

## What the synthetic scenes saw

Ten simulated lanes, five speckle draws each, processed by the real pipeline (40 correct, 5 conservative, 5
dangerous; the same in both runs):

| Lane | Expected | Result |
|---|---|---|
| `channel_20m`, `channel_40m` | narrow (at risk or isolated) | correct 5/5 |
| `channel_60m`, `channel_100m`, `channel_200m`, `channel_400m`, `zigzag_100m` | connected | correct 5/5 |
| `vegetation_block` | isolated | correct 5/5 |
| `mud_bar` | isolated | **dangerous 5/5**: smooth wet mud (−17 dB HH) is mapped as water and the route is shown |
| `wind_stretch` | connected | conservative 5/5: wind-roughened water (−13 dB HH) is mapped as land |

Sentinel-1 plays no part in the synthetic scenes. They simulate NISAR only, and they have no gauge, so the
low-water rule is off. The `mud_bar` lane shows the L-band failure that ADR-007 handles on the real record with
Sentinel-1. Until the latest change, the synthetic run still searched for real Sentinel-1 scenes over the place of the
simulated lanes. The scenes changed no result, and the synthetic area no longer reads Sentinel-1.

## What the latest manual review saw (2026-11-13)

The project lead checked the case of the first run and six NISAR / Sentinel-1 places on the 10 m Sentinel-1 and the
Sentinel-2 images (`processing/benchmark/reviews.json`, `processing/benchmark/crosscheck_reviews.json`):

| Place | Zone (report) | Seen on the images | Verdict |
|---|---|---|---|
| Nova Esperança, 2026-10-11 (exam case) | `sentinel1_mud` | Route clear on Sentinel-1 and Sentinel-2; the point is a small bright patch next to the water | reference right: the mud veto was wrong |
| 1. São Jorge | `narrow_channel` | Channel over 100 m wide on Sentinel-1; a Sentinel-2 cloud cuts it at that point | NISAR right |
| 2. Itapiranema (Santa Luzia do Catuiri, Vila Sião) | `shore_mixed_pixel` | Sentinel-2 clouds cut the link to Lake Tefé; Sentinel-1 shows it over 100 m wide | NISAR right |
| 3. São Jose | `narrow_channel` | The point lies by the Solimões, over 1 km wide; by Jaquiri a 40 m side channel | NISAR right |
| 4. Itapiranema, in the lake | `unexplained` → `wind_roughness` | Open water far from the shore | NISAR right |
| 5. Santa Rosa do Repartimento | `narrow_channel` | Sentinel-2 all cloud; Sentinel-1 scene cut there (scene edge); channel at least 100 m wide | NISAR right |
| 17. Cauaçu de Baixo | `narrow_channel` | Link over 100 m wide on Sentinel-1; a Sentinel-2 cloud cuts it | NISAR right |

What it changed:

- **Wind.** C band is much more sensitive to wind than L band. Lake Tefé read −15.4 to −15.6 dB VV on windy scenes,
  above the −16 dB land threshold, and −20 dB on calm ones. The view of a pass now keeps the darkest usable scene on
  each pixel: a drained bed is bright on every date, wind lasts a day or two. The river level tolerance (30 cm) now
  applies both ways.
- **Effect.** The confirmed false routes stay cut. Nova Esperança on 2026-10-11 goes from isolated to at risk; the
  person saw it connected, so the remaining error is on the safe side. The radar status cases on 2026-10-11 fall from
  40 to 5.
- **Weights by zone type.** The verdicts so far are 78 to 0 for NISAR in narrow channels, 15 to 0 on mixed shore
  pixels and 13 to 0 on wind. Sentinel-1 is not trusted more in narrow channels. Its "land" counts only on seasonal
  ground at low water, and only when every scene agrees.

## Pending

- One place to review: Nova Jerusalem on 2026-10-11. Canaman is at risk and São Jose do Madureira is connected,
  while the reference, under a cloud edge, cuts them off. Both were cut on 2026-10-23, but the river was 1.3 m
  higher on the 11th.
- 32 NISAR / Sentinel-1 places without a verdict (13 narrow channel, 11 mixed shore pixel, 22 unexplained, 17
  threshold and 1 smooth ground cases).
