"""从 docx 压缩包里抽出可见文本，供泄题测试使用。"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path


def docx_text(path: Path) -> str:
    """合并 word/*.xml 的文本，隐藏文字和页眉页脚也包括在内。"""
    chunks: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            base = name.rsplit("/", 1)[-1]
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            if not base.startswith(("document", "header", "footer", "footnotes", "endnotes", "comments")):
                continue
            xml = archive.read(name).decode("utf-8")
            xml = re.sub(r"</w:p>", "\n", xml)
            xml = re.sub(r"<[^>]+>", "", xml)
            chunks.append(xml)
    return "\n".join(chunks)


def has_embedded_image(path: Path) -> bool:
    with zipfile.ZipFile(path) as archive:
        return any(name.startswith("word/media/") for name in archive.namelist())
