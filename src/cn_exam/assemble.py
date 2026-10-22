"""从题库抽题、避开卷面上已经印出的答案，并分配分数。"""

from __future__ import annotations

import hashlib
import random

from cn_exam.errors import DataError, ExamError
from cn_exam.models import (
    ChoiceItem,
    ClozeItem,
    Edition,
    Paper,
    PaperMeta,
    Poem,
    Question,
    ReadingPassage,
    Section,
    Unit,
    WordItem,
    WritingTask,
    lesson_label,
)
from cn_exam.pinyin_util import words_to_pinyin
from cn_exam.points import (
    DEFAULT_TOTAL,
    SECTION_ORDER,
    allocate_section_points,
    split_points,
)

# 各题型期望小题数。题库不够时有多少用多少。
DEFAULT_COUNTS: dict[str, int] = {
    "pinyin": 8,
    "classical": 3,
    "cloze": 4,
    "choice": 6,
    "reading": 1,
    "writing": 1,
}

SECTION_TITLES = {
    "pinyin": "看拼音，写词语",
    "classical": "古诗积累",
    "cloze": "选词填空",
    "choice": "判断与选择",
    "reading": "阅读理解",
    "writing": "习作",
}

SECTION_INSTRUCTIONS = {
    "pinyin": "读拼音，把词语写在田字格里。",
    "classical": "根据题目默写或补写诗句，字迹工整。",
    "cloze": "从括号里选一个最恰当的词语，写在横线上。",
    "choice": "判断题在括号里打“√”或“×”。选择题把正确选项的字母写在括号里。",
    "reading": "阅读短文，回答问题。",
    "writing": "按要求写作。写不下可以写在背面。",
}

BLANK = "＿＿＿＿"
WRITING_LINES = 8


def default_seed(edition_id: str, grade: int, term: int, scope_key: str) -> int:
    """同一命令默认得到同一份试卷。"""
    raw = f"{edition_id}|{grade}|{term}|{scope_key}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def assemble_paper(
    edition: Edition,
    unit_numbers: list[int],
    scope_label: str,
    duration_minutes: int,
    seed: int,
    weights: dict[str, int] | None = None,
    total: int = DEFAULT_TOTAL,
    writing_override: WritingTask | None = None,
    counts: dict[str, int] | None = None,
) -> Paper:
    """组装一份试卷。学生可见文字里不写入答案字段。"""
    if not unit_numbers:
        raise ExamError("组卷范围为空")
    units = [edition.unit(number) for number in unit_numbers]
    rng = random.Random(seed)
    wanted = dict(DEFAULT_COUNTS)
    if counts:
        wanted.update(counts)

    poems = _unique_poems(units)
    classical = _build_classical(poems, wanted["classical"], rng)
    hidden = [line for question in classical for line in question.hidden_parts]

    cloze = _build_cloze(_filter_cloze(units, hidden), wanted["cloze"], rng)
    choice = _build_choice(_filter_choice(units, hidden), wanted["choice"], rng)
    reading_section_preamble, reading = _build_reading(
        _filter_reading(units, hidden),
        rng,
    )
    writing = _build_writing(writing_override, units, rng)

    scope_detail = "、".join(
        lesson_label(lesson) for unit in units for lesson in unit.lessons
    )
    visible = _visible_blob(scope_detail, classical, cloze, choice, reading, writing)
    visible += "\n".join(reading_section_preamble)
    # 大题名和作答说明会印在学生卷上。里面已经出现的词不再当作看拼音的答案。
    shown = {
        "classical": classical,
        "cloze": cloze,
        "choice": choice,
        "reading": reading,
        "writing": writing,
    }
    for key, questions in shown.items():
        if questions:
            visible += f"\n{SECTION_TITLES[key]}\n{SECTION_INSTRUCTIONS[key]}"
    visible += f"\n{SECTION_TITLES['pinyin']}\n{SECTION_INSTRUCTIONS['pinyin']}"
    word_bank = _collect_words(units)
    pinyin = _build_pinyin(word_bank, visible, wanted["pinyin"], rng)

    built: dict[str, list[Question]] = {
        "pinyin": pinyin,
        "classical": classical,
        "cloze": cloze,
        "choice": choice,
        "reading": reading,
        "writing": writing,
    }
    preambles = {key: [] for key in SECTION_ORDER}
    preambles["reading"] = reading_section_preamble

    section_points = _fit_section_points(built, weights, total)

    active = [key for key in SECTION_ORDER if built[key]]
    sections: list[Section] = []
    for key in active:
        questions = built[key]
        parts = split_points(section_points[key], [item.weight for item in questions])
        for number, (question, points) in enumerate(zip(questions, parts), start=1):
            question.number = number
            question.points = points
        instruction = _instruction(key, questions)
        sections.append(
            Section(
                id=key,
                title=SECTION_TITLES[key],
                instruction=instruction,
                points=section_points[key],
                preamble=list(preambles[key]),
                questions=questions,
            )
        )

    warnings = _warnings(word_bank, built["pinyin"], built["classical"])
    stem = _filename_stem(edition, scope_label)
    meta = PaperMeta(
        edition_id=edition.id,
        edition_name=edition.name,
        series_label=edition.series_label,
        grade=edition.grade,
        term=edition.term,
        book_name=edition.book_name,
        scope_label=scope_label,
        scope_detail=scope_detail,
        duration_minutes=duration_minutes,
        total_points=total,
        seed=seed,
        paper_note=edition.paper_note,
        filename_stem=stem,
    )
    return Paper(meta=meta, sections=sections, warnings=warnings)


