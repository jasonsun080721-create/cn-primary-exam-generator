"""把满分拆成整数题型分、小题分。"""

from __future__ import annotations

import math

from cn_exam.errors import ExamError

# 各题型默认权重。范围内没有题目的题型不参与分配。
DEFAULT_WEIGHTS: dict[str, int] = {
    "pinyin": 16,
    "classical": 18,
    "cloze": 12,
    "choice": 12,
    "reading": 24,
    "writing": 18,
}

# 单题得分上限。词语题保持每词 2 分；其余上限用于避免某一题型独占整卷。
# 若所有题型都触顶仍不够满分，剩余分数交给习作或最后一种题型。
PER_ITEM_CAP: dict[str, int] = {
    "pinyin": 2,
    "classical": 10,
    "cloze": 4,
    "choice": 3,
    "reading": 8,
    "writing": 40,
}

SECTION_ORDER: tuple[str, ...] = (
    "pinyin",
    "classical",
    "cloze",
    "choice",
    "reading",
    "writing",
)

DEFAULT_TOTAL = 100


def largest_remainder(weights: dict[str, int], total: int) -> dict[str, int]:
    """按权重把 total 分成整数，键的插入顺序决定同分时谁先得余数。"""
    if total < 0:
        raise ExamError("满分不能为负数")
    if not weights:
        raise ExamError("没有可分配的题型")
    if any(value < 0 for value in weights.values()):
        raise ExamError("题型权重不能为负数")
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        raise ExamError("题型权重之和必须大于 0")

    raw = {key: total * value / weight_sum for key, value in weights.items()}
    floors = {key: math.floor(raw[key]) for key in weights}
    leftover = total - sum(floors.values())
    order = {key: index for index, key in enumerate(weights)}
    ranked = sorted(
        weights,
        key=lambda key: (raw[key] - floors[key], weights[key], -order[key]),
        reverse=True,
    )
    for key in ranked[:leftover]:
        floors[key] += 1
    if sum(floors.values()) != total:
        raise ExamError("分值分配内部错误")
    return floors


def cap_and_redistribute(points: dict[str, int], caps: dict[str, int]) -> dict[str, int]:
    """把超过上限的分数挪到仍有空间的题型，总和保持不变。"""
    if set(points) != set(caps):
        raise ExamError("分值上限与题型不一致")
    result = {key: min(points[key], caps[key]) for key in points}
    excess = sum(points.values()) - sum(result.values())
    while excess > 0:
        candidates = [key for key in points if result[key] < caps[key]]
        if not candidates:
            sink = "writing" if "writing" in result else next(reversed(result))
            result[sink] += excess
            break
        candidates.sort(
            key=lambda key: (caps[key] - result[key], points[key]),
            reverse=True,
        )
        result[candidates[0]] += 1
        excess -= 1
    if sum(result.values()) != sum(points.values()):
        raise ExamError("上限调整后总分发生变化")
    return result


def allocate_section_points(
    active: list[str],
    counts: dict[str, int],
    weights: dict[str, int] | None,
    total: int,
) -> dict[str, int]:
    """给实际有题的题型分配整数分，合计为 total。"""
    if total <= 0:
        raise ExamError("满分必须大于 0")
    if not active:
        raise ExamError("没有可出的题目，无法组卷")
    requested = dict(DEFAULT_WEIGHTS)
    if weights:
        unknown = sorted(set(weights) - set(DEFAULT_WEIGHTS))
        if unknown:
            names = "、".join(unknown)
            allowed = "、".join(SECTION_ORDER)
            raise ExamError(f"未知题型：{names}。可用题型：{allowed}")
        for key, value in weights.items():
            if value <= 0:
                raise ExamError(f"题型 {key} 的权重必须大于 0")
            requested[key] = value

    ordered = {key: requested[key] for key in SECTION_ORDER if key in active}
    ideal = largest_remainder(ordered, total)
    caps = {}
    for key in ordered:
        count = counts.get(key, 0)
        if count <= 0:
            raise ExamError(f"题型 {key} 没有题目却参与了分值分配")
        caps[key] = PER_ITEM_CAP[key] * count
    return cap_and_redistribute(ideal, caps)


def split_points(total: int, weights: list[int]) -> list[int]:
    """把一道大题的分数分给各小题。"""
    if total < len(weights):
        raise ExamError("小题数量超过该大题分数，无法保证每题至少 1 分")
    named = {str(index): weight for index, weight in enumerate(weights)}
    allocated = largest_remainder(named, total)
    return [allocated[str(index)] for index in range(len(weights))]
