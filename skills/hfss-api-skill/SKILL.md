---
name: hfss-pyaedt
description: Automate ANSYS HFSS tasks on Windows through PyAEDT. Use when Codex needs to inspect the local HFSS environment, create or modify HFSS projects, set design variables, build simple geometry, create setups and sweeps, run analyses, or export Touchstone results from `.aedt` projects.
---

# HFSS PyAEDT

## Overview

Use this skill to perform scripted HFSS work through local PyAEDT instead of hand-driving the HFSS GUI. Prefer it for repeatable setup, small geometry automation, environment diagnostics, and simple simulation-to-export workflows.

This skill currently ships one stable entrypoint: [scripts/hfss_workflow.py](./scripts/hfss_workflow.py). Start with `doctor`, then use `new-box-project` or `analyze-project`.

## Workflow

1. Run the environment check before touching HFSS:
   `py -3.14 scripts/hfss_workflow.py doctor`
2. Read [references/local-environment.md](./references/local-environment.md) if version or Python path discovery matters.
3. For a brand new automation smoke test, create a minimal project with `new-box-project`.
4. For an existing `.aedt` project, use `analyze-project` to set variables, rerun a setup, and optionally export Touchstone.
5. Save outputs outside the repository when they are large or binary-heavy.

## Command Guide

### Doctor

Use this first. It does not launch HFSS. It reports Python, PyAEDT, and detected AEDT install directories.

```powershell
py -3.14 scripts/hfss_workflow.py doctor
```

Use `--json` when another tool or script should consume the output.

### Create A Minimal Project

Use this for the first smoke test on a machine or when you need a tiny deterministic HFSS project.

```powershell
py -3.14 scripts/hfss_workflow.py new-box-project `
  --project C:\temp\hfss\demo_box.aedt `
  --design HFSSDesign1 `
  --solution-type DrivenModal `
  --origin 0mm,0mm,0mm `
  --size 10mm,10mm,1mm `
  --create-open-region `
  --setup-name Setup1 `
  --setup-frequency 10GHz `
  --sweep-name Sweep1 `
  --sweep-start 8 `
  --sweep-stop 12 `
  --sweep-count 401
```

Notes:

- `--set-variable NAME=VALUE` is repeatable.
- `--non-graphical` is available, but prefer graphical mode until local licensing is proven stable.
- The first version only creates one box. Extend the script rather than improvising repeated fragile GUI operations.

### Analyze An Existing Project

Use this to reopen a saved `.aedt` project, update variables, rerun a setup, and optionally export Touchstone.

```powershell
py -3.14 scripts/hfss_workflow.py analyze-project `
  --project C:\temp\hfss\demo_box.aedt `
  --design HFSSDesign1 `
  --setup-name Setup1 `
  --sweep-name Sweep1 `
  --set-variable L=12mm `
  --export-touchstone C:\temp\hfss\demo_box.s2p
```

## Working Rules

- Prefer explicit file paths for `.aedt` outputs and exported `.sNp` files.
- Treat PyAEDT API behavior as version-sensitive. If a method fails, inspect the current method signature before patching.
- Keep first-pass automations narrow and verifiable. Add one new HFSS operation at a time.
- When a user asks for metasurface or antenna-specific flows, extend the script or add a new one rather than overloading prompts with unchecked assumptions.
- If HFSS launch or solve fails, rerun `doctor`, confirm installed AEDT paths, and capture the exact error.

## References

- [references/workflow-recipes.md](./references/workflow-recipes.md): command examples and Codex prompt patterns
- [references/local-environment.md](./references/local-environment.md): local AEDT and Python findings recorded during skill creation