def _fit_section_points(
    built: dict[str, list[Question]],
    weights: dict[str, int] | None,
    total: int,
) -> dict[str, int]:
    """小题太多时裁到每题至少 1 分，再按剩余题目重算大题分数。"""
    section_points: dict[str, int] = {}
    for _ in range(4):
        active = [key for key in SECTION_ORDER if built[key]]
        if not active:
            raise DataError("这个范围里没有可出的题目")
        counts = {key: len(built[key]) for key in active}
        section_points = allocate_section_points(active, counts, weights, total)
        changed = False
        for key in active:
            if section_points[key] <= 0:
                built[key] = []
                changed = True
                continue
            if len(built[key]) > section_points[key]:
                built[key] = built[key][: section_points[key]]
                changed = True
        if not changed:
            return section_points
    raise ExamError("分值与小题数量无法对齐")


def _instruction(key: str, questions: list[Question]) -> str:
    if key == "choice":
        kinds = {question.kind for question in questions}
        if kinds == {"judge"}:
            instruction = "在括号里打“√”或“×”。"
        elif kinds == {"single"}:
            instruction = "把正确选项的字母写在括号里。"
        else:
            instruction = SECTION_INSTRUCTIONS["choice"]
    else:
        instruction = SECTION_INSTRUCTIONS[key]
    if key == "pinyin" and any(question.source == "original_practice" for question in questions):
        instruction += "本题含自编练习词，不是教材写字表。"
    return instruction


def format_poem(lines: list[str]) -> str:
    """把不含标点的诗句排成试卷上的上下句。"""
    chunks: list[str] = []
    index = 0
    while index < len(lines):
        if index + 1 < len(lines):
            chunks.append(f"{lines[index]}，{lines[index + 1]}。")
            index += 2
        else:
            chunks.append(f"{lines[index]}。")
            index += 1
    return "\n".join(chunks)


def _filename_stem(edition: Edition, scope_label: str) -> str:
    term_name = "上册" if edition.term == 1 else "下册"
    safe_scope = scope_label.replace("/", "·").replace("\\", "·").replace(" ", "")
    return f"{edition.id}_{edition.grade}年级{term_name}_{safe_scope}"


def _warnings(words: list[WordItem], pinyin: list[Question], classical: list[Question]) -> list[str]:
    notes: list[str] = []
    if not pinyin:
        if not words:
            notes.append("未出“看拼音，写词语”：题库里还没有词语，请录入写字表。")
        else:
            notes.append("未出“看拼音，写词语”：写字表尚未录入，已印在卷面上的标题不再出默写。")
    if not classical:
        notes.append("未出“古诗积累”：本范围没有已核对的古诗。")
    return notes


