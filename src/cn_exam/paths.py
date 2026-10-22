"""定位 data/ 目录。

查找顺序：
1. 调用方显式传入
2. 环境变量 CN_EXAM_DATA_DIR
3. 安装包内的 cn_exam/data（若打包时放入）
4. 从本文件向上找到含 pyproject.toml 的仓库根目录下的 data/
5. 当前工作目录下的 data/
"""

from __future__ import annotations

import os
from pathlib import Path

from cn_exam.errors import DataError


def find_data_dir(explicit: str | Path | None = None) -> Path:
    """返回题库根目录。目录必须真实存在。"""
    if explicit is not None:
        path = Path(explicit).expanduser().resolve()
        if not path.is_dir():
            raise DataError(f"数据目录不存在：{path}")
        return path

    env = os.environ.get("CN_EXAM_DATA_DIR")
    if env:
        path = Path(env).expanduser().resolve()
        if path.is_dir():
            return path
        raise DataError(f"环境变量 CN_EXAM_DATA_DIR 不是目录：{path}")

    bundled = Path(__file__).resolve().parent / "data"
    if bundled.is_dir() and any(bundled.iterdir()):
        return bundled

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "data"
        if (parent / "pyproject.toml").is_file() and candidate.is_dir():
            return candidate

    cwd_data = Path.cwd() / "data"
    if cwd_data.is_dir():
        return cwd_data.resolve()

    raise DataError(
        "找不到题库目录 data/。请在仓库根目录运行，或设置 CN_EXAM_DATA_DIR。"
    )
