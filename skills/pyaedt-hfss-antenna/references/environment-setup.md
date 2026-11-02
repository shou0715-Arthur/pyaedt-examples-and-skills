# 环境握手:AEDT / Python / pyaedt 版本与连接方式

接到任务先确认这三件事,任何一项不对都会让后面所有步骤失败。

## 1. 本机 AEDT 装在哪、是哪个版本

### Windows 默认安装路径

```
C:\Program Files\AnsysEM\v<XXX>\Win64\
```

`<XXX>` 是版本数字,对应关系:

| AEDT 版本     | 数字代号 | 环境变量             |
| ------------- | -------- | -------------------- |
| 2026 R1       | 261      | `ANSYSEM_ROOT261`    |
| 2025 R2       | 252      | `ANSYSEM_ROOT252`    |
| 2025 R1       | 251      | `ANSYSEM_ROOT251`    |
| 2024 R2       | 242      | `ANSYSEM_ROOT242`    |
| 2024 R1       | 241      | `ANSYSEM_ROOT241`    |
| 2023 R2       | 232      | `ANSYSEM_ROOT232`    |
| 2023 R1       | 231      | `ANSYSEM_ROOT231`    |
| 2022 R2       | 222      | `ANSYSEM_ROOT222`    |
| 2022 R1       | 221      | `ANSYSEM_ROOT221`    |

PyAEDT 启动时如果不指定 `version=`,会自动找最高版本。要指定版本:

```python
from ansys.aedt.core import Hfss
hfss = Hfss(version="2025.2")     # 字符串,点号分隔
```

### Linux 默认路径

```
/ansys_inc/v<XXX>/AnsysEM/Linux64/ansysedt
```

需要把对应 `ANSYSEM_ROOT<XXX>` 设到环境变量,或在调用时传 `aedt_process_id` / `port`。

### Mac

**AEDT 不支持 Mac 原生**。Mac 用户只能:
- 远程到 Windows/Linux 服务器,在那边跑 AEDT,本地用 pyaedt 走 gRPC 连过去
- 或者只处理 EDB(PyEDB 跨平台),不做完整 HFSS 仿真

## 2. PyAEDT 版本怎么选

### 配套对照(测试主目标版本)

| 你的 AEDT      | 推荐 pyaedt 版本范围   | Python      |
| -------------- | ---------------------- | ----------- |
| 2026 R1        | `>= 0.24`(含 1.0rc)   | 3.10–3.13   |
| 2025 R2        | `>= 0.18`              | 3.10–3.12   |
| 2025 R1        | `0.14 ~ 0.17.x`        | 3.9–3.12    |
| 2024 R2        | `0.10 ~ 0.13.3`        | 3.9–3.12    |
| 2024 R1        | `<= 0.9.x`             | 3.8–3.11    |
| 2023 R2        | `0.6 ~ 0.9`            | 3.8–3.10    |
| 2023 R1        | `0.6 ~ 0.8`            | 3.7–3.10    |
| 2022 R2        | `0.5 ~ 0.7`(gRPC 可用) | 3.7–3.9     |
| 2022 R1        | `0.5 ~ 0.7`(仅 COM)   | 3.7–3.9     |

PyAEDT 向下兼容到 AEDT 2022 R1;表里的"测试主目标"是发版时官方持续验证的版本,选这个组合最稳。

### 安装

```bash
# 当前最新(适配 2025 R2 / 2026 R1)
pip install pyaedt

# 锁版本
pip install "pyaedt==0.17.5"

# 含可选依赖(画图、设计示例等),做天线后处理建议加
pip install "pyaedt[all]"
```

PyAEDT 1.x 起 import 名换成了 `ansys.aedt.core`:

```python
# 推荐(1.x)
import ansys.aedt.core as pyaedt
from ansys.aedt.core import Hfss, Desktop

# 仍可用但 deprecated(0.x 写法)
from pyaedt import Hfss
```

## 3. 通信接口:gRPC vs COM

PyAEDT 通过两条路连 AEDT:

| 接口  | 平台              | 何时用                                    |
| ----- | ----------------- | ----------------------------------------- |
| gRPC  | Windows + Linux   | 默认。AEDT 2023 R1+ 推荐                  |
| COM   | 仅 Windows + .NET | AEDT 2022 R1 必须用;远程不可             |

### 显式选择

```python
from ansys.aedt.core import settings
settings.use_grpc_api = True    # 默认 True,2023 R1+ 不用动
settings.use_grpc_api = False   # 老 AEDT(<= 2022 R1)走 COM
```

### gRPC 远程连接

把 AEDT 起在远端服务器(以 server 模式),pyaedt 在本地连:

```bash
# 服务器端(Windows 例)
ansysedt.exe -grpcsrv 50051
```

```python
# 客户端
hfss = Hfss(machine="10.0.0.5", port=50051, version="2025.2")
```

## 4. 许可证(License)注意

- 启动 AEDT/pyaedt 会占一个 `electronics_desktop` license
- HFSS 求解再额外占 `hfss_solve` 或类似 license(看你的合同)
- **没释放就退出会留下幽灵进程**,下次启动报"license already in use"
- 标准释放方式:

  ```python
  hfss.release_desktop(close_projects=True, close_desktop=True)
  ```

  或用上下文管理器(更稳):

  ```python
  from ansys.aedt.core import Desktop
  with Desktop(version="2025.2", non_graphical=True, new_desktop=True,
               close_on_exit=True) as desktop:
      hfss = Hfss(project="patch.aedt")
      ...
  # with 块退出会自动 release
  ```

### 杀掉幽灵进程(Windows)

```powershell
taskkill /F /IM ansysedt.exe
taskkill /F /IM ansyscl.exe
```

## 5. 启动参数速查

最常用的 `Hfss(...)` 关键参数:

| 参数              | 作用                                  | 推荐值                       |
| ----------------- | ------------------------------------- | ---------------------------- |
| `project`         | 工程文件路径或工程名                  | 绝对路径                     |
| `design`          | 设计名,不存在会新建                   | 字符串                       |
| `version`         | AEDT 版本                             | `"2025.2"`(点号格式)        |
| `non_graphical`   | 不开 GUI                              | `True`(批量/CI 必开)        |
| `new_desktop`     | 是否新开一个 AEDT 进程                | `False` 复用,`True` 隔离     |
| `close_on_exit`   | release 时是否关闭 desktop            | `True`(批量)                |
| `student_version` | 用 Student 版                         | 视情况                       |
| `aedt_process_id` | 连接已有 AEDT 进程的 PID              | 调试时偶尔用                 |
| `solution_type`   | 求解类型                              | `"Modal"`(端口)/`"Terminal"` |

## 检查清单(开工前过一遍)

- [ ] 知道本机 AEDT 版本号?(用 `scripts/check_env.py` 或看安装目录)
- [ ] Python 版本与 pyaedt 版本对得上?(对照本文表 2)
- [ ] 用 gRPC 还是 COM?(默认 gRPC,2022 R1 才需要切 COM)
- [ ] 有没有幽灵 `ansysedt.exe` 进程占着许可证?
- [ ] 工程路径是绝对路径?
- [ ] `non_graphical / close_on_exit` 是否符合你这次跑的目的?
