"""在本机有 LibreOffice 时，把 docx 转成 PDF。没有则跳过。"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def export_pdf(docx_path: Path) -> tuple[Path | None, str | None]:
    """返回 (pdf 路径, 警告)。转换失败不删除已生成的 docx。"""
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if executable is None:
        return None, "未检测到 LibreOffice（soffice），已跳过 PDF。"
    try:
        completed = subprocess.run(
            [
                executable,
                "--headless",
                "--norestore",
                "--convert-to",
                "pdf",
                "--outdir",
                str(docx_path.parent),
                str(docx_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return None, f"LibreOffice 转换超时，已保留 docx：{docx_path.name}"
    pdf_path = docx_path.with_suffix(".pdf")
    if completed.returncode != 0 or not pdf_path.is_file():
        detail = (completed.stderr or completed.stdout or "").strip()
        return None, f"LibreOffice 转换 PDF 失败，已保留 docx。{detail}"
    return pdf_path, None