def _collect_words(units: list[Unit]) -> list[WordItem]:
    """写字表优先；没有写字表时才使用标题词和诗中词语。"""
    textbook: list[WordItem] = []
    fallback: list[WordItem] = []
    for unit in units:
        textbook.extend(unit.textbook_words)
        fallback.extend(unit.words)
        for poem in unit.poems:
            fallback.extend(poem.words)
    chosen = textbook if textbook else fallback
    seen: set[str] = set()
    result: list[WordItem] = []
    for item in chosen:
        if item.word in seen:
            continue
        seen.add(item.word)
        result.append(item)
    return result


def _unique_poems(units: list[Unit]) -> list[Poem]:
    seen: set[str] = set()
    poems: list[Poem] = []
    for unit in units:
        for poem in unit.poems:
            if poem.title in seen:
                continue
            seen.add(poem.title)
            poems.append(poem)
    return poems


def _build_classical(poems: list[Poem], count: int, rng: random.Random) -> list[Question]:
    if count <= 0 or not poems:
        return []
    chosen = _shuffled(rng, poems, lambda poem: poem.title)[:count]
    questions: list[Question] = []
    for index, poem in enumerate(chosen):
        if index == 0:
            questions.append(_dictation(poem))
        else:
            questions.append(_couplet(poem))
    return questions


def _dictation(poem: Poem) -> Question:
    return Question(
        number=0,
        points=0,
        kind="classical",
        visible_parts=[
            f"默写《{poem.title}》。",
            f"【{poem.dynasty}】{poem.author}",
        ],
        options=[],
        blank_grids=[len(line) for line in poem.lines],
        writing_lines=0,
        answer=format_poem(poem.lines),
        explanation=_poem_note(poem),
        hidden_parts=list(poem.lines),
        weight=2,
        source="public_domain",
    )


def _couplet(poem: Poem) -> Question:
    split_at = len(poem.lines) // 2
    shown = poem.lines[:split_at]
    hidden = poem.lines[split_at:]
    return Question(
        number=0,
        points=0,
        kind="classical",
        visible_parts=[
            f"补写《{poem.title}》的后半首。",
            f"【{poem.dynasty}】{poem.author}",
            format_poem(shown),
        ],
        options=[],
        blank_grids=[len(line) for line in hidden],
        writing_lines=0,
        answer=format_poem(hidden),
        explanation=_poem_note(poem),
        hidden_parts=list(hidden),
        weight=1,
        source="public_domain",
    )


def _poem_note(poem: Poem) -> str:
    parts = [f"《{poem.title}》{poem.dynasty}·{poem.author}"]
    if poem.teacher_note:
        parts.append(poem.teacher_note)
    for gloss in poem.glosses:
        parts.append(f"{gloss.term}：{gloss.meaning}")
    return " ".join(parts)


def _filter_cloze(units: list[Unit], hidden: list[str]) -> list[ClozeItem]:
    items: list[ClozeItem] = []
    for unit in units:
        for item in unit.cloze_items:
            blob = item.text + "".join(item.bank)
            if _contains_hidden(blob, hidden):
                continue
            items.append(item)
    return items


def _filter_choice(units: list[Unit], hidden: list[str]) -> list[ChoiceItem]:
    items: list[ChoiceItem] = []
    for unit in units:
        for item in unit.choice_items:
            blob = item.stem + "".join(item.options)
            if _contains_hidden(blob, hidden):
                continue
            items.append(item)
    return items


def _filter_reading(units: list[Unit], hidden: list[str]) -> list[ReadingPassage]:
    passages: list[ReadingPassage] = []
    for unit in units:
        for passage in unit.readings:
            blob = passage.title + "".join(passage.paragraphs)
            blob += "".join(question.stem for question in passage.questions)
            if _contains_hidden(blob, hidden):
                continue
            passages.append(passage)
    return passages


def _contains_hidden(text: str, hidden: list[str]) -> bool:
    compact = _compact(text)
    return any(_compact(line) in compact for line in hidden)


def _compact(text: str) -> str:
    drop = " \t\n\r，。、“”\"'‘’！？：；,.　"
    return "".join(char for char in text if char not in drop)


def _build_cloze(items: list[ClozeItem], count: int, rng: random.Random) -> list[Question]:
    chosen = _shuffled(rng, items, lambda item: item.id)[:count]
    questions: list[Question] = []
    for item in chosen:
        bank = "　".join(item.bank)
        sentence = item.text.replace("____", BLANK)
        questions.append(
            Question(
                number=0,
                points=0,
                kind="cloze",
                visible_parts=[f"（{bank}）{sentence}"],
                options=[],
                blank_grids=[],
                writing_lines=0,
                answer=item.answer,
                explanation=item.explanation,
                hidden_parts=[],
                source=item.origin,
            )
        )
    return questions


