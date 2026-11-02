"""
环境探测脚本:列出本机能用的 AEDT 安装、Python 版本、pyaedt 版本,
并给出最匹配的 pyaedt 推荐。

用法:
    python check_env.py
"""

from __future__ import annotations

import os
import sys
import platform
import subprocess
from pathlib import Path


# AEDT 数字代号 -> 商业版本名
VERSION_MAP = {
    "261": "2026 R1",
    "252": "2025 R2",
    "251": "2025 R1",
    "242": "2024 R2",
    "241": "2024 R1",
    "232": "2023 R2",
    "231": "2023 R1",
    "222": "2022 R2",
    "221": "2022 R1",
    "212": "2021 R2",
    "211": "2021 R1",
}


# pyaedt 推荐对照(测试主目标版本)
PYAEDT_REC = {
    "261": ">=0.24",
    "252": ">=0.18",
    "251": "0.14 ~ 0.17.x",
    "242": "0.10 ~ 0.13.3",
    "241": "<=0.9.x",
    "232": "0.6 ~ 0.9",
    "231": "0.6 ~ 0.8",
    "222": "0.5 ~ 0.7 (gRPC 可用)",
    "221": "0.5 ~ 0.7 (仅 COM)",
    "212": "0.5 (仅 COM)",
    "211": "0.5 (仅 COM)",
}


def find_aedt_installs() -> list[tuple[str, str, Path]]:
    """返回 [(代号, 商业版本名, 路径)] 列表。"""
    found = []
    sys_name = platform.system()

    if sys_name == "Windows":
        # 1) 环境变量
        for code in VERSION_MAP:
            env_key = f"ANSYSEM_ROOT{code}"
            p = os.environ.get(env_key)
            if p and Path(p).exists():
                found.append((code, VERSION_MAP[code], Path(p)))

        # 2) 标准目录扫一遍兜底
        base_candidates = [
            Path(r"C:\Program Files\AnsysEM"),
            Path(r"C:\Program Files\AnsysEM\AnsysEM"),
        ]
        for base in base_candidates:
            if not base.exists():
                continue
            for child in base.iterdir():
                if not child.is_dir():
                    continue
                # 形如 v252 或 v252Win64
                name = child.name.lower()
                for code in VERSION_MAP:
                    if name.startswith(f"v{code}"):
                        path = child / "Win64"
                        if path.exists() and (code, VERSION_MAP[code], path) not in found:
                            found.append((code, VERSION_MAP[code], path))

    elif sys_name == "Linux":
        for code in VERSION_MAP:
            env_key = f"ANSYSEM_ROOT{code}"
            p = os.environ.get(env_key)
            if p and Path(p).exists():
                found.append((code, VERSION_MAP[code], Path(p)))
        base = Path("/ansys_inc")
        if base.exists():
            for child in base.iterdir():
                name = child.name.lower()
                for code in VERSION_MAP:
                    if name.startswith(f"v{code}"):
                        path = child / "AnsysEM" / "Linux64"
                        if path.exists() and (code, VERSION_MAP[code], path) not in found:
                            found.append((code, VERSION_MAP[code], path))

    elif sys_name == "Darwin":
        # macOS 没有原生 AEDT
        pass

    # 按版本号降序
    found.sort(key=lambda t: int(t[0]), reverse=True)
    return found


def get_pyaedt_version() -> str | None:
    try:
        import ansys.aedt.core as pyaedt
        return getattr(pyaedt, "__version__", None) or "unknown"
    except ImportError:
        try:
            import pyaedt
            return getattr(pyaedt, "__version__", None) or "unknown (legacy import)"
        except ImportError:
            return None


def get_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def main() -> int:
    print("=" * 60)
    print(" PyAEDT environment check")
    print("=" * 60)

    print(f"\n[OS]      {platform.system()} {platform.release()}")
    print(f"[Python]  {get_python_version()}  ({sys.executable})")

    pyaedt_ver = get_pyaedt_version()
    if pyaedt_ver:
        print(f"[pyaedt]  {pyaedt_ver}")
    else:
        print("[pyaedt]  NOT INSTALLED")
        print("          install:  pip install pyaedt")

    if platform.system() == "Darwin":
        print("\n[!] macOS 不支持原生 AEDT。需远程到 Windows/Linux 服务器,"
              "本地 pyaedt 走 gRPC 连接。")
        return 0

    print("\n--- AEDT installations ---")
    installs = find_aedt_installs()
    if not installs:
        print("  没找到任何 AEDT 安装。")
        print("  Windows 默认路径:C:\\Program Files\\AnsysEM\\v<XXX>\\Win64\\")
        print("  或设置环境变量 ANSYSEM_ROOT<XXX> 指向 AEDT 根目录。")
        return 1

    for code, name, path in installs:
        rec = PYAEDT_REC.get(code, "?")
        print(f"  v{code} ({name})")
        print(f"      path : {path}")
        print(f"      pyaedt 推荐版本:{rec}")

    # 给出主推
    top_code, top_name, top_path = installs[0]
    print(f"\n[推荐] 优先使用 AEDT {top_name},pyaedt 装 {PYAEDT_REC.get(top_code, '最新')}")
    print(f"\n        在 Hfss(...) 里这样指定:")
    print(f"        hfss = Hfss(version=\"{top_code[0:2]}.{top_code[2]}\", ...)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
