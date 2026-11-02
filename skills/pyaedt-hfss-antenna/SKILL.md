---
name: pyaedt-hfss-antenna
description: 用 PyAEDT 驱动 Ansys HFSS / AEDT 完成天线与 RF 仿真自动化的工作流骨架。当用户提到 HFSS、Ansys Electronics Desktop、AEDT、pyaedt、ansys.aedt.core,或要做天线仿真、S 参数(S11/S21)、回波损耗(return loss)、VSWR、远场方向图(far-field)、增益、辐射效率、阻抗匹配、参数化扫频(frequency sweep)、参扫优化(parametric sweep),或者说"自动化跑 HFSS / 用脚本驱动 HFSS / 让 agent 帮我跑仿真"时,务必使用本 skill。即使用户没明说"用 pyaedt",只要任务核心是"用 Python 控制 HFSS 做天线/RF 仿真",也应触发。
---

# PyAEDT HFSS 天线/RF 仿真 Skill

## 这个 skill 解决什么问题

把"agent 用 Python 驱动 Ansys HFSS 做天线/RF 仿真"这件事流程化。它给你三样东西:

1. **环境握手指引** —— 怎么找到本机 AEDT、用 gRPC 还是 COM、避免许可证冲突
2. **标准天线仿真流水线** —— 建项目 → 建模 → 边界/激励 → 求解设置 → 扫频 → 求解 → 后处理,每步给出可粘贴改写的代码骨架
3. **三个高频任务模板** —— S 参数提取、远场方向图、参数化扫频,直接当起点改

它**不替你设计天线**(几何、馈电方式、目标频段是用户/工程师的工作),只负责把"已知设计 → 跑出仿真结果"这条路走顺。

## 何时触发

- 用户说"用 HFSS 仿真这个天线"、"提取 S 参数"、"扫频 2-6 GHz"、"画方向图"、"看增益"
- 用户给出了 `.aedt`/`.aedtz`/`.hfss` 工程,要求自动跑/批量跑
- 用户写代码 `import ansys.aedt.core` / `from pyaedt import Hfss`
- 用户问"怎么用 pyaedt 启动 HFSS"、"为什么连不上 AEDT"、"许可证占用怎么办"

## 标准工作流(一条主线)

无论具体任务是什么,天线/RF 仿真都遵循下面这条主线。**先沿这条线建立心智地图**,再跳到对应模板:

```
[1] 环境握手    →  确认 AEDT 版本 + Python 版本 + 通信接口
                   见 references/environment-setup.md
                   不确定时先跑 scripts/check_env.py

[2] 建/打开工程  →  Hfss(project=..., design=..., version=..., new_desktop=...)
                   关键:non_graphical=True 用于 CI/批量
                          new_desktop=False 复用已开的桌面
                          close_on_exit=True 跑完释放许可证

[3] 几何建模     →  hfss.modeler.create_box / create_cylinder / create_polyline ...
                   或用 hfss.modeler.import_3d_cad("xxx.step")
                   建议先定义变量(见下),再用变量驱动几何

[4] 变量参数化   →  hfss[" $patch_w "] = "30mm"  (项目变量,带 $)
                   hfss["patch_l"]    = "32mm"   (设计变量,不带 $)
                   建议把所有可能扫的尺寸都建成变量

[5] 边界与激励   →  辐射边界:hfss.assign_radiation_boundary_to_objects(["AirBox"])
                   端口:    hfss.lumped_port / hfss.wave_port / hfss.create_floquet_port
                   接地:    hfss.assign_perfecte_to_sheets(...)

[6] 求解设置     →  setup = hfss.create_setup("Setup1", Frequency="3GHz",
                                             MaximumPasses=15, MaxDeltaS=0.02)
                   sweep = setup.create_linear_count_sweep(
                       unit="GHz", start_frequency=2, stop_frequency=6,
                       num_of_freq_points=401, sweep_type="Interpolating")

[7] 求解          →  hfss.analyze(setup="Setup1", cores=8)   # 阻塞式
                   或 hfss.analyze_setup("Setup1")

[8] 后处理        →  S 参数:hfss.post.get_solution_data("S(1,1)")
                   远场:  hfss.insert_infinite_sphere(...)
                          hfss.post.get_far_field_data(...)
                   导出:  data.export_data_to_csv("xxx.csv")

[9] 收尾          →  hfss.save_project()
                   hfss.release_desktop(close_projects=False, close_desktop=True)
                   不释放会一直占用许可证!
```

