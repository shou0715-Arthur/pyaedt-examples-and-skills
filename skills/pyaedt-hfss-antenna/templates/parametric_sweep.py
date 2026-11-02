"""
模板:几何/材料参数扫描
========================================
适用:研究某个或某几个变量(如 patch_w / feed_x)对 S11、谐振频率、增益的影响,
     一次跑出多组结果,导出汇总 CSV。

两种模式:
  - SWEEP_MODE = "native"   用 AEDT 原生 ParametricSetup,效率最高,所有点共用一次仿真启动
  - SWEEP_MODE = "loop"     Python 循环改变量再 analyze,简单但每点都要重启 setup
建议默认 "native"。

用法:
    1) 改下方 USER CONFIG
    2) python parametric_sweep.py
"""

from __future__ import annotations

import csv
import itertools
from pathlib import Path

import numpy as np
from ansys.aedt.core import Hfss

# ============================ USER CONFIG ============================
PROJECT_PATH  = r"D:\sim\patch_2p4G.aedt"
DESIGN_NAME   = "Patch_2p4G"
AEDT_VERSION  = "2025.2"

SETUP_NAME    = "Setup1"
SWEEP_NAME    = "SweepInterp"

# 要扫的变量与取值列表(可一维也可多维)
VARIABLES = {
    "patch_w": ["28mm", "30mm", "32mm"],
    "feed_x":  ["6mm",  "8mm",  "10mm"],
}

# 提取的标量(对每个 case 提取一组)
S_EXPR        = "dB(S(P1,P1))"
TARGET_FREQ_GHZ = 2.45                       # 用来取该频点 S11
TRACK_GAIN    = True                         # 是否同时跑远场取 peak gain

EXPORT_DIR    = Path(PROJECT_PATH).parent / "out_param"
SWEEP_MODE    = "native"                     # "native" / "loop"

CORES         = 8
NON_GRAPHICAL = True
# ============================ /USER CONFIG ===========================


def native_param_sweep(hfss: Hfss) -> str:
    """用 AEDT 原生 ParametricSetup 跑全组合,返回 parametric setup 名。"""
    param = hfss.parametrics.add(
        variable=list(VARIABLES.keys())[0],  # 占位,后面 add_variation 覆盖
        start_point=0, end_point=1, step=1,
        parametric_name="ParamSweep",
        solution=f"{SETUP_NAME} : {SWEEP_NAME}",
    )
    # 清掉占位 variation,用真正的离散组合
    param.props["Sweeps"]["SweepDefinition"] = []
    for var_name, values in VARIABLES.items():
        param.add_variation(
            sweep_variable=var_name,
            datalist=values,
            unit="",
            override_existing=False,
        )
    param.analyze(cores=CORES)
    return param.name


def loop_sweep_records(hfss: Hfss):
    """Python 循环模式:逐点改变量 + analyze + 取数据。yield dict 记录。"""
    keys = list(VARIABLES.keys())
    for combo in itertools.product(*VARIABLES.values()):
        for k, v in zip(keys, combo):
            hfss[k] = v

        hfss.analyze(setup=SETUP_NAME, cores=CORES, use_auto_settings=True)

        s_data = hfss.post.get_solution_data(
            expressions=[S_EXPR],
            setup_sweep_name=f"{SETUP_NAME} : {SWEEP_NAME}",
            domain="Sweep",
            primary_sweep_variable="Freq",
        )
        freqs = np.array(s_data.primary_sweep_values, dtype=float)
        s11 = np.array(s_data.data_real(S_EXPR), dtype=float)
        idx = int(np.argmin(np.abs(freqs - TARGET_FREQ_GHZ)))
        s11_at_target = float(s11[idx])
        f_res = float(freqs[int(np.argmin(s11))])

        rec = dict(zip(keys, combo))
        rec.update({
            "f_res_GHz": f_res,
            f"s11_at_{TARGET_FREQ_GHZ}GHz_dB": s11_at_target,
            "s11_min_dB": float(s11.min()),
        })

        if TRACK_GAIN:
            try:
                ff = hfss.post.get_far_field_data(
                    expressions=["GainTotal"],
                    setup_sweep_name=f"{SETUP_NAME} : {SWEEP_NAME}",
                    domain="Infinite_Sphere",   # 假设已建,否则建议 native 模式
                    variations={"Freq": [f"{TARGET_FREQ_GHZ}GHz"], "Phi": ["0deg"]},
                )
                if ff is not None:
                    g_lin = np.array(ff.data_real("GainTotal"), dtype=float)
                    rec["peak_gain_dBi"] = float(10*np.log10(max(g_lin.max(), 1e-12)))
            except Exception as e:
                rec["peak_gain_dBi"] = None
                rec["gain_warn"] = str(e)

        yield rec


def export_records(records: list[dict], path: Path) -> None:
    if not records:
        print("[warn] no records to export")
        return
    fieldnames = list({k for r in records for k in r.keys()})
    fieldnames.sort()
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in records:
            w.writerow(r)
    print(f"[ok ] summary -> {path}")


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
        if SWEEP_MODE == "native":
            param_name = native_param_sweep(hfss)
            print(f"[ok ] native parametric sweep '{param_name}' done. "
                  f"打开 GUI 看 Results / Parametric 表查看汇总")
            # 提示:从 native 模式取标量需要 hfss.post.create_report_from_oreport
            #       或直接看 AEDT 内的报告。复杂时切到 loop 模式更直接。

        elif SWEEP_MODE == "loop":
            records = list(loop_sweep_records(hfss))
            export_records(records, EXPORT_DIR / "param_summary.csv")

        else:
            raise ValueError(f"unknown SWEEP_MODE: {SWEEP_MODE}")

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
