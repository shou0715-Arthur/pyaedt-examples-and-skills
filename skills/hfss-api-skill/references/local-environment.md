# Local Environment Checklist

Use this file when local machine setup matters.

## Expected Baseline

- OS: Windows
- Local AEDT or HFSS installation
- Working Python launcher such as `py`
- PyAEDT installed in the interpreter used by the skill

## Quick Checks

- Confirm PyAEDT import:
  `py -3.14 -c "import ansys.aedt.core; print(ansys.aedt.core.__version__)"`
- Confirm the skill can inspect the environment:
  `py -3.14 scripts/hfss_workflow.py doctor`
- Confirm local AEDT install folders exist under one of these common roots:
  - `C:\Program Files\AnsysEM`
  - `C:\Program Files\ANSYS Inc`

## Implications

- Prefer an explicit Python launcher such as `py -3.14` when running bundled scripts.
- Confirm licensing and GUI launch behavior before adding fragile high-level workflows such as batch parametric sweeps, report export, or large optimization loops.
- If a different Python version is the active PyAEDT environment, use that interpreter consistently for all skill commands.
