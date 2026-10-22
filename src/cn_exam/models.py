"""题库对象和一份已组好的试卷。

学生卷渲染只接收 SafeQuestion / SafeSection，其中没有答案字段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WordItem:
    word: str
    source: str
    detail: str = ""
    pinyin: str | None = None


@dataclass
class Gloss:
    term: str
    meaning: str


@dataclass
class Poem:
    title: str
    dynasty: str
    author: str
    lines: list[str]
    glosses: list[Gloss] = field(default_factory=list)
    teacher_note: str = ""
    words: list[WordItem] = field(default_factory=list)


@dataclass
class ClozeItem:
    id: str
    bank: list[str]
    text: str
    answer: str
    origin: str
    explanation: str = ""


@dataclass
class ChoiceItem:
    id: str
    kind: str
    stem: str
    options: list[str]
    answer: str
    origin: str
    explanation: str = ""


@dataclass
class ReadingQuestion:
    id: str
    stem: str
    answer: str
    explanation: str = ""


@dataclass
class ReadingPassage:
    id: str
    title: str
    origin: str
    credit: str
    paragraphs: list[str]
    questions: list[ReadingQuestion]


@dataclass
class WritingTask:
    id: str
    title: str
    prompt: str
    requirements: list[str]
    origin: str
    word_count: int


@dataclass
class Accumulation:
    """语文园地“日积月累”。只存已从课本页读到的条目，暂不单独出题。"""

    kind: str
    text: str = ""
    title: str = ""
    dynasty: str = ""
    author: str = ""
    source: str = ""
    lines: list[str] = field(default_factory=list)


@dataclass
class Lesson:
    title: str
    author: str
    author_status: str
    note: str = ""
    pieces: list[str] = field(default_factory=list)
    # 识字表、写字表的单字。recognize_review 是识字表里印成蓝色的多音字，不计入生字总数。
    recognize: list[str] = field(default_factory=list)
    recognize_review: list[str] = field(default_factory=list)
    write_chars: list[str] = field(default_factory=list)


@dataclass
class Unit:
    number: int
    title: str
    lessons: list[Lesson]
    words: list[WordItem]
    textbook_words: list[WordItem]
    poems: list[Poem]
    cloze_items: list[ClozeItem]
    choice_items: list[ChoiceItem]
    readings: list[ReadingPassage]
    writing: WritingTask | None
    note: str = ""
    garden_recognize: list[str] = field(default_factory=list)
    garden_write: list[str] = field(default_factory=list)
    garden_note: str = ""
    accumulation: list[Accumulation] = field(default_factory=list)


@dataclass
class ExamRange:
    key: str
    label: str
    units: list[int]
    duration_minutes: int
    note: str = ""
    writing: WritingTask | None = None


@dataclass
class Edition:
    id: str
    name: str
    series_label: str
    grade: int
    term: int
    book_name: str
    paper_note: str
    unit_duration_minutes: int
    todos: list[str]
    units: list[Unit]
    exam_ranges: dict[str, ExamRange]
    source_path: Path

    def unit(self, number: int) -> Unit:
        for item in self.units:
            if item.number == number:
                return item
        found = "、".join(str(item.number) for item in self.units)
        raise KeyError(f"没有第 {number} 单元，现有单元：{found}")


@dataclass
class Question:
    """组卷内部题目。答案字段不得传给学生卷渲染函数。"""

    number: int
    points: int
    kind: str
    visible_parts: list[str]
    options: list[str]
    blank_grids: list[int]
    writing_lines: int
    answer: str
    explanation: str
    hidden_parts: list[str]
    weight: int = 1
    source: str = ""


@dataclass(frozen=True)
class SafeQuestion:
    """学生卷可见内容。故意不包含答案、解析和应默写的诗句。"""

    number: int
    points: int
    kind: str
    visible_parts: tuple[str, ...]
    options: tuple[str, ...]
    blank_grids: tuple[int, ...]
    writing_lines: int


@dataclass
class Section:
    id: str
    title: str
    instruction: str
    points: int
    preamble: list[str]
    questions: list[Question]


@dataclass(frozen=True)
class SafeSection:
    id: str
    title: str
    instruction: str
    points: int
    preamble: tuple[str, ...]
    questions: tuple[SafeQuestion, ...]


@dataclass
class PaperMeta:
    edition_id: str
    edition_name: str
    series_label: str
    grade: int
    term: int
    book_name: str
    scope_label: str
    scope_detail: str
    duration_minutes: int
    total_points: int
    seed: int
    paper_note: str
    filename_stem: str


@dataclass
class Paper:
    meta: PaperMeta
    sections: list[Section]
    warnings: list[str]


@dataclass
class GenerateResult:
    paper: Paper
    student_docx: Path
    answer_docx: Path
    student_pdf: Path | None
    answer_pdf: Path | None
    warnings: list[str]


def to_safe_question(question: Question) -> SafeQuestion:
    return SafeQuestion(
        number=question.number,
        points=question.points,
        kind=question.kind,
        visible_parts=tuple(question.visible_parts),
        options=tuple(question.options),
        blank_grids=tuple(question.blank_grids),
        writing_lines=question.writing_lines,
    )


def to_safe_section(section: Section) -> SafeSection:
    return SafeSection(
        id=section.id,
        title=section.title,
        instruction=section.instruction,
        points=section.points,
        preamble=tuple(section.preamble),
        questions=tuple(to_safe_question(item) for item in section.questions),
    )


def lesson_label(lesson: Lesson) -> str:
    """卷头范围用的课名。古诗三首会带上已核对的诗题。"""
    if lesson.pieces:
        inner = "、".join(lesson.pieces)
        return f"{lesson.title}（{inner}）"
    return lesson.title
