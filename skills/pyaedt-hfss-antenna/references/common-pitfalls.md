# 常见坑速查

按"症状"分类,扫一眼就能定位。每条都给出**为什么会这样**和**怎么修**。

---

## A. 启动 / 连接类

### A1. `Could not start Ansys Electronics Desktop` / 启动卡住

可能原因:
- 没装 AEDT,或 `version=` 指定的版本不存在
- 上一次 pyaedt 退出没释放,有幽灵进程
- 许可证服务器不通

**修复:**
1. Windows:`taskkill /F /IM ansysedt.exe & taskkill /F /IM ansyscl.exe`
2. 检查 `C:\Program Files\AnsysEM\` 下哪些版本存在
3. 命令行单独启 AEDT 看能不能起来:`& "C:\Program Files\AnsysEM\v252\Win64\ansysedt.exe"`

### A2. `License checkout failed`

- License 服务器没启动 / VPN 没连
- 上一次没正常 release,license 还被占着
- 同时跑的 AEDT 实例数超过 license 数

**修复:**
- 等 5-10 分钟让 license server 自动回收(默认 timeout)
- 或重启 ansyslmd 服务
- 之后用 `with Desktop(...) as d:` 上下文管理器避免再泄漏

### A3. `gRPC connect failed` / 远程连不上

- 远端没用 `-grpcsrv <port>` 启动
- 防火墙挡了端口
- 版本不匹配:client 的 pyaedt 版本和 server 端 AEDT 版本差太多

**修复:**
```python
# 显式指定
hfss = Hfss(machine="10.0.0.5", port=50051, version="2025.2")
# 测试:能 ping 通服务器,telnet 该端口能通
```

### A4. AEDT 2022 R1 报 `gRPC not supported`

2022 R1 不支持 gRPC,必须切 COM:

```python
from ansys.aedt.core import settings
settings.use_grpc_api = False           # 必须在 import Hfss 之前设
```

注意 COM 只在 Windows 上可用。

---

## B. 几何建模类

### B1. 创建几何后看不到

- 没 save 或没刷新视图
- non_graphical=True 时本来就看不到
- 单位错了(默认 mm,你给了 m 当 mm 用了)

**修复:**
```python
hfss.modeler.model_units = "mm"        # 显式设单位
hfss.save_project()
```

### B2. 参数表达式报错 `Variable not defined`

常见于变量没建就用、或大小写错。变量名**大小写敏感**,而且项目变量必须带 `$`:

```python
hfss["$sub_h"] = "1.6mm"        # 项目变量
hfss["patch_w"] = "30mm"        # 设计变量
modeler.create_box(sizes=["patch_w", "patch_l", "$sub_h"])  # 项目变量也带 $
```

### B3. 导入 STEP 后丢面 / 残留小特征

```python
hfss.modeler.import_3d_cad("xxx.step", healing=True)  # 务必开 healing
# 还可后处理:
hfss.modeler.heal_objects(["Body1"])
```

---

## C. 边界 / 端口类

### C1. `No port assigned` 求解直接失败

激励忘了加,或加在了错的对象上(比如加在 3D 体而不是面)。

```python
# 端口必须建在 sheet(2D)上
port_sheet = modeler.create_rectangle(...)
hfss.lumped_port(assignment="port_sheet", ...)
```

### C2. 端口阻抗算出来不是 50Ω

- 端口面尺寸不对(波端口尺寸要 ≥ 3 倍传输线宽)
- 积分线方向给错了
- 端口面没紧贴金属(端口面应该在馈电缝隙处,两端贴 PEC 边界)

### C3. 辐射边界距天线太近

距离 < λ/4 会让辐射边界吸收近场,导致结果失真。

```python
# 2.45 GHz, λ=122mm, λ/4=30mm,空气盒留 30 mm 余量
hfss.modeler.create_air_region(
    x_pos=30, y_pos=30, z_pos=40,
    x_neg=30, y_neg=30, z_neg=10,
    is_percentage=False,
)
```

---

## D. 求解 / 收敛类

### D1. 求解跑了几小时不收敛

- `MaxDeltaS` 太严(<0.01)
- `MaximumPasses` 太多
- 网格初始就太粗,自适应每步翻倍直到内存耗尽

**修复:**
- 先粗跑:`MaximumPasses=5, MaxDeltaS=0.05`
- 收敛了再加密
- 检查内存使用,32 GB 机器跑大模型容易 OOM

### D2. 求解快但 S11 像噪声

通常是没收敛。检查 setup 报告里 `Max Delta S` 是不是真到了你设的阈值。如果只跑了 2 pass 就停,可能是 `MinimumPasses` 没设。

### D3. 多核求解反而慢

- 物理核 vs 超线程:cores 数应该 ≤ 物理核数
- 内存带宽瓶颈:超过 8 核往往边际收益很差
- 大模型对 NUMA 敏感,Windows 任务管理器看 CPU 是不是被均匀使用

```python
hfss.analyze(setup="Setup1", cores=8, use_auto_settings=True)
```

---

## E. 后处理类

### E1. `get_solution_data` 返回 None / 空

- `setup_sweep_name` 拼错了(空格、冒号)
- 求解还没跑完 / 没 sweep 结果
- expression 写法错(用 `S(1,1)` 而不是 `S11`)

```python
# 正确写法
data = hfss.post.get_solution_data(
    expressions=["dB(S(P1,P1))"],            # 用端口名,不要写数字
    setup_sweep_name="Setup1 : SweepInterp", # 中间有空格
)
```

### E2. 远场看不到方向图

- 没建 infinite sphere
- expression 用了 `Gain` 而 setup 没勾"compute radiation"
- HFSS 默认远场是相对辐射边界算的,辐射边界没设也没远场

### E3. 单位混乱:dBi vs dB vs 倍数

- `GainTotal` 默认是**线性倍数**,转 dB 要 `dB(GainTotal)` 或 Python 里 `10*log10(g)`
- `dB(S(1,1))` 已经是 dB
- 角度单位看 `Theta/Phi` 表达式默认 deg,函数参数默认也 deg

---

## F. 流程 / 工程类

### F1. 脚本结束 AEDT 不退出

没调 `release_desktop` 或调了但 `close_desktop=False`:

```python
hfss.release_desktop(close_projects=True, close_desktop=True)
```

更稳的方式:`try/finally` 或 `with Desktop(...)`。

### F2. 工程文件越来越大(几 GB)

每次跑都保留了 `.aedtresults`。批量跑时建议:

```python
hfss.cleanup_solution()                  # 清求解结果
hfss.save_project(overwrite=True)
```

或干脆每次复制工程文件到临时目录跑,跑完只导出结果。

### F3. 路径问题:相对路径找不到文件

AEDT 进程的工作目录不一定是脚本所在目录。**永远用绝对路径**。

```python
import os
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.join(HERE, "..", "projects", "patch.aedt")
```

### F4. 中文路径报错

PyAEDT 跨进程通信对非 ASCII 路径不稳定。**项目路径全用英文**。

---

## G. 调试技巧

### G1. 让 pyaedt 多说话

```python
import logging
from ansys.aedt.core import settings
settings.enable_debug_logger = True
settings.enable_logger = True
logging.basicConfig(level=logging.DEBUG)
```

日志默认写在 `%TEMP%\pyaedt.log` (Windows) / `/tmp/pyaedt.log`。

### G2. 跑通流水线再加密

第一次跑任何脚本:

```python
setup = hfss.create_setup(Frequency="2.45GHz",
                          MaximumPasses=3,        # 粗
                          MaxDeltaS=0.1)
sweep = setup.create_linear_count_sweep(num_of_freq_points=21)  # 稀
```

5-10 分钟跑完,看流程对不对。再改成 `MaximumPasses=15, MaxDeltaS=0.02, num_of_freq_points=401` 正式跑。

### G3. 出错时不要直接 release

报错后保留 AEDT 进程 + 工程,手动打开 GUI 看几何/边界对不对:

```python
try:
    ...
except Exception:
    hfss.save_project()
    print("出错了,AEDT 工程保留在", hfss.project_file)
    raise
finally:
    # 出错时不关 desktop,方便调试
    hfss.release_desktop(close_projects=False, close_desktop=False)
```