## 怎么用本 skill

### 第一次接到天线/RF 仿真任务时

1. **先读 `references/environment-setup.md`** —— 弄清用户机器上 AEDT 是哪个版本、Python 是哪个版本、要不要装 pyaedt。如果不清楚,运行 `scripts/check_env.py`。
2. **再读 `references/antenna-workflow.md`** —— 这里是上面那条主线的"放大版",每一步给出 API 用法和常用参数。
3. **遇到报错前先扫一眼 `references/common-pitfalls.md`** —— 80% 的"连不上 / 跑不动 / 结果不对"都列在这里。

### 写代码时

去 `templates/` 挑最贴近任务的那个模板,**整段复制后改**:

| 任务类型                              | 模板                                  |
| ------------------------------------- | ------------------------------------- |
| 单个工程,单/多频点 S11/S21 扫频提取   | `templates/sparam_extraction.py`      |
| 远场方向图、增益、辐射效率、3D 方向图 | `templates/far_field_pattern.py`      |
| 几何尺寸/材料参数扫描,提取多组结果    | `templates/parametric_sweep.py`       |

模板都是**可独立运行的脚本**,顶部统一暴露 `PROJECT_PATH / DESIGN_NAME / FREQ_*` 等参数,先改顶部,再改中间几何/边界部分。

### 关键原则

- **先小后大**:第一次跑任何脚本,把网格 `MaximumPasses` 设成 3-5,扫频点设成 21,先跑通流水线再加密。一次到位会浪费几小时。
- **永远 release_desktop**:不释放许可证 = 下次启动报错。脚本结尾用 `try/finally` 包住。
- **non_graphical 默认 True**:除非要看几何/调试,否则不开 GUI,省内存且能并行。
- **路径用绝对路径**:相对路径在 AEDT 进程里不一定指向你以为的目录。
- **变量优先**:任何一个"可能要改"的尺寸,先建成变量,别写死字面量,否则后面参扫要重写。

## 安装 pyaedt(如果还没装)

```bash
# 推荐组合(2025 R2 / 2026 R1)
pip install pyaedt

# 老 AEDT 用旧 pyaedt(具体对照见 references/environment-setup.md)
pip install pyaedt==0.17.5     # AEDT 2025 R1
pip install pyaedt==0.13.3     # AEDT 2024 R2
```

## 不要做的事

- **不要直接 import pyaedt** —— 1.0 起官方推荐 `import ansys.aedt.core as pyaedt` 或 `from ansys.aedt.core import Hfss`。老代码 `from pyaedt import Hfss` 仍可用但已 deprecated。
- **不要在 GUI 已经开着 AEDT 的情况下用 `new_desktop=True`** —— 会另开一个进程,许可证翻倍。要复用已开的桌面用 `new_desktop=False`。
- **不要在 Mac 上期待原生 AEDT** —— AEDT 只跑 Windows/Linux。Mac 上要么远程到 Windows,要么用 PyEDB 处理 EDB 而非 HFSS。
- **不要省略 `hfss.save_project()`** —— release 之前必须 save,否则下次打开找不到改动。
- **不要用 `MaxDeltaS` 太松(>0.05)就交付结果** —— 收敛不够看到的 S11 是噪声不是物理。

## 参考文件清单

```
pyaedt-hfss-antenna/
├── SKILL.md                          ← 你正在读这个
├── references/
│   ├── environment-setup.md          ← 版本对照、安装、gRPC/COM、许可证
│   ├── antenna-workflow.md           ← 主线工作流的 API 详解
│   └── common-pitfalls.md            ← 高频报错与处置
├── templates/
│   ├── sparam_extraction.py          ← S 参数扫频提取
│   ├── far_field_pattern.py          ← 远场方向图/增益
│   └── parametric_sweep.py           ← 变量参扫
└── scripts/
    └── check_env.py                  ← 探测本机 AEDT/Python/pyaedt
```

读取顺序建议:本文 → environment-setup → 模板顶部说明 → antenna-workflow(用到哪步看哪步)→ 出问题查 common-pitfalls。
