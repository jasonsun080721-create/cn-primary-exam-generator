"""学生卷不得出现答案字段、隐藏诗句和答案卷专有说明。"""

from pathlib import Path

import yaml
from dataclasses import fields

from cn_exam import generate_exam
from cn_exam.models import SafeQuestion, SafeSection
from tests.docx_util import docx_text


def test_safe_models_have_no_answer_fields() -> None:
    safe_question = {item.name for item in fields(SafeQuestion)}
    safe_section = {item.name for item in fields(SafeSection)}
    for name in ("answer", "explanation", "hidden_parts"):
        assert name not in safe_question
        assert name not in safe_section


def test_real_papers_hide_answers_and_dictation(tmp_path: Path) -> None:
    for seed in range(5):
        result = generate_exam(
            edition="rj2026",
            grade=4,
            term=1,
            unit=3,
            seed=seed,
            output_dir=tmp_path / str(seed),
            export_pdf_files=False,
        )
        student = docx_text(result.student_docx)
        answer = docx_text(result.answer_docx)
        assert "答案：" not in student
        assert "参考答案" not in student
        assert "卢梅坡" not in student
        assert "答案：" in answer
        assert "参考答案" in answer
        assert "卢梅坡" in answer
        question_count = sum(len(section.questions) for section in result.paper.sections)
        assert answer.count("答案：") == question_count
        for section in result.paper.sections:
            for question in section.questions:
                for hidden in question.hidden_parts:
                    assert hidden not in student
                    assert hidden in answer
                assert f"答案：{question.answer.split(chr(10))[0]}" not in student


def test_sentinel_answers_stay_out_of_student_file(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _write_sentinel_bank(data_dir)
    result = generate_exam(
        edition="sentinel",
        grade=4,
        term=1,
        unit=1,
        output_dir=tmp_path / "out",
        data_dir=data_dir,
        export_pdf_files=False,
        seed=1,
    )
    student = docx_text(result.student_docx)
    answer = docx_text(result.answer_docx)
    for secret in ("哨兵词", "哨兵诗句一二三", "只有答案卷才有的哨兵说明"):
        assert secret not in student
        assert secret in answer
    assert "答案：" not in student


def _write_sentinel_bank(data_dir: Path) -> None:
    payload = {
        "schema_version": 1,
        "edition": {
            "id": "sentinel",
            "name": "哨兵版",
            "series_label": "测试",
            "grade": 4,
            "term": 1,
            "book_name": "四年级上册",
        },
        "paper_note": "测试卷",
        "unit_duration_minutes": 40,
        "exam_ranges": {
            "midterm": {"label": "期中", "units": [1], "duration_minutes": 40},
            "final": {"label": "期末", "units": [1], "duration_minutes": 40},
        },
        "units": [
            {
                "number": 1,
                "title": "第1单元",
                "lessons": [{"title": "普通课文", "author_status": "todo"}],
                "words": [],
                "textbook_words": [
                    {
                        "word": "哨兵词",
                        "source": "textbook",
                        "detail": "只有答案卷才有的哨兵说明",
                    }
                ],
                "poems": [
                    {
                        "title": "哨兵诗",
                        "dynasty": "唐",
                        "author": "测试",
                        "lines": [
                            "哨兵诗句一二三",
                            "甲乙丙丁戊己庚",
                            "辛壬癸子丑寅卯",
                            "辰巳午未申酉戌",
                        ],
                        "teacher_note": "只有答案卷才有的哨兵说明",
                    }
                ],
                "cloze_items": [
                    {
                        "id": "c1",
                        "bank": ["安静", "热闹"],
                        "text": "院子里很____。",
                        "answer": "安静",
                        "origin": "original_practice",
                    }
                ],
                "choice_items": [
                    {
                        "id": "q1",
                        "kind": "judge",
                        "stem": "普通课文是一篇课文。",
                        "answer": "对",
                        "origin": "original_practice",
                        "explanation": "只有答案卷才有的哨兵说明",
                    }
                ],
                "readings": [],
            }
        ],
    }
    folder = data_dir / "sentinel"
    folder.mkdir(parents=True)
    path = folder / "grade4_term1.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
