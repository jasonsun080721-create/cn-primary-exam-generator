"""组卷结果：文件、满分、题型和拼音。"""

from pathlib import Path

import pytest

from cn_exam import generate_exam
from cn_exam.generate import parse_unit_spec
from cn_exam.pinyin_util import words_to_pinyin
from tests.docx_util import docx_text, has_embedded_image


def test_pinyin_known_words() -> None:
    assert words_to_pinyin("观潮") == "guān cháo"
    assert words_to_pinyin("繁星") == "fán xīng"
    assert words_to_pinyin("女娲") == "nǚ wā"
    assert words_to_pinyin("阁笔", "gē bǐ") == "gē bǐ"


def test_parse_unit_spec() -> None:
    assert parse_unit_spec("1-3") == [1, 2, 3]
    assert parse_unit_spec("1,3") == [1, 3]
    assert parse_unit_spec("1-2,4") == [1, 2, 4]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"unit": 1},
        {"unit": 2},
        {"unit": 3},
        {"unit": 4},
        {"unit": 5},
        {"unit": 6},
        {"unit": 7},
        {"unit": 8},
        {"exam": "midterm"},
        {"exam": "final"},
        {"units": "1-8"},
    ],
)
def test_scopes_score_one_hundred(tmp_path: Path, kwargs: dict) -> None:
    result = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        output_dir=tmp_path,
        export_pdf_files=False,
        **kwargs,
    )
    paper = result.paper
    assert result.student_docx.is_file()
    assert result.answer_docx.is_file()
    assert paper.meta.total_points == 100
    assert sum(section.points for section in paper.sections) == 100
    question_points = [
        question.points
        for section in paper.sections
        for question in section.questions
    ]
    assert sum(question_points) == 100
    assert all(points >= 1 for points in question_points)
    assert "答案：" not in docx_text(result.student_docx)


def test_unit1_has_header_and_no_classical(tmp_path: Path) -> None:
    result = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        unit=1,
        output_dir=tmp_path,
        export_pdf_files=False,
    )
    text = docx_text(result.student_docx)
    assert "第1单元练习卷" in text
    assert "姓名：" in text
    assert "班级：" in text
    assert "得分：" in text
    assert "观潮" in text
    assert "繁星" in text
    section_ids = [section.id for section in result.paper.sections]
    assert "classical" not in section_ids
    assert "pinyin" in section_ids
    assert "秋晚的江上" in text
    pinyin = next(section for section in result.paper.sections if section.id == "pinyin")
    for question in pinyin.questions:
        assert question.answer not in text
    assert "cloze" in section_ids
    assert "choice" in section_ids
    assert "reading" in section_ids
    assert "writing" in section_ids
    assert "w:w=" in _page_size_xml(result.student_docx)


def test_unit3_has_poems_pinyin_and_grids(tmp_path: Path) -> None:
    result = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        unit=3,
        output_dir=tmp_path,
        export_pdf_files=False,
    )
    ids = [section.id for section in result.paper.sections]
    assert "classical" in ids
    assert "pinyin" in ids
    pinyin = next(section for section in result.paper.sections if section.id == "pinyin")
    assert pinyin.questions
    assert all(question.points <= 2 for question in pinyin.questions)
    assert has_embedded_image(result.student_docx)
    student = docx_text(result.student_docx)
    for question in pinyin.questions:
        assert question.visible_parts[0] in student
        assert question.answer not in student


def test_custom_section_weights(tmp_path: Path) -> None:
    result = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        unit=1,
        output_dir=tmp_path,
        export_pdf_files=False,
        section_points={"reading": 50, "writing": 30, "cloze": 10, "choice": 10},
    )
    points = {section.id: section.points for section in result.paper.sections}
    assert sum(points.values()) == 100
    assert points["reading"] > points["cloze"]
    assert points["writing"] > points["choice"]


def test_same_seed_is_stable(tmp_path: Path) -> None:
    first = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        unit=3,
        output_dir=tmp_path / "a",
        seed=7,
        export_pdf_files=False,
    )
    second = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        unit=3,
        output_dir=tmp_path / "b",
        seed=7,
        export_pdf_files=False,
    )
    assert _answers(first) == _answers(second)


def test_default_seed_is_stable(tmp_path: Path) -> None:
    first = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        unit=1,
        output_dir=tmp_path / "a",
        export_pdf_files=False,
    )
    second = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        unit=1,
        output_dir=tmp_path / "b",
        export_pdf_files=False,
    )
    assert first.paper.meta.seed == second.paper.meta.seed
    assert _answers(first) == _answers(second)


def test_midterm_does_not_use_later_units(tmp_path: Path) -> None:
    result = generate_exam(
        edition="rj2026",
        grade=4,
        term=1,
        exam="midterm",
        output_dir=tmp_path,
        export_pdf_files=False,
    )
    detail = result.paper.meta.scope_detail
    assert "观潮" in detail
    assert "盘古开天地" in detail
    assert "女娲补天" in detail
    assert "长城" not in detail
    assert "凉州词" not in detail
    answer = docx_text(result.answer_docx)
    assert "凉州词" not in answer
    assert "李清照" not in answer
    assert "答案：" in answer


def _answers(result) -> list[str]:
    return [
        question.answer
        for section in result.paper.sections
        for question in section.questions
    ]


def _page_size_xml(path: Path) -> str:
    import zipfile

    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    start = xml.find("<w:pgSz")
    assert start != -1
    return xml[start:start + 80]
