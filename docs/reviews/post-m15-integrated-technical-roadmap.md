# Post-M15 Integrated Technical Roadmap

## Current Position

After `M15`, the repository now ships:

- local-first control-plane runtime semantics
- ownership topology and local batch concurrency
- external worker-pool boundaries plus real remote HTTP worker productization
- durable/config/trace baselines
- formal multi-agent orchestration baseline
- full built-in Web operator UI and human control surface

## What Remains Deferred

The major remaining structural debt is now narrower:

- `TD-021` - multi-control-plane arbitration and distributed scheduler consensus remain deferred beyond the shipped single-control-plane remote worker productization

## Recommended Next Cycle

`M16` should begin with a post-`M15` rebaseline and answer three questions before new breadth starts:

1. does the repository need true multi-control-plane scheduling now, or can the single-control-plane model remain the canonical production posture?
2. should multimodal/provider expansion be staged after distributed consensus, or remain behind the scheduler/productization gate?
3. which hosted/deployment concerns belong in the next cycle versus a later product-expansion cycle?

## Route Synthesis

The optimal route after `M15` is to keep the repository centered on the shipped single-control-plane control plane, treat the Web operator surface and remote worker productization as complete, and use `M16` to decide whether the next breadth is:

- true distributed scheduler consensus
- hosted deployment hardening
- or selective ecosystem expansion on top of the newly stable product surface
