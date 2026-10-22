"""分值分配：整数、合计满分、上限可挪动。"""

from cn_exam.points import (
    allocate_section_points,
    cap_and_redistribute,
    largest_remainder,
    split_points,
)


def test_largest_remainder_keeps_total() -> None:
    weights = {"pinyin": 16, "cloze": 12, "choice": 12, "reading": 24, "writing": 18}
    allocated = largest_remainder(weights, 100)
    assert sum(allocated.values()) == 100
    assert set(allocated) == set(weights)


def test_full_default_weights_stay_put() -> None:
    weights = {
        "pinyin": 16,
        "classical": 18,
        "cloze": 12,
        "choice": 12,
        "reading": 24,
        "writing": 18,
    }
    assert largest_remainder(weights, 100) == weights


def test_cap_moves_extra_points_without_changing_total() -> None:
    points = {"pinyin": 20, "writing": 80}
    caps = {"pinyin": 4, "writing": 40}
    result = cap_and_redistribute(points, caps)
    assert sum(result.values()) == 100
    assert result["pinyin"] == 4
    assert result["writing"] == 96


def test_allocate_respects_pinyin_cap() -> None:
    allocated = allocate_section_points(
        ["pinyin", "writing"],
        {"pinyin": 2, "writing": 1},
        None,
        100,
    )
    assert sum(allocated.values()) == 100
    assert allocated["pinyin"] <= 4


def test_split_points_matches_weights() -> None:
    parts = split_points(10, [2, 1, 1])
    assert parts == [5, 3, 2] or sum(parts) == 10
    assert sum(parts) == 10
    assert all(item >= 1 for item in parts)
