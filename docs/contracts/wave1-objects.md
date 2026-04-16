# Wave 1 Objects

## Canonical rule

For M0, `universal_agentic_workflow_os_M0_task_breakdown_v2_1.md` remains the source of truth for fields and acceptance criteria. This document freezes object responsibility and usage boundaries.

## Run

- Serves:
  Operator and orchestrator service.
- Purpose:
  Represents the lifecycle container for one goal executed with one preset.
- Must not:
  Carry worker execution details or replace timeline.

## Phase

- Serves:
  Orchestrator service and future multi-stage flow.
- Purpose:
  Tracks the coarse stage boundary inside a run.
- Must not:
  Become a generic storage bucket for unrelated runtime details.

## TaskCard

- Serves:
  Humans and planner-facing logic.
- Purpose:
  Holds the readable task intent and acceptance criteria.
- Must not:
  Act as the worker execution contract.

## RuntimeTask

- Serves:
  Orchestrator, runtime, repositories, and CLI status views.
- Purpose:
  Represents the executable task instance selected for runtime handling.
- Must not:
  Replace `TaskPacket` or absorb evidence.

## TaskPacket

- Serves:
  Worker adapter and compile output.
- Purpose:
  Captures the concrete execution payload used by a worker.
- Must not:
  Become a long-lived business truth record.

## Evidence

- Serves:
  Review logic, timeline, and operator debugging.
- Purpose:
  Records machine-readable execution truth derived from a runtime result.
- Must not:
  Be reduced to plain stdout or act as the review decision itself.

## ReviewVerdict

- Serves:
  Quality and operator decision surfaces.
- Purpose:
  Stores the review conclusion linked to a piece of evidence.
- Must not:
  Embed the full execution transcript or replace evidence.

## PresetDefinition

- Serves:
  Run creation and compile defaults.
- Purpose:
  Defines the allowed task kinds, review policy, and budget policy for a preset.
- Must not:
  Become an inferred planner result in M0.

## HandoffLite

- Serves:
  Future cross-phase handoff semantics.
- Purpose:
  Freezes the minimum handoff contract and risks summary.
- Must not:
  Enter the first persistence batch or the M0 smoke critical path.

## Core relationships

- `Run -> Phase`
- `Run -> TaskCard`
- `Run -> RuntimeTask`
- `RuntimeTask -> TaskPacket`
- `RuntimeTask -> Evidence -> ReviewVerdict`
- `Run / Phase -> HandoffLite`
