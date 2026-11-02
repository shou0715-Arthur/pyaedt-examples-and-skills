"""
模板:S 参数扫频提取
========================================
适用:已有 .aedt 工程(里面建好了几何、边界、端口),想批量跑扫频并把
     S(i,j) 导出成 CSV / Touchstone,顺便提取谐振频率和 -10 dB 带宽。

用法:
    1) 改下方 USER CONFIG 区
    2) python sparam_extraction.py

依赖:
    pip install "pyaedt[all]" numpy
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from ansys.aedt.core import Hfss

# ============================ USER CONFIG ============================
PROJECT_PATH  = r"D:\sim\patch_2p4G.aedt"   # 绝对路径,英文
DESIGN_NAME   = "Patch_2p4G"
AEDT_VERSION  = "2025.2"

SETUP_NAME    = "Setup1"
SWEEP_NAME    = "SweepInterp"
FREQ_START_GHZ = 2.0
FREQ_STOP_GHZ  = 3.0
NUM_POINTS    = 401
SWEEP_TYPE    = "Interpolating"             # Interpolating / Discrete / Fast

ADAPT_FREQ    = "2.45GHz"
MAX_PASSES    = 15
MAX_DELTA_S   = 0.02

PORT_NAMES    = ["P1"]                       # 要提取哪几个端口的 S
S_EXPRESSIONS = ["dB(S(P1,P1))"]             # 想看的 S 参数表达式
EXPORT_DIR    = Path(PROJECT_PATH).parent / "out"

CORES         = 8
NON_GRAPHICAL = True
NEW_DESKTOP   = False
# ============================ /USER CONFIG ===========================


def ensure_setup_and_sweep(hfss: Hfss) -> None:
    """如果 setup/sweep 不存在则创建;存在则更新参数。"""
    setup = next((s for s in hfss.setups if s.name == SETUP_NAME), None)
    if setup is None:
        setup = hfss.create_setup(
            name=SETUP_NAME,
            setup_type="HFSSDriven",
            Frequency=ADAPT_FREQ,
            MaximumPasses=MAX_PASSES,
            MaxDeltaS=MAX_DELTA_S,
            MinimumPasses=2,
            BasisOrder=1,
        )
    else:
        setup.props["Frequency"] = ADAPT_FREQ
        setup.props["MaximumPasses"] = MAX_PASSES
        setup.props["MaxDeltaS"] = MAX_DELTA_S
        setup.update()

    if not any(sw.name == SWEEP_NAME for sw in setup.sweeps):
        setup.create_linear_count_sweep(
            unit="GHz",
            start_frequency=FREQ_START_GHZ,
            stop_frequency=FREQ_STOP_GHZ,
            num_of_freq_points=NUM_POINTS,
            name=SWEEP_NAME,
            sweep_type=SWEEP_TYPE,
            save_fields=False,
        )


def extract_resonance_and_bw(freqs_ghz: np.ndarray, s11_db: np.ndarray,
                              threshold_db: float = -10.0) -> dict:
    """从 S11(dB) 数组提取谐振频率与 -threshold dB 带宽。"""
    f_res = float(freqs_ghz[np.argmin(s11_db)])
    s11_min = float(s11_db.min())

    mask = s11_db <= threshold_db
    if mask.any():
        bw_low = float(freqs_ghz[mask].min())
        bw_high = float(freqs_ghz[mask].max())
        bw = bw_high - bw_low
        fbw_pct = bw / f_res * 100.0
    else:
        bw_low = bw_high = bw = fbw_pct = float("nan")

    return {
        "f_res_GHz": f_res,
        "s11_min_dB": s11_min,
        "bw_low_GHz": bw_low,
        "bw_high_GHz": bw_high,
        "bw_GHz": bw,
        "fbw_percent": fbw_pct,
    }


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    hfss = Hfss(
        project=PROJECT_PATH,
        design=DESIGN_NAME,
        version=AEDT_VERSION,
        non_graphical=NON_GRAPHICAL,
        new_desktop=NEW_DESKTOP,
        close_on_exit=False,
    )

    try:
        ensure_setup_and_sweep(hfss)

        print(f"[run] solving {SETUP_NAME}/{SWEEP_NAME} on {CORES} cores ...")
        hfss.analyze(setup=SETUP_NAME, cores=CORES, use_auto_settings=True)

        # 1) Touchstone 导出
        touchstone_path = EXPORT_DIR / f"{DESIGN_NAME}.s{len(PORT_NAMES)}p"
        hfss.export_touchstone(
            setup=SETUP_NAME,
            sweep=SWEEP_NAME,
            output_file=str(touchstone_path),
        )
        print(f"[ok ] touchstone -> {touchstone_path}")

        # 2) 取数据 + CSV
        data = hfss.post.get_solution_data(
            expressions=S_EXPRESSIONS,
            setup_sweep_name=f"{SETUP_NAME} : {SWEEP_NAME}",
            domain="Sweep",
            primary_sweep_variable="Freq",
        )
        if data is None:
            raise RuntimeError("get_solution_data returned None — sweep 可能没跑成功")

        csv_path = EXPORT_DIR / f"{DESIGN_NAME}_sparams.csv"
        data.export_data_to_csv(str(csv_path))
        print(f"[ok ] csv        -> {csv_path}")

        # 3) 提取关键指标
        freqs = np.array(data.primary_sweep_values, dtype=float)  # GHz
        s11 = np.array(data.data_real(S_EXPRESSIONS[0]), dtype=float)
        metrics = extract_resonance_and_bw(freqs, s11, threshold_db=-10.0)

        print("\n=== Antenna metrics ===")
        for k, v in metrics.items():
            print(f"  {k:>15s}: {v:.4f}" if isinstance(v, float) else f"  {k:>15s}: {v}")

        hfss.save_project()

    except Exception as e:
        # 保留工程便于调试
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
