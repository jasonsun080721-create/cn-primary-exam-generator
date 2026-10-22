"""命令行入口。"""

from pathlib import Path

from cn_exam.cli import main


def test_cli_unit1(tmp_path: Path, capsys) -> None:
    code = main(
        [
            "--edition",
            "rj2026",
            "--grade",
            "4",
            "--term",
            "1",
            "--unit",
            "1",
            "--output",
            str(tmp_path),
            "--no-pdf",
        ]
    )
    assert code == 0
    output = capsys.readouterr().out
    assert "学生卷" in output
    assert "答案卷" in output
    files = list(tmp_path.glob("*.docx"))
    assert len(files) == 2


def test_cli_list(capsys) -> None:
    assert main(["--list"]) == 0
    output = capsys.readouterr().out
    assert "rj2026" in output
    assert "待补" in output


def test_cli_missing_edition() -> None:
    code = main(["--edition", "missing", "--grade", "4", "--term", "1", "--unit", "1"])
    assert code == 2
