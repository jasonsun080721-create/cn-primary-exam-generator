"""题库读取与校验。"""

from pathlib import Path

import pytest
import yaml

from cn_exam.errors import DataError
from cn_exam.loader import list_edition_files, load_edition

POEMS = {
    "暮江吟": ["一道残阳铺水中", "半江瑟瑟半江红", "可怜九月初三夜", "露似真珠月似弓"],
    "题西林壁": ["横看成岭侧成峰", "远近高低各不同", "不识庐山真面目", "只缘身在此山中"],
    "雪梅": ["梅雪争春未肯降", "骚人阁笔费评章", "梅须逊雪三分白", "雪却输梅一段香"],
}


def test_load_rj2026_poems_and_units() -> None:
    book = load_edition("rj2026", 4, 1)
    assert book.name == "人教版（统编版）"
    assert book.series_label == "2026秋新版"
    assert [unit.number for unit in book.units] == [1, 2, 3, 4, 5, 6, 7, 8]
    poems = {poem.title: poem for poem in book.unit(3).poems}
    assert set(poems) == set(POEMS)
    for title, lines in POEMS.items():
        assert poems[title].lines == lines
        assert poems[title].author in {"白居易", "苏轼", "卢钺"}
    assert book.unit(3).poems[2].author == "卢钺"
    words = [item.word for item in book.unit(1).textbook_words]
    assert "奇观" in words
    assert "风平浪静" in words
    assert "繁星" in words
    assert book.exam_ranges["midterm"].units == [1, 2, 3, 4]
    assert book.exam_ranges["final"].units == [1, 2, 3, 4, 5, 6, 7, 8]


def test_lessons_match_requested_starter_titles() -> None:
    book = load_edition("rj2026", 4, 1)
    expected = {
        1: ["观潮", "繁星", "现代诗二首"],
        2: ["一个豆荚里的五粒豆", "夜间飞行的秘密", "方帽子店", "田忌赛马"],
        3: ["古诗三首", "爬山虎的脚", "蟋蟀的住宅"],
        4: ["盘古开天地", "精卫填海", "普罗米修斯", "女娲补天"],
    }
    for number, titles in expected.items():
        assert [lesson.title for lesson in book.unit(number).lessons] == titles
    pieces = book.unit(3).lessons[0].pieces
    assert pieces == ["暮江吟", "题西林壁", "雪梅"]
    assert book.unit(1).lessons[2].pieces == ["秋晚的江上", "花牛歌"]
    assert book.unit(8).lessons[0].title == "我将无我，不负人民"
    assert [poem.title for poem in book.unit(8).poems] == ["凉州词", "出塞", "夏日绝句"]
    assert book.unit(8).poems[2].lines[-2:] == ["至今思项羽", "不肯过江东"]


def test_list_skips_template(tmp_path: Path) -> None:
    files = list_edition_files()
    names = [path.name for path in files]
    assert "grade4_term1.yaml" in names
    assert all(not path.parent.name.startswith("_") for path in files)
    assert not list(tmp_path.glob("_template.yaml"))


def test_reject_poem_punctuation(tmp_path: Path) -> None:
    payload = _minimal_payload()
    payload["units"][0]["poems"] = [
        {
            "title": "坏诗",
            "dynasty": "唐",
            "author": "某人",
            "lines": ["一行有标点。", "二三四五六七"],
        }
    ]
    _write(tmp_path, payload)
    with pytest.raises(DataError):
        load_edition("fixture", 4, 1, data_dir=tmp_path)


def test_reject_cloze_answer_outside_bank(tmp_path: Path) -> None:
    payload = _minimal_payload()
    payload["units"][0]["cloze_items"][0]["answer"] = "不在词库"
    _write(tmp_path, payload)
    with pytest.raises(DataError):
        load_edition("fixture", 4, 1, data_dir=tmp_path)


def test_load_json_edition(tmp_path: Path) -> None:
    payload = _minimal_payload()
    folder = tmp_path / "fixture"
    folder.mkdir()
    path = folder / "grade4_term1.json"
    path.write_text(__import__("json").dumps(payload, ensure_ascii=False), encoding="utf-8")
    book = load_edition("fixture", 4, 1, data_dir=tmp_path)
    assert book.id == "fixture"
    assert book.source_path.suffix == ".json"


def _write(folder: Path, payload: dict) -> None:
    target = folder / payload["edition"]["id"]
    target.mkdir(parents=True, exist_ok=True)
    path = target / "grade4_term1.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _minimal_payload() -> dict:
    return {
        "schema_version": 1,
        "edition": {
            "id": "fixture",
            "name": "测试版",
            "series_label": "测试",
            "grade": 4,
            "term": 1,
            "book_name": "四年级上册",
        },
        "paper_note": "测试",
        "unit_duration_minutes": 60,
        "exam_ranges": {
            "midterm": {"label": "期中", "units": [1], "duration_minutes": 90},
            "final": {"label": "期末", "units": [1], "duration_minutes": 90},
        },
        "units": [
            {
                "number": 1,
                "title": "第1单元",
                "lessons": [{"title": "示例课文", "author_status": "todo"}],
                "words": [],
                "textbook_words": [],
                "poems": [],
                "cloze_items": [
                    {
                        "id": "c1",
                        "bank": ["安静", "热闹"],
                        "text": "夜里很____。",
                        "answer": "安静",
                        "origin": "original_practice",
                    }
                ],
                "choice_items": [],
                "readings": [],
                "writing": {
                    "id": "w1",
                    "title": "写一件事",
                    "prompt": "写一件事。",
                    "requirements": ["写清楚。"],
                    "origin": "original_practice",
                    "word_count": 200,
                },
            }
        ],
    }
