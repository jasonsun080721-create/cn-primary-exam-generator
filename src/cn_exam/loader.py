"""读取 YAML / JSON 题库并做结构校验。"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from cn_exam.errors import DataError
from cn_exam.models import (
    Accumulation,
    ChoiceItem,
    ClozeItem,
    Edition,
    ExamRange,
    Gloss,
    Lesson,
    Poem,
    ReadingPassage,
    ReadingQuestion,
    Unit,
    WordItem,
    WritingTask,
)
from cn_exam.paths import find_data_dir

SCHEMA_VERSION = 1
WORD_SOURCES = {"textbook", "lesson_title", "poem", "content_fact", "original_practice"}
ORIGINS = {"original_practice", "textbook", "public_domain", "content_fact"}
AUTHOR_STATUS = {"verified", "todo"}
HAN_WORD = re.compile(r"[\u4e00-\u9fff·]{2,8}")
HAN_CHAR = re.compile(r"[\u4e00-\u9fff]")
ACCUMULATION_KINDS = {"poem", "quotation", "saying"}


def list_edition_files(data_dir: str | Path | None = None) -> list[Path]:
    """列出 data/<版本>/gradeN_termN.yaml|yml|json。忽略下划线开头的目录。"""
    root = find_data_dir(data_dir)
    files: list[Path] = []
    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith(("_", ".")):
            continue
        for path in sorted(folder.iterdir()):
            if path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            if path.name.startswith("_"):
                continue
            files.append(path)
    return files


def load_edition(
    edition_id: str,
    grade: int,
    term: int,
    data_dir: str | Path | None = None,
) -> Edition:
    root = find_data_dir(data_dir)
    path = _resolve_file(root, edition_id, grade, term)
    payload = _parse(path)
    edition = _build_edition(payload, path)
    if edition.id != edition_id:
        raise DataError(f"{path} 的 edition.id 是 {edition.id}，与目录 {edition_id} 不一致")
    if edition.grade != grade or edition.term != term:
        raise DataError(
            f"{path} 的年级或学期与文件名不一致："
            f"文件内为 {edition.grade} 年级第 {edition.term} 学期"
        )
    return edition


def _resolve_file(root: Path, edition_id: str, grade: int, term: int) -> Path:
    folder = root / edition_id
    if not folder.is_dir():
        known = "、".join(item.name for item in sorted(root.iterdir()) if item.is_dir())
        raise DataError(f"没有版本 {edition_id}。已有目录：{known or '（空）'}")
    stem = f"grade{grade}_term{term}"
    for suffix in (".yaml", ".yml", ".json"):
        path = folder / f"{stem}{suffix}"
        if path.is_file():
            return path
    raise DataError(f"找不到 {folder / stem}.yaml（也接受 .yml / .json）")


def _parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise DataError(f"{path} 的顶层必须是映射")
    return data


def _build_edition(data: dict, path: Path) -> Edition:
    _keys(
        data,
        allowed={
            "schema_version",
            "edition",
            "exam_ranges",
            "unit_duration_minutes",
            "todos",
            "paper_note",
            "units",
        },
        required={
            "schema_version",
            "edition",
            "exam_ranges",
            "unit_duration_minutes",
            "paper_note",
            "units",
        },
        where=str(path),
    )
    if data["schema_version"] != SCHEMA_VERSION:
        raise DataError(f"{path} 的 schema_version 必须为 {SCHEMA_VERSION}")
    meta = _mapping(data["edition"], f"{path} edition")
    _keys(
        meta,
        allowed={"id", "name", "series_label", "grade", "term", "book_name"},
        required={"id", "name", "series_label", "grade", "term", "book_name"},
        where=f"{path} edition",
    )
    ranges = _ranges(data["exam_ranges"], path)
    units = [_unit(item, path) for item in _list(data["units"], f"{path} units")]
    numbers = [item.number for item in units]
    if len(numbers) != len(set(numbers)):
        raise DataError(f"{path} 单元编号重复")
    for item in ranges.values():
        for number in item.units:
            if number not in numbers:
                raise DataError(f"{path} 的 {item.key} 引用了不存在的第 {number} 单元")
    todos = [str(item) for item in data.get("todos", [])]
    return Edition(
        id=str(meta["id"]).strip(),
        name=str(meta["name"]).strip(),
        series_label=str(meta["series_label"]).strip(),
        grade=_int(meta["grade"], f"{path} grade"),
        term=_int(meta["term"], f"{path} term"),
        book_name=str(meta["book_name"]).strip(),
        paper_note=str(data["paper_note"]).strip(),
        unit_duration_minutes=_int(data["unit_duration_minutes"], f"{path} duration"),
        todos=todos,
        units=units,
        exam_ranges=ranges,
        source_path=path,
    )


def _ranges(raw: object, path: Path) -> dict[str, ExamRange]:
    mapping = _mapping(raw, f"{path} exam_ranges")
    _keys(
        mapping,
        allowed={"midterm", "final"},
        required={"midterm", "final"},
        where=f"{path} exam_ranges",
    )
    built: dict[str, ExamRange] = {}
    for key in ("midterm", "final"):
        item = _mapping(mapping[key], f"{path} {key}")
        _keys(
            item,
            allowed={"label", "units", "duration_minutes", "note", "writing"},
            required={"label", "units", "duration_minutes"},
            where=f"{path} {key}",
        )
        writing = None
        if "writing" in item and item["writing"] is not None:
            writing = _writing(item["writing"], f"{path} {key}.writing")
        units = [_int(number, f"{path} {key}.units") for number in _list(item["units"], key)]
        if not units:
            raise DataError(f"{path} 的 {key} 没有单元")
        built[key] = ExamRange(
            key=key,
            label=str(item["label"]).strip(),
            units=units,
            duration_minutes=_int(item["duration_minutes"], f"{path} {key}.duration"),
            note=str(item.get("note", "")).strip(),
            writing=writing,
        )
    return built


def _unit(raw: object, path: Path) -> Unit:
    item = _mapping(raw, f"{path} unit")
    _keys(
        item,
        allowed={
            "number",
            "title",
            "lessons",
            "words",
            "textbook_words",
            "poems",
            "cloze_items",
            "choice_items",
            "readings",
            "writing",
            "note",
            "garden_recognize",
            "garden_write",
            "garden_note",
            "accumulation",
        },
        required={
            "number",
            "title",
            "lessons",
            "words",
            "textbook_words",
            "poems",
            "cloze_items",
            "choice_items",
            "readings",
        },
        where=f"{path} unit",
    )
    number = _int(item["number"], "unit.number")
    where = f"{path} 第{number}单元"
    lessons = [_lesson(row, where) for row in _list(item["lessons"], where)]
    words = [_word(row, where, default_source=None) for row in _list(item["words"], where)]
    textbook = [
        _word(row, where, default_source="textbook")
        for row in _list(item["textbook_words"], where)
    ]
    poems = [_poem(row, where) for row in _list(item["poems"], where)]
    cloze = [_cloze(row, where) for row in _list(item["cloze_items"], where)]
    choices = [_choice(row, where) for row in _list(item["choice_items"], where)]
    readings = [_reading(row, where) for row in _list(item["readings"], where)]
    writing = None
    if item.get("writing") is not None:
        writing = _writing(item["writing"], where)
    ids = [row.id for row in cloze + choices + readings]
    ids.extend(question.id for passage in readings for question in passage.questions)
    if writing is not None:
        ids.append(writing.id)
    if len(ids) != len(set(ids)):
        raise DataError(f"{where} 存在重复 id")
    garden_recognize = _han_chars(item.get("garden_recognize", ""), where, "语文园地识字")
    garden_write = _han_chars(item.get("garden_write", ""), where, "语文园地写字")
    raw_accumulation = item.get("accumulation", [])
    if not isinstance(raw_accumulation, list):
        raise DataError(f"{where} accumulation 必须是列表")
    accumulation = [_accumulation(row, where) for row in raw_accumulation]
    return Unit(
        number=number,
        title=str(item["title"]).strip(),
        lessons=lessons,
        words=words,
        textbook_words=textbook,
        poems=poems,
        cloze_items=cloze,
        choice_items=choices,
        readings=readings,
        writing=writing,
        note=str(item.get("note", "")).strip(),
        garden_recognize=garden_recognize,
        garden_write=garden_write,
        garden_note=str(item.get("garden_note", "")).strip(),
        accumulation=accumulation,
    )


def _lesson(raw: object, where: str) -> Lesson:
    item = _mapping(raw, where)
    _keys(
        item,
        allowed={
            "title",
            "author",
            "author_status",
            "note",
            "pieces",
            "recognize",
            "recognize_review",
            "write_chars",
        },
        required={"title", "author_status"},
        where=where,
    )
    status = str(item["author_status"])
    if status not in AUTHOR_STATUS:
        raise DataError(f"{where} author_status 只能是 verified 或 todo")
    author = str(item.get("author") or "").strip()
    if status == "verified" and not author:
        raise DataError(f"{where} 课文《{item['title']}》标记为已核对作者，但作者为空")
    pieces = [str(piece).strip() for piece in item.get("pieces", [])]
    title = str(item["title"]).strip()
    recognize = _han_chars(item.get("recognize", ""), where, f"《{title}》识字")
    review = _han_chars(item.get("recognize_review", ""), where, f"《{title}》多音字")
    extra = [char for char in review if char not in recognize]
    if extra:
        raise DataError(f"{where}《{title}》蓝色多音字不在识字表中：{''.join(extra)}")
    return Lesson(
        title=title,
        author=author,
        author_status=status,
        note=str(item.get("note", "")).strip(),
        pieces=pieces,
        recognize=recognize,
        recognize_review=review,
        write_chars=_han_chars(item.get("write_chars", ""), where, f"《{title}》写字"),
    )


def _han_chars(raw: object, where: str, label: str) -> list[str]:
    """识字表、写字表收单个汉字。字符串和列表都可以，空值表示该课没有这一栏。"""
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        chars = [char for char in raw if not char.isspace()]
    elif isinstance(raw, list):
        chars = [str(char).strip() for char in raw if str(char).strip()]
    else:
        raise DataError(f"{where} {label} 应为字符串或汉字列表")
    for char in chars:
        if HAN_CHAR.fullmatch(char) is None:
            raise DataError(f"{where} {label} 须为单个汉字：{char}")
    if len(chars) != len(set(chars)):
        raise DataError(f"{where} {label} 有重复的字")
    return chars


def _accumulation(raw: object, where: str) -> Accumulation:
    item = _mapping(raw, f"{where} 日积月累")
    _keys(
        item,
        allowed={"kind", "text", "title", "dynasty", "author", "source", "lines"},
        required={"kind"},
        where=f"{where} 日积月累",
    )
    kind = str(item["kind"]).strip()
    if kind not in ACCUMULATION_KINDS:
        raise DataError(f"{where} 日积月累 kind 无效：{kind}")
    lines = [str(line).strip() for line in item.get("lines", [])]
    text = str(item.get("text", "")).strip()
    title = str(item.get("title", "")).strip()
    if kind == "poem":
        if not title or not str(item.get("author", "")).strip() or len(lines) < 2:
            raise DataError(f"{where} 日积月累古诗需要 title、author 和诗句")
        for line in lines:
            if re.fullmatch(r"[\u4e00-\u9fff]+", line) is None or len(line) not in {5, 7}:
                raise DataError(f"{where} 日积月累《{title}》诗句须为五言或七言且不含标点：{line}")
    elif not text:
        raise DataError(f"{where} 日积月累缺少正文")
    return Accumulation(
        kind=kind,
        text=text,
        title=title,
        dynasty=str(item.get("dynasty", "")).strip(),
        author=str(item.get("author", "")).strip(),
        source=str(item.get("source", "")).strip(),
        lines=lines,
    )


def _word(raw: object, where: str, default_source: str | None) -> WordItem:
    item = _mapping(raw, where)
    _keys(
        item,
        allowed={"word", "source", "detail", "pinyin"},
        required={"word"},
        where=where,
    )
    word = str(item["word"]).strip()
    if HAN_WORD.fullmatch(word) is None:
        raise DataError(f"{where} 词语应为 2–8 个汉字：{word}")
    source = str(item.get("source") or default_source or "")
    if source not in WORD_SOURCES:
        raise DataError(f"{where} 词语《{word}》的 source 无效：{source}")
    pinyin = item.get("pinyin")
    override = str(pinyin).strip() if pinyin else None
    return WordItem(
        word=word,
        source=source,
        detail=str(item.get("detail", "")).strip(),
        pinyin=override,
    )


def _poem(raw: object, where: str) -> Poem:
    item = _mapping(raw, where)
    _keys(
        item,
        allowed={"title", "dynasty", "author", "lines", "glosses", "teacher_note", "words"},
        required={"title", "dynasty", "author", "lines"},
        where=where,
    )
    lines = [str(line).strip() for line in _list(item["lines"], "lines")]
    if len(lines) < 2 or len(lines) % 2 != 0:
        raise DataError(f"{where}《{item['title']}》诗句应为成对的偶数句")
    for line in lines:
        if re.fullmatch(r"[\u4e00-\u9fff]+", line) is None or len(line) not in {5, 7}:
            raise DataError(f"{where}《{item['title']}》诗句须为五言或七言且不含标点：{line}")
    glosses = []
    for gloss in item.get("glosses", []):
        row = _mapping(gloss, "gloss")
        _keys(row, allowed={"term", "meaning"}, required={"term", "meaning"}, where="gloss")
        glosses.append(Gloss(term=str(row["term"]).strip(), meaning=str(row["meaning"]).strip()))
    words = [_word(row, where, default_source="poem") for row in item.get("words", [])]
    return Poem(
        title=str(item["title"]).strip(),
        dynasty=str(item["dynasty"]).strip(),
        author=str(item["author"]).strip(),
        lines=lines,
        glosses=glosses,
        teacher_note=str(item.get("teacher_note", "")).strip(),
        words=words,
    )


def _cloze(raw: object, where: str) -> ClozeItem:
    item = _mapping(raw, where)
    _keys(
        item,
        allowed={"id", "bank", "text", "answer", "origin", "explanation"},
        required={"id", "bank", "text", "answer", "origin"},
        where=where,
    )
    bank = [str(word).strip() for word in _list(item["bank"], "bank")]
    answer = str(item["answer"]).strip()
    text = str(item["text"]).strip()
    if "____" not in text:
        raise DataError(f"{where} 选词填空 {item['id']} 缺少 ____")
    if answer not in bank:
        raise DataError(f"{where} 选词填空 {item['id']} 的答案不在词库中")
    origin = _origin(item["origin"], where)
    return ClozeItem(
        id=str(item["id"]).strip(),
        bank=bank,
        text=text,
        answer=answer,
        origin=origin,
        explanation=str(item.get("explanation", "")).strip(),
    )


def _choice(raw: object, where: str) -> ChoiceItem:
    item = _mapping(raw, where)
    _keys(
        item,
        allowed={"id", "kind", "stem", "options", "answer", "origin", "explanation"},
        required={"id", "kind", "stem", "answer", "origin"},
        where=where,
    )
    kind = str(item["kind"])
    stem = str(item["stem"]).strip()
    answer = str(item["answer"]).strip()
    options = [str(option).strip() for option in item.get("options", [])]
    if kind == "judge":
        if answer not in {"对", "错"}:
            raise DataError(f"{where} 判断题 {item['id']} 的答案只能是对或错")
        if options:
            raise DataError(f"{where} 判断题 {item['id']} 不应填写 options")
    elif kind == "single":
        if not 2 <= len(options) <= 6:
            raise DataError(f"{where} 选择题 {item['id']} 选项数量应为 2–6")
        letters = [chr(ord("A") + index) for index in range(len(options))]
        if answer not in letters:
            raise DataError(f"{where} 选择题 {item['id']} 的答案必须是 {'/'.join(letters)}")
    else:
        raise DataError(f"{where} 未知选择题型 {kind}")
    return ChoiceItem(
        id=str(item["id"]).strip(),
        kind=kind,
        stem=stem,
        options=options,
        answer=answer,
        origin=_origin(item["origin"], where),
        explanation=str(item.get("explanation", "")).strip(),
    )


def _reading(raw: object, where: str) -> ReadingPassage:
    item = _mapping(raw, where)
    _keys(
        item,
        allowed={"id", "title", "origin", "credit", "paragraphs", "questions"},
        required={"id", "title", "origin", "credit", "paragraphs", "questions"},
        where=where,
    )
    paragraphs = [str(part).strip() for part in _list(item["paragraphs"], "paragraphs")]
    if not paragraphs:
        raise DataError(f"{where} 阅读 {item['id']} 没有正文")
    questions = []
    for row in _list(item["questions"], "questions"):
        question = _mapping(row, "reading question")
        _keys(
            question,
            allowed={"id", "stem", "answer", "explanation"},
            required={"id", "stem", "answer"},
            where=where,
        )
        questions.append(
            ReadingQuestion(
                id=str(question["id"]).strip(),
                stem=str(question["stem"]).strip(),
                answer=str(question["answer"]).strip(),
                explanation=str(question.get("explanation", "")).strip(),
            )
        )
    if not questions:
        raise DataError(f"{where} 阅读 {item['id']} 没有问题")
    return ReadingPassage(
        id=str(item["id"]).strip(),
        title=str(item["title"]).strip(),
        origin=_origin(item["origin"], where),
        credit=str(item["credit"]).strip(),
        paragraphs=paragraphs,
        questions=questions,
    )


def _writing(raw: object, where: str) -> WritingTask:
    item = _mapping(raw, where)
    _keys(
        item,
        allowed={"id", "title", "prompt", "requirements", "origin", "word_count"},
        required={"id", "title", "prompt", "requirements", "origin", "word_count"},
        where=where,
    )
    requirements = [str(line).strip() for line in _list(item["requirements"], "requirements")]
    if not requirements:
        raise DataError(f"{where} 习作缺少要求")
    return WritingTask(
        id=str(item["id"]).strip(),
        title=str(item["title"]).strip(),
        prompt=str(item["prompt"]).strip(),
        requirements=requirements,
        origin=_origin(item["origin"], where),
        word_count=_int(item["word_count"], "word_count"),
    )


def _origin(value: object, where: str) -> str:
    origin = str(value).strip()
    if origin not in ORIGINS:
        raise DataError(f"{where} origin 无效：{origin}")
    return origin


def _keys(data: dict, allowed: set[str], required: set[str], where: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise DataError(f"{where} 出现未定义字段：{'、'.join(unknown)}")
    missing = [key for key in required if key not in data]
    if missing:
        raise DataError(f"{where} 缺少字段：{'、'.join(missing)}")


def _mapping(value: object, where: str) -> dict:
    if not isinstance(value, dict):
        raise DataError(f"{where} 必须是映射")
    return value


def _list(value: object, where: str) -> list:
    if not isinstance(value, list):
        raise DataError(f"{where} 必须是列表")
    return value


def _int(value: object, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DataError(f"{where} 必须是整数")
    return value
