# HFSS PyAEDT Recipes

Use this file when the user wants concrete HFSS automation prompts or command shapes.

## Quick Checks

- Environment doctor:
  `py -3.14 scripts/hfss_workflow.py doctor`
- JSON doctor output:
  `py -3.14 scripts/hfss_workflow.py doctor --json`

## Create A Minimal Project

Create a small `DrivenModal` project with one vacuum box, one setup, and one sweep:

```powershell
py -3.14 scripts/hfss_workflow.py new-box-project `
  --project C:\temp\hfss\demo_box.aedt `
  --design HFSSDesign1 `
  --solution-type DrivenModal `
  --origin 0mm,0mm,0mm `
  --size 10mm,10mm,1mm `
  --box-name Substrate `
  --material vacuum `
  --create-open-region `
  --open-region-frequency 10GHz `
  --setup-name Setup1 `
  --setup-frequency 10GHz `
  --sweep-name Sweep1 `
  --sweep-start 8 `
  --sweep-stop 12 `
  --sweep-count 401
```

## Re-Analyze An Existing Project

```powershell
py -3.14 scripts/hfss_workflow.py analyze-project `
  --project C:\temp\hfss\demo_box.aedt `
  --design HFSSDesign1 `
  --setup-name Setup1 `
  --sweep-name Sweep1 `
  --set-variable L=12mm `
  --set-variable W=6mm `
  --export-touchstone C:\temp\hfss\demo_box.s2p
```

## Prompt Patterns For Codex

- `Use $hfss-pyaedt to diagnose whether PyAEDT and AEDT are ready on this Windows machine.`
- `Use $hfss-pyaedt to create a minimal HFSS DrivenModal project at C:\temp\hfss\demo.aedt with a 10 mm by 10 mm by 1 mm box and a 10 GHz setup.`
- `Use $hfss-pyaedt to reopen this HFSS project, set L=12mm and W=6mm, rerun Setup1, and export Touchstone data.`
