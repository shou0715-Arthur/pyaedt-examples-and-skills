# 天线/RF 标准仿真流水线 —— API 详解

主线 9 步,每步给出最常用的 PyAEDT API 与可粘贴片段。需要哪步看哪步,不必通读。

## 目录

1. [启动 / 打开工程](#1-启动打开工程)
2. [变量定义](#2-变量定义)
3. [几何建模](#3-几何建模)
4. [材料赋值](#4-材料赋值)
5. [边界与激励](#5-边界与激励)
6. [求解设置 + 扫频](#6-求解设置--扫频)
7. [运行求解](#7-运行求解)
8. [后处理(S 参数 / 远场 / 增益)](#8-后处理)
9. [收尾与释放](#9-收尾与释放)

---

## 1. 启动 / 打开工程

```python
from ansys.aedt.core import Hfss

# 新建工程(项目和设计都不存在则自动创建)
hfss = Hfss(
    project=r"D:\sim\patch_antenna.aedt",
    design="Patch_2p4G",
    solution_type="Modal",         # 端口仿真用 Modal;终端激励用 Terminal
    version="2025.2",
    non_graphical=True,
    new_desktop=False,             # 复用已有 AEDT
    close_on_exit=False,           # release 时不关 desktop
)

# 打开已有工程
hfss = Hfss(project=r"D:\sim\existing.aedt", design="Antenna1", version="2025.2")
```

`solution_type` 选择:
- `"Modal"` —— 模式驱动,端口结果是 S 参数(最常见,patch/dipole/horn 都用这个)
- `"Terminal"` —— 终端驱动,适合多导体共享地的差分结构
- `"Eigenmode"` —— 谐振模式分析(腔体、滤波器)
- `"SBR+"` —— 弹跳射线,大尺寸目标(平台天线、雷达散射)

## 2. 变量定义

仿真前**先把所有可能要扫的尺寸定义成变量**,后期改尺寸或参扫不用动几何代码。

```python
# 项目级变量(所有设计共享,带 $)
hfss["$sub_h"] = "1.6mm"           # FR4 厚度

# 设计级变量(只这个设计可见)
hfss["patch_w"] = "30mm"
hfss["patch_l"] = "32mm"
hfss["feed_x"]  = "8mm"
hfss["freq0"]   = "2.45GHz"

# 读变量
print(hfss["patch_w"])              # '30mm'
print(hfss.variable_manager.variables)
```

变量可以是表达式:

```python
hfss["sub_w"] = "patch_w + 20mm"
hfss["sub_l"] = "patch_l + 20mm"
```

## 3. 几何建模

### 基本图元

```python
modeler = hfss.modeler

# 长方体
sub = modeler.create_box(
    origin=["-sub_w/2", "-sub_l/2", "0"],
    sizes=["sub_w", "sub_l", "$sub_h"],
    name="Substrate",
    material="FR4_epoxy",
)

# 矩形面(贴片)
patch = modeler.create_rectangle(
    orientation="XY",
    origin=["-patch_w/2", "-patch_l/2", "$sub_h"],
    sizes=["patch_w", "patch_l"],
    name="Patch",
)

# 圆柱(同轴馈电芯)
feed_pin = modeler.create_cylinder(
    orientation="Z",
    origin=["feed_x", "0", "0"],
    radius="0.6mm",
    height="$sub_h",
    name="FeedPin",
    material="copper",
)
```

### 包围空气盒(辐射边界要)

天线仿真必须有空气盒,边界距天线至少 λ/4(2.45 GHz 约 30 mm)。

```python
# 自动按比例包一层空气盒
hfss.modeler.create_air_region(
    x_pos=20, y_pos=20, z_pos=30,
    x_neg=20, y_neg=20, z_neg=10,
    is_percentage=False,            # 直接用 mm
)
```

### 导入 CAD

```python
hfss.modeler.import_3d_cad(r"D:\sim\horn.step", healing=True)
```

## 4. 材料赋值

PyAEDT 自带常用材料(`copper / FR4_epoxy / Rogers RO4350 / vacuum / air` 等)。建模时通过 `material=` 直接赋值即可。自定义材料:

```python
my_mat = hfss.materials.add_material("MyDielectric")
my_mat.permittivity = 4.4
my_mat.dielectric_loss_tangent = 0.02
```

## 5. 边界与激励

### 5.1 辐射边界(天线必加)

```python
# 给空气盒外表面加辐射边界
hfss.assign_radiation_boundary_to_objects("Region")
```

更好的选择是 PML(吸收完美层),计算量大但精度高:

```python
hfss.create_pml_region(["+X", "-X", "+Y", "-Y", "+Z", "-Z"], thickness="5mm")
```

### 5.2 完美电导体(地、贴片)

```python
hfss.assign_perfecte_to_sheets(["Patch", "GND"])
```

### 5.3 集总端口(Lumped Port)—— patch 同轴馈电常用

```python
# 馈电端口的端口面(通常是同轴外导体内壁的小矩形)
port_sheet = modeler.create_rectangle(
    orientation="XZ",
    origin=["feed_x - 0.6mm", "0", "0"],
    sizes=["1.2mm", "$sub_h"],
    name="PortSheet",
)

hfss.lumped_port(
    assignment="PortSheet",
    integration_line=hfss.AxisDir.ZNeg,    # 积分线方向
    impedance=50,
    name="P1",
    renormalize=True,
)
```

### 5.4 波端口(Wave Port)—— 波导/微带馈线常用

```python
hfss.wave_port(
    assignment="PortFace",
    integration_line=hfss.AxisDir.ZPos,
    impedance=50,
    modes=1,
    name="P1",
)
```

### 5.5 Floquet 端口(周期阵列、超表面)

```python
hfss.create_floquet_port(
    face=top_face,
    lattice_origin=[0, 0, 0],
    lattice_a_end=["a", 0, 0],
    lattice_b_end=[0, "b", 0],
    name="Floquet1",
    modes=2,
)
```

## 6. 求解设置 + 扫频

```python
setup = hfss.create_setup(
    name="Setup1",
    setup_type="HFSSDriven",
    Frequency="2.45GHz",        # 自适应网格频率,通常取目标中心频率
    MaximumPasses=15,           # 最大自适应迭代次数
    MaxDeltaS=0.02,             # 收敛阈值,正式跑 0.02,粗跑 0.05
    MinimumPasses=2,
    BasisOrder=1,               # 1=一阶,精度足够;-1=mixed
)

# 离散点扫频(精确,慢)
sweep_disc = setup.create_linear_count_sweep(
    unit="GHz", start_frequency=2.0, stop_frequency=3.0,
    num_of_freq_points=21,
    name="SweepDisc",
    sweep_type="Discrete",
)

# 插值扫频(快,推荐)
sweep_interp = setup.create_linear_count_sweep(
    unit="GHz", start_frequency=2.0, stop_frequency=3.0,
    num_of_freq_points=401,
    name="SweepInterp",
    sweep_type="Interpolating",
)

# 快速扫频(单点 + 微扰,极快但只在小带宽精确)
sweep_fast = setup.create_linear_count_sweep(
    unit="GHz", start_frequency=2.4, stop_frequency=2.5,
    num_of_freq_points=101,
    name="SweepFast",
    sweep_type="Fast",
)
```

扫频类型选择:
- **Interpolating**(默认推荐):宽带、平滑响应,大多数天线
- **Discrete**:谐振尖锐、滤波器、需逐点准确
- **Fast**:窄带(<10% 带宽),只看一个谐振峰

## 7. 运行求解

```python
# 阻塞式,等求解完
hfss.analyze(
    setup="Setup1",
    cores=8,                    # 物理核数,不要超线程
    use_auto_settings=True,
)

# 后台异步(配合多设计批量跑)
hfss.analyze_setup("Setup1", num_cores=8, blocking=False)
```

## 8. 后处理

### 8.1 S 参数

```python
data = hfss.post.get_solution_data(
    expressions=["dB(S(P1,P1))", "dB(S(P2,P1))"],
    setup_sweep_name="Setup1 : SweepInterp",
    domain="Sweep",
    primary_sweep_variable="Freq",
)

freqs = data.primary_sweep_values        # GHz
s11 = data.data_real("dB(S(P1,P1))")     # list of float

# 导出 CSV
data.export_data_to_csv(r"D:\sim\out\s11.csv")

# 导出 Touchstone
hfss.export_touchstone(setup="Setup1", sweep="SweepInterp",
                      output_file=r"D:\sim\out\patch.s2p")
```

### 8.2 谐振点 / 带宽提取

```python
import numpy as np

s11_db = np.array(data.data_real("dB(S(P1,P1))"))
freqs = np.array(data.primary_sweep_values)

# 谐振频率 = S11 最深点
f_res = freqs[np.argmin(s11_db)]

# -10 dB 带宽
mask = s11_db <= -10
if mask.any():
    bw_low, bw_high = freqs[mask].min(), freqs[mask].max()
    bw = bw_high - bw_low
    fbw_pct = bw / f_res * 100
```

### 8.3 远场方向图

先建立"无穷球"采样面:

```python
sphere = hfss.insert_infinite_sphere(
    definition="Theta-Phi",
    x_start=0, x_stop=180, x_step=2,        # theta
    y_start=-180, y_stop=180, y_step=2,     # phi
    name="Infinite_Sphere",
)
```

提取数据:

```python
# 2D 切面方向图
ff = hfss.post.get_far_field_data(
    expressions=["GainTotal"],
    setup_sweep_name="Setup1 : SweepInterp",
    domain="Infinite_Sphere",
)

# 3D 增益图(导出到 png)
hfss.post.create_3d_plot(
    plot_name="Gain3D",
    solution=hfss.nominal_adaptive,
    quantity_name="GainTotal",
    primary_sweep="Phi",
    secondary_sweep="Theta",
)
```

### 8.4 关键指标

| 指标         | 表达式                     | 物理含义               |
| ------------ | -------------------------- | ---------------------- |
| 回波损耗     | `dB(S(1,1))`               | 越负越好,工程线 -10 dB |
| VSWR         | `VSWR(1)`                  | < 2 视为匹配良好       |
| 增益(dBi)    | `GainTotal` 最大值,转 dB    | 主瓣方向辐射强度       |
| 实际增益     | `RealizedGainTotal`         | 含失配损耗的真实增益   |
| 辐射效率     | `RadiationEfficiency`       | 0~1,越高越好           |
| 总效率       | `TotalEfficiency`           | 含失配                 |
| 半功率波束宽 | 方向图 -3 dB 点             | 主瓣覆盖角             |

## 9. 收尾与释放

```python
hfss.save_project()

hfss.release_desktop(
    close_projects=False,          # 保留工程在 AEDT 中
    close_desktop=True,             # 关闭 AEDT 进程
)
```

更稳的写法是用上下文管理器,异常也能正确释放:

```python
from ansys.aedt.core import Desktop, Hfss

with Desktop(version="2025.2", non_graphical=True,
             new_desktop=True, close_on_exit=True):
    hfss = Hfss(project="patch.aedt", design="Patch")
    # ... 仿真代码 ...
    hfss.save_project()
# 这里 desktop 自动 release
```
