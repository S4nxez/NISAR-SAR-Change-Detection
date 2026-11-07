# How to read the groundwater irrigation footprint map

> Draft. Completed in plan phases 5 (classification) and 8 (web help). NISAR data is **provisional** until the
> validated reprocessing (expected late 2026): results may change.

Each 500 m hexagon in the Tule and Tulare Lake subbasins gets a class and a confidence level. The map shows where
groundwater pumping for irrigation is **probable**; it does not detect wells, and it does not say that any pumping is
illegal.

## Classes

| Class | Name | What it means | What it does not mean |
| --- | --- | --- | --- |
| A | Probable active pumping | Excess subsidence in summer 2026 over the long-term trend, high evapotranspiration, little surface water available | A confirmed well or an unreported extraction |
| B | Inherited compaction | Significant long-term subsidence (DWR), no excess in 2026 | That there is no pumping today |
| C | Probable surface-water irrigation | High evapotranspiration, no significant deformation, inside a district with deliveries | That no groundwater is used |
| D | Recharge or uplift | Significant ground uplift | Absence of pumping |
| — | No signal or low confidence | None of the above, or not enough data | Absence of irrigation |

Thresholds are decided with the team in phase 5 and recorded in an ADR.

## Confidence

Depends on the fraction of coherent pixels, the number of valid acquisitions and the agreement with nearby GNSS and DWR
data. Each cell stores which indicators classified it.

## Known false positives and negatives

To be filled in as the residual risks of the plan are quantified: inherited clay compaction (1), surface water (2),
oil fields (3), artificial recharge (4), 12-day pairs and the 27 Jul – 10 Aug 2026 data gap (5), short series (6),
atmosphere (7), soil moisture phase (8), line of sight vs vertical (9), resolution (10), provisional data (11).
