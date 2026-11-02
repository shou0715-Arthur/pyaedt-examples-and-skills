#!/usr/bin/env python3
"""
Minimal HFSS automation entrypoint for the hfss-pyaedt skill.

This script favors a small number of stable workflows over broad coverage:
1. doctor            - inspect local PyAEDT and AEDT availability
2. new-box-project   - create a minimal HFSS project with one box and setup
3. analyze-project   - open an existing project, update variables, analyze, export Touchstone
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from pathlib import Path
from typing import Iterable


def _require_pyaedt():
    try:
        from ansys.aedt.core import Hfss  # type: ignore
    except Exception as exc:  # pragma: no cover - import failure path is user-facing
        raise RuntimeError(
            "PyAEDT is not importable. Install it with `py -3.14 -m pip install pyaedt` "
            "and confirm that AEDT/HFSS is installed locally."
        ) from exc
    return Hfss


def _parse_triplet(raw: str) -> list[str]:
    parts = [item.strip() for item in raw.split(",")]
    if len(parts) != 3 or any(not item for item in parts):
        raise argparse.ArgumentTypeError(
            f"Expected three comma-separated values, got: {raw!r}"
        )
    return parts


def _parse_variable_overrides(items: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(
                f"Variable override {item!r} is invalid. Use NAME=VALUE, for example L=10mm."
            )
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            raise ValueError(
                f"Variable override {item!r} is invalid. Use NAME=VALUE, for example L=10mm."
            )
        result[name] = value
    return result


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _find_aedt_installs() -> list[str]:
    roots = [
        Path(r"C:\Program Files\AnsysEM"),
        Path(r"C:\Program Files\ANSYS Inc"),
    ]
    found: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir():
                found.append(str(child))
    return found


def cmd_doctor(args: argparse.Namespace) -> int:
    data: dict[str, object] = {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": os.getcwd(),
        "aedt_install_dirs": _find_aedt_installs(),
    }
    try:
        import ansys.aedt.core  # type: ignore

        data["pyaedt_version"] = getattr(ansys.aedt.core, "__version__", "unknown")
        data["pyaedt_import"] = True
    except Exception as exc:
        data["pyaedt_import"] = False
        data["pyaedt_error"] = str(exc)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print("HFSS PyAEDT Doctor")
        for key, value in data.items():
            print(f"- {key}: {value}")
    return 0


def _build_hfss_context(args: argparse.Namespace):
    Hfss = _require_pyaedt()
    return Hfss(
        project=args.project,
        design=args.design,
        solution_type=args.solution_type,
        version=args.version,
        non_graphical=args.non_graphical,
        new_desktop=True,
        close_on_exit=True,
    )


def cmd_new_box_project(args: argparse.Namespace) -> int:
    project_path = Path(args.project).expanduser().resolve()
    _ensure_parent_dir(project_path)

    variable_overrides = _parse_variable_overrides(args.set_variable)

    with _build_hfss_context(args) as hfss:
        for name, value in variable_overrides.items():
            hfss[name] = value

        box = hfss.modeler.create_box(
            origin=args.origin,
            sizes=args.size,
            name=args.box_name,
            material=args.material,
        )
        if not box:
            raise RuntimeError("Failed to create the box geometry.")

        if args.create_open_region:
            hfss.create_open_region(args.open_region_frequency)

        setup = hfss.create_setup(name=args.setup_name)
        setup.props["Frequency"] = args.setup_frequency
        setup.update()

        if args.sweep_name:
            hfss.create_linear_count_sweep(
                setup=args.setup_name,
                name=args.sweep_name,
                units=args.sweep_units,
                start_frequency=args.sweep_start,
                stop_frequency=args.sweep_stop,
                num_of_freq_points=args.sweep_count,
            )

        saved = hfss.save_project(file_name=str(project_path), overwrite=True)
        if not saved:
            raise RuntimeError(f"Failed to save project to {project_path}")

    print(f"Created HFSS project: {project_path}")
    return 0


def cmd_analyze_project(args: argparse.Namespace) -> int:
    project_path = Path(args.project).expanduser().resolve()
    if not project_path.exists():
        raise FileNotFoundError(f"Project file does not exist: {project_path}")

    variable_overrides = _parse_variable_overrides(args.set_variable)

    with _build_hfss_context(args) as hfss:
        for name, value in variable_overrides.items():
            hfss[name] = value

        if args.setup_name:
            success = hfss.analyze(setup=args.setup_name)
        else:
            success = hfss.analyze()
        if not success:
            raise RuntimeError("HFSS analyze() returned False.")

        exported_file = None
        if args.export_touchstone:
            output_path = Path(args.export_touchstone).expanduser().resolve()
            _ensure_parent_dir(output_path)
            exported_file = hfss.export_touchstone(
                setup=args.setup_name,
                sweep=args.sweep_name,
                output_file=str(output_path),
            )
            if not exported_file:
                raise RuntimeError(f"Touchstone export failed: {output_path}")

        saved = hfss.save_project(file_name=str(project_path), overwrite=True)
        if not saved:
            raise RuntimeError(f"Failed to save project to {project_path}")

    print(f"Analyzed project: {project_path}")
    if exported_file:
        print(f"Exported Touchstone: {exported_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HFSS workflows built on PyAEDT for Codex skill automation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor", help="Inspect Python, PyAEDT, and local AEDT installation paths."
    )
    doctor.add_argument("--json", action="store_true", help="Print JSON output.")
    doctor.set_defaults(func=cmd_doctor)

    new_box = subparsers.add_parser(
        "new-box-project",
        help="Create a minimal HFSS project with one box, one setup, and an optional sweep.",
    )
    new_box.add_argument("--project", required=True, help="Output .aedt file path.")
    new_box.add_argument("--design", default="HFSSDesign1", help="Design name.")
    new_box.add_argument(
        "--solution-type",
        default="DrivenModal",
        help="HFSS solution type, for example DrivenModal or Terminal.",
    )
    new_box.add_argument("--version", default=None, help="AEDT version such as 2023.1.")
    new_box.add_argument(
        "--non-graphical",
        action="store_true",
        help="Launch AEDT in non-graphical mode.",
    )
    new_box.add_argument(
        "--set-variable",
        action="append",
        default=[],
        help="Repeatable NAME=VALUE variable assignment.",
    )
    new_box.add_argument(
        "--origin",
        type=_parse_triplet,
        default=["0mm", "0mm", "0mm"],
        help="Box origin as x,y,z.",
    )
    new_box.add_argument(
        "--size",
        type=_parse_triplet,
        default=["10mm", "10mm", "1mm"],
        help="Box size as sx,sy,sz.",
    )
    new_box.add_argument("--box-name", default="Box1", help="Geometry object name.")
    new_box.add_argument("--material", default="vacuum", help="Material name.")
    new_box.add_argument(
        "--create-open-region",
        action="store_true",
        help="Create an open region after the box is created.",
    )
    new_box.add_argument(
        "--open-region-frequency",
        default="10GHz",
        help="Frequency used for create_open_region.",
    )
    new_box.add_argument("--setup-name", default="Setup1", help="Setup name.")
    new_box.add_argument(
        "--setup-frequency",
        default="10GHz",
        help="Adaptive setup frequency.",
    )
    new_box.add_argument(
        "--sweep-name",
        default=None,
        help="Optional sweep name. Omit to skip sweep creation.",
    )
    new_box.add_argument("--sweep-units", default="GHz", help="Sweep frequency units.")
    new_box.add_argument("--sweep-start", type=float, default=8.0, help="Sweep start.")
    new_box.add_argument("--sweep-stop", type=float, default=12.0, help="Sweep stop.")
    new_box.add_argument(
        "--sweep-count", type=int, default=401, help="Number of sweep points."
    )
    new_box.set_defaults(func=cmd_new_box_project)

    analyze = subparsers.add_parser(
        "analyze-project",
        help="Open an existing project, optionally set variables, analyze, and export Touchstone.",
    )
    analyze.add_argument("--project", required=True, help="Existing .aedt file path.")
    analyze.add_argument("--design", default=None, help="Design name to open.")
    analyze.add_argument(
        "--solution-type",
        default=None,
        help="Optional HFSS solution type override.",
    )
    analyze.add_argument("--version", default=None, help="AEDT version such as 2023.1.")
    analyze.add_argument(
        "--non-graphical",
        action="store_true",
        help="Launch AEDT in non-graphical mode.",
    )
    analyze.add_argument(
        "--set-variable",
        action="append",
        default=[],
        help="Repeatable NAME=VALUE variable assignment before solve.",
    )
    analyze.add_argument(
        "--setup-name",
        default=None,
        help="Setup to analyze. Omit to use HFSS default behavior.",
    )
    analyze.add_argument(
        "--sweep-name",
        default=None,
        help="Sweep name for Touchstone export.",
    )
    analyze.add_argument(
        "--export-touchstone",
        default=None,
        help="Output .sNp file path. Omit to skip export.",
    )
    analyze.set_defaults(func=cmd_analyze_project)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args) or 0)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
