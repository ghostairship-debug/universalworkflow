# P3-T01 - Simulation Record Sources

## Goal

Add an explicit source model so simulation history can distinguish manual requests from automatic lifecycle hooks.

## Scope

- add explicit simulation-record source values
- use those values in `SimulationRecord`
- extend `simulation_recorded` payload shape accordingly

## Done When

- simulation records round-trip with explicit source values
- event payload validation accepts the new `recorded_from` field
