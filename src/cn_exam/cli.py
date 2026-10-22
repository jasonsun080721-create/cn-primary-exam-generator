"""cn-exam 命令行。"""

from __future__ import annotations

import argparse
import sys

from cn_exam import __version__
from cn_exam.errors import DataError, ExamError
from cn_exam.generate import generate_exam
from cn_exam.loader import list_edition_files, load_edition
from cn_exam.points import SECTION_ORDER


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.list:
            _print_editions(args.data_dir)
            return 0
        if args.edition is None or args.grade is None or args.term is None:
            parser.error("生成试卷时必须提供 --edition、--grade 和 --term")
        points = _parse_points(args.points) if args.points else None
        result = generate_exam(
            edition=args.edition,
            grade=args.grade,
            term=args.term,
            unit=args.unit,
            exam=args.exam,
            units=args.units,
            output_dir=args.output,
            data_dir=args.data_dir,
            seed=args.seed,
            section_points=points,
            total=args.total,
            export_pdf_files=not args.no_pdf,
        )
    except (DataError, ExamError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"学生卷：{result.student_docx}")
    print(f"答案卷：{result.answer_docx}")
    if result.student_pdf:
        print(f"学生卷 PDF：{result.student_pdf}")
    if result.answer_pdf:
        print(f"答案卷 PDF：{result.answer_pdf}")
    print(f"满分：{result.paper.meta.total_points}　种子：{result.paper.meta.seed}")
    for warning in result.warnings:
        print(f"提示：{warning}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cn-exam",
        description="小学语文试卷生成器。按版本、年级、学期和单元生成学生卷与答案卷。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  cn-exam --edition rj2026 --grade 4 --term 1 --unit 1\n"
            "  cn-exam --edition rj2026 --grade 4 --term 1 --unit 3\n"
            "  cn-exam --edition rj2026 --grade 4 --term 1 --exam midterm\n"
            "  cn-exam --edition rj2026 --grade 4 --term 1 --exam final\n"
            "  cn-exam --list\n"
        ),
    )
    parser.add_argument("--edition", help="教材版本编号，例如 rj2026")
    parser.add_argument("--grade", type=int, help="年级，例如 4")
    parser.add_argument("--term", type=int, choices=(1, 2), help="学期，1 为上册，2 为下册")
    parser.add_argument("--unit", type=int, help="单个单元编号")
    parser.add_argument("--units", help="单元范围，例如 1-2 或 1,3")
    parser.add_argument("--exam", choices=("midterm", "final"), help="期中 midterm 或期末 final")
    parser.add_argument("--output", default="out", help="输出目录，默认 out")
    parser.add_argument("--data-dir", help="题库目录，默认自动查找 data/")
    parser.add_argument("--seed", type=int, help="随机种子。省略时按版本和范围固定")
    parser.add_argument("--total", type=int, default=100, help="满分，默认 100")
    parser.add_argument(
        "--points",
        help="题型权重，例如 pinyin=16,classical=18,cloze=12,choice=12,reading=24,writing=18",
    )
    parser.add_argument("--no-pdf", action="store_true", help="不尝试调用 LibreOffice 转 PDF")
    parser.add_argument("--list", action="store_true", help="列出已安装的题库")
    parser.add_argument("--version", action="version", version=f"cn-exam {__version__}")
    return parser


def _parse_points(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for part in text.split(","):
        piece = part.strip()
        if not piece:
            continue
        if "=" not in piece:
            raise ExamError(f"无法解析题型分值：{piece}")
        key, value = piece.split("=", 1)
        name = key.strip()
        if name not in SECTION_ORDER:
            allowed = "、".join(SECTION_ORDER)
            raise ExamError(f"未知题型 {name}。可用：{allowed}")
        result[name] = int(value.strip())
    if not result:
        raise ExamError("题型分值为空")
    return result


def _print_editions(data_dir: str | None) -> None:
    files = list_edition_files(data_dir)
    if not files:
        print("没有找到题库。")
        return
    seen: set[tuple[str, int, int]] = set()
    for path in files:
        edition_id = path.parent.name
        stem = path.stem
        if not stem.startswith("grade") or "_term" not in stem:
            continue
        grade_text, term_text = stem.removeprefix("grade").split("_term", 1)
        grade = int(grade_text)
        term = int(term_text)
        key = (edition_id, grade, term)
        if key in seen:
            continue
        seen.add(key)
        book = load_edition(edition_id, grade, term, data_dir=data_dir)
        numbers = "、".join(str(unit.number) for unit in book.units)
        term_name = "上册" if term == 1 else "下册"
        print(f"{book.id}  {book.name}  {grade}年级{term_name}  {book.series_label}  单元：{numbers}")
        for todo in book.todos:
            print(f"  待补：{todo}")


if __name__ == "__main__":
    sys.exit(main())
