# Post-M18 Integrated Technical Roadmap

## Current Position

After `M18`, the repository now ships:

- local-first runtime semantics with repository-owned truth
- bounded repo-mutation contracts and semi-automatic workflow-driven development
- single-control-plane remote worker productization
- built-in Web operator UI
- formal `project_delivery` orchestration
- a centralized scheduler-authority first slice for multi-control-plane proposal and lease provenance

## What Remains Open

The primary remaining structural debt is now narrower:

- `TD-021` - a centralized scheduler-authority first slice now exists, but true distributed scheduler consensus, multi-authority failover, and final cross-control-plane lease ownership remain incomplete

## Recommended Next Cycle

`M19` should begin with a post-`M18` rebaseline and decide how to stage the next breadth:

1. deepen scheduler consensus beyond the centralized authority first slice
2. expand workflow self-hosting autonomy on top of the new repo-mutation baseline
3. decide whether any ecosystem or multimodal expansion is justified after the scheduler/autonomy gate

## Route Synthesis

The best route after `M18` is to preserve the current repository as the canonical control plane, keep the centralized scheduler authority as an honest first slice, and use `M19` to choose between:

- deeper multi-authority scheduler consensus
- stronger workflow self-bootstrapping autonomy
- or a later selective ecosystem expansion once those two foundations are stable