def _build_choice(items: list[ChoiceItem], count: int, rng: random.Random) -> list[Question]:
    chosen = _shuffled(rng, items, lambda item: item.id)[:count]
    # 判断题在前，选择题在后；同一类内部保持打乱后的顺序。
    chosen.sort(key=lambda item: 0 if item.kind == "judge" else 1)
    questions: list[Question] = []
    for item in chosen:
        if item.kind == "judge":
            answer = "√" if item.answer == "对" else "×"
            explanation = f"判断为“{item.answer}”。{item.explanation}".strip()
            options: list[str] = []
        else:
            index = ord(item.answer) - ord("A")
            answer = f"{item.answer}（{item.options[index]}）"
            explanation = item.explanation
            options = list(item.options)
        questions.append(
            Question(
                number=0,
                points=0,
                kind=item.kind,
                visible_parts=[item.stem],
                options=options,
                blank_grids=[],
                writing_lines=0,
                answer=answer,
                explanation=explanation,
                hidden_parts=[],
                source=item.origin,
            )
        )
    return questions


def _build_reading(
    passages: list[ReadingPassage],
    rng: random.Random,
) -> tuple[list[str], list[Question]]:
    if not passages:
        return [], []
    passage = _shuffled(rng, passages, lambda item: item.id)[0]
    preamble = [f"《{passage.title}》（{passage.credit}）", *passage.paragraphs]
    questions = [
        Question(
            number=0,
            points=0,
            kind="reading",
            visible_parts=[item.stem],
            options=[],
            blank_grids=[],
            writing_lines=0,
            answer=item.answer,
            explanation=item.explanation or "意思相近即可。",
            hidden_parts=[],
            source=passage.origin,
        )
        for item in passage.questions
    ]
    return preamble, questions


def _build_writing(
    override: WritingTask | None,
    units: list[Unit],
    rng: random.Random,
) -> list[Question]:
    task = override
    if task is None:
        tasks = [unit.writing for unit in units if unit.writing is not None]
        if not tasks:
            return []
        task = _shuffled(rng, tasks, lambda item: item.id)[0]
    requirement_lines = [f"{index}. {line}" for index, line in enumerate(task.requirements, start=1)]
    visible = [
        task.prompt,
        "要求：",
        *requirement_lines,
        f"不少于{task.word_count}字。",
    ]
    rubric = (
        "无唯一标准答案。评分看是否切合题意、内容具体、顺序清楚、语句通顺、"
        f"标点基本正确，并达到约{task.word_count}字。可按优良中弱四档给分。"
    )
    return [
        Question(
            number=0,
            points=0,
            kind="writing",
            visible_parts=visible,
            options=[],
            blank_grids=[],
            writing_lines=WRITING_LINES,
            answer="见评分建议，不设范文。",
            explanation=rubric,
            hidden_parts=[],
            source=task.origin,
        )
    ]


def _build_pinyin(
    words: list[WordItem],
    visible: str,
    count: int,
    rng: random.Random,
) -> list[Question]:
    hidden_words = [item for item in words if item.word not in visible]
    chosen = _shuffled(rng, hidden_words, lambda item: item.word)[:count]
    questions: list[Question] = []
    for item in chosen:
        questions.append(
            Question(
                number=0,
                points=0,
                kind="pinyin",
                visible_parts=[words_to_pinyin(item.word, item.pinyin)],
                options=[],
                blank_grids=[len(item.word)],
                writing_lines=0,
                answer=item.word,
                explanation=item.detail,
                hidden_parts=[item.word],
                source=item.source,
            )
        )
    return questions


def _visible_blob(scope_detail: str, *groups: list[Question]) -> str:
    parts = [scope_detail]
    for group in groups:
        for question in group:
            parts.extend(question.visible_parts)
            parts.extend(question.options)
    return "\n".join(parts)


def _shuffled(rng: random.Random, items: list, key) -> list:
    ordered = sorted(items, key=key)
    rng.shuffle(ordered)
    return ordered
