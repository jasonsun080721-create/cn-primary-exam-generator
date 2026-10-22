"""对外组卷入口。"""

from __future__ import annotations

from pathlib import Path

from cn_exam.assemble import assemble_paper, default_seed
from cn_exam.errors import ExamError
from cn_exam.loader import load_edition
from cn_exam.models import Edition, GenerateResult
from cn_exam.pdf_export import export_pdf
from cn_exam.points import DEFAULT_TOTAL
from cn_exam.render_docx import render_answer, render_student


def generate_exam(
    edition: str,
    grade: int,
    term: int,
    unit: int | None = None,
    exam: str | None = None,
    units: str | None = None,
    output_dir: str | Path = "out",
    data_dir: str | Path | None = None,
    seed: int | None = None,
    section_points: dict[str, int] | None = None,
    total: int = DEFAULT_TOTAL,
    export_pdf_files: bool = True,
) -> GenerateResult:
    """生成学生卷和答案卷。

    unit、exam、units 只能选一种。exam 取题库里的 midterm 或 final。
    """
    book = load_edition(edition, grade, term, data_dir=data_dir)
    scope = _resolve_scope(book, unit=unit, exam=exam, units=units)
    resolved_seed = seed
    if resolved_seed is None:
        resolved_seed = default_seed(book.id, book.grade, book.term, scope["key"])
    paper = assemble_paper(
        edition=book,
        unit_numbers=scope["units"],
        scope_label=scope["label"],
        duration_minutes=scope["duration"],
        seed=resolved_seed,
        weights=section_points,
        total=total,
        writing_override=scope["writing"],
    )
    output = Path(output_dir)
    student_path = output / f"{paper.meta.filename_stem}_学生卷.docx"
    answer_path = output / f"{paper.meta.filename_stem}_答案.docx"
    render_student(paper, student_path)
    render_answer(paper, answer_path)
    warnings = list(paper.warnings)
    student_pdf = None
    answer_pdf = None
    if export_pdf_files:
        student_pdf, student_warning = export_pdf(student_path)
        answer_pdf, answer_warning = export_pdf(answer_path)
        for warning in (student_warning, answer_warning):
            if warning and warning not in warnings:
                warnings.append(warning)
    return GenerateResult(
        paper=paper,
        student_docx=student_path,
        answer_docx=answer_path,
        student_pdf=student_pdf,
        answer_pdf=answer_pdf,
        warnings=warnings,
    )


def _resolve_scope(
    book: Edition,
    unit: int | None,
    exam: str | None,
    units: str | None,
) -> dict:
    chosen = [item is not None for item in (unit, exam, units)]
    if sum(chosen) != 1:
        raise ExamError("请在 --unit、--units、--exam 中选择一种范围")
    if unit is not None:
        _require_unit(book, unit)
        return {
            "key": f"unit-{unit}",
            "label": f"第{unit}单元练习卷",
            "units": [unit],
            "duration": book.unit_duration_minutes,
            "writing": None,
        }
    if units is not None:
        numbers = parse_unit_spec(units)
        for number in numbers:
            _require_unit(book, number)
        if len(numbers) == 1:
            label = f"第{numbers[0]}单元练习卷"
        else:
            label = f"第{numbers[0]}–{numbers[-1]}单元练习卷"
        return {
            "key": "units-" + "-".join(str(number) for number in numbers),
            "label": label,
            "units": numbers,
            "duration": book.unit_duration_minutes if len(numbers) == 1 else 90,
            "writing": None,
        }
    if exam not in book.exam_ranges:
        raise ExamError("exam 只能是 midterm 或 final")
    spec = book.exam_ranges[exam]
    suffix = "期中测试卷" if exam == "midterm" else "期末测试卷"
    return {
        "key": exam,
        "label": suffix,
        "units": list(spec.units),
        "duration": spec.duration_minutes,
        "writing": spec.writing,
    }


def _require_unit(book: Edition, number: int) -> None:
    try:
        book.unit(number)
    except KeyError as exc:
        raise ExamError(str(exc)) from exc


def parse_unit_spec(text: str) -> list[int]:
    """解析 1、1-3、1,3、1-2,4。"""
    numbers: list[int] = []
    for part in text.split(","):
        piece = part.strip()
        if not piece:
            continue
        if "-" in piece:
            start_text, end_text = piece.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if end < start:
                raise ExamError(f"单元范围无效：{piece}")
            numbers.extend(range(start, end + 1))
        else:
            numbers.append(int(piece))
    if not numbers:
        raise ExamError("单元范围为空")
    unique: list[int] = []
    for number in numbers:
        if number not in unique:
            unique.append(number)
    return unique
