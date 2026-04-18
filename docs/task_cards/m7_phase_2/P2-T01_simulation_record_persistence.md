# P2-T01 - Simulation Record Persistence

## Goal

Persist simulation reports as explicit local records with event lineage.

## Scope

- `SimulationRecord` contract
- SQLite table + repository
- `simulation_recorded` event

## Done When

- a persisted simulation record can round-trip and list by run
- recording a simulation produces a timeline event
