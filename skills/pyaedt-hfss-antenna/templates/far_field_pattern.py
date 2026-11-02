"""
模板:远场方向图 / 增益 / 辐射效率
========================================
适用:已经有跑过求解的工程(或下面 SOLVE_FIRST=True 自动跑),
     提取远场方向图(2D 切面 + 3D 增益)、最大增益、辐射效率,
     并导出 PNG / CSV。

用法:
    1) 改下方 USER CONFIG
    2) python far_field_pattern.py

依赖:
    pip install "pyaedt[all]" numpy matplotlib
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from ansys.aedt.core import Hfss

# ============================ USER CONFIG ============================
PROJECT_PATH  = r"D:\sim\patch_2p4G.aedt"
DESIGN_NAME   = "Patch_2p4G"
AEDT_VERSION  = "2025.2"

SETUP_NAME    = "Setup1"
SWEEP_NAME    = "SweepInterp"
TARGET_FREQ   = "2.45GHz"            # 取哪个频点的方向图

INFINITE_SPHERE_NAME = "FF_Sphere"
THETA_RANGE   = (0, 180, 2)           # start, stop, step (deg)
PHI_RANGE     = (-180, 180, 2)

EXPORT_DIR    = Path(PROJECT_PATH).parent / "out_ff"

SOLVE_FIRST   = False                 # True 表示先求解再后处理
CORES         = 8
NON_GRAPHICAL = True
# ============================ /USER CONFIG ===========================


def ensure_infinite_sphere(hfss: Hfss):
    if any(s.name == INFINITE_SPHERE_NAME for s in hfss.field_setups):
        return
    hfss.insert_infinite_sphere(
        definition="Theta-Phi",
        x_start=THETA_RANGE[0], x_stop=THETA_RANGE[1], x_step=THETA_RANGE[2],
        y_start=PHI_RANGE[0],  y_stop=PHI_RANGE[1],   y_step=PHI_RANGE[2],
        name=INFINITE_SPHERE_NAME,
    )


def plot_polar(theta_deg: np.ndarray, gain_db: np.ndarray, title: str,
               out_path: Path) -> None:
    fig = plt.figure(figsize=(5, 5))
    ax = fig.add_subplot(111, projection="polar")
    ax.plot(np.deg2rad(theta_deg), gain_db, lw=1.6)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_rlabel_position(135)
    ax.set_title(title)
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160)
    plt.close(fig)


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    hfss = Hfss(
        project=PROJECT_PATH,
        design=DESIGN_NAME,
        version=AEDT_VERSION,
        non_graphical=NON_GRAPHICAL,
        new_desktop=False,
        close_on_exit=False,
    )

    try:
        ensure_infinite_sphere(hfss)

        if SOLVE_FIRST:
            print(f"[run] solving {SETUP_NAME}/{SWEEP_NAME} ...")
            hfss.analyze(setup=SETUP_NAME, cores=CORES, use_auto_settings=True)

        sweep_label = f"{SETUP_NAME} : {SWEEP_NAME}"

        # === 1) 取 phi=0 切面增益(E-plane,通常) ===
        ff_e = hfss.post.get_far_field_data(
            expressions=["GainTotal"],
            setup_sweep_name=sweep_label,
            domain=INFINITE_SPHERE_NAME,
            variations={"Freq": [TARGET_FREQ], "Phi": ["0deg"]},
        )
        if ff_e is None:
            raise RuntimeError("E-plane far-field 取数据失败,检查 setup/sphere/freq")

        theta_e = np.array(ff_e.primary_sweep_values, dtype=float)         # deg
        g_e_lin = np.array(ff_e.data_real("GainTotal"), dtype=float)
        g_e_db = 10.0 * np.log10(np.maximum(g_e_lin, 1e-12))

        plot_polar(
            theta_e, g_e_db,
            title=f"E-plane gain @ {TARGET_FREQ}, phi=0",
            out_path=EXPORT_DIR / "ff_eplane.png",
        )
        np.savetxt(EXPORT_DIR / "ff_eplane.csv",
                   np.column_stack([theta_e, g_e_db]),
                   header="theta_deg, gain_dBi", delimiter=",")

        # === 2) 取 phi=90 切面 (H-plane) ===
        ff_h = hfss.post.get_far_field_data(
            expressions=["GainTotal"],
            setup_sweep_name=sweep_label,
            domain=INFINITE_SPHERE_NAME,
            variations={"Freq": [TARGET_FREQ], "Phi": ["90deg"]},
        )
        theta_h = np.array(ff_h.primary_sweep_values, dtype=float)
        g_h_lin = np.array(ff_h.data_real("GainTotal"), dtype=float)
        g_h_db = 10.0 * np.log10(np.maximum(g_h_lin, 1e-12))

        plot_polar(
            theta_h, g_h_db,
            title=f"H-plane gain @ {TARGET_FREQ}, phi=90",
            out_path=EXPORT_DIR / "ff_hplane.png",
        )

        # === 3) 关键标量 ===
        peak_gain_db = float(max(g_e_db.max(), g_h_db.max()))

        eff_data = hfss.post.get_solution_data(
            expressions=["RadiationEfficiency", "TotalEfficiency"],
            setup_sweep_name=sweep_label,
            domain="Sweep",
            primary_sweep_variable="Freq",
            variations={"Freq": [TARGET_FREQ]},
        )
        rad_eff = float(eff_data.data_real("RadiationEfficiency")[0]) if eff_data else float("nan")
        tot_eff = float(eff_data.data_real("TotalEfficiency")[0]) if eff_data else float("nan")

        print("\n=== Far-field metrics ===")
        print(f"  peak gain      : {peak_gain_db:.2f} dBi")
        print(f"  rad efficiency : {rad_eff:.3f}  ({rad_eff*100:.1f} %)")
        print(f"  tot efficiency : {tot_eff:.3f}  ({tot_eff*100:.1f} %)")
        print(f"  outputs in     : {EXPORT_DIR}")

        # === 4) 3D 方向图导出(可选,在 GUI 才看得到的话用 export_image) ===
        try:
            hfss.post.create_3d_plot(
                plot_name="Gain3D",
                solution=hfss.nominal_adaptive,
                quantity_name="GainTotal",
                primary_sweep="Phi",
                secondary_sweep="Theta",
            )
            hfss.post.export_field_jpg(
                file_name=str(EXPORT_DIR / "gain_3d.jpg"),
                plot_name="Gain3D",
                project_path=str(EXPORT_DIR),
            )
        except Exception as e:
            # 3D 导出依赖 GUI 渲染,non_graphical 下可能失败 — 不致命
            print(f"[warn] 3D plot export skipped: {e}")

        hfss.save_project()

    except Exception as e:
        try:
            hfss.save_project()
        except Exception:
            pass
        print(f"[err] {e}\nProject kept at: {hfss.project_file}")
        raise
    finally:
        hfss.release_desktop(close_projects=False, close_desktop=True)


if __name__ == "__main__":
    main()
