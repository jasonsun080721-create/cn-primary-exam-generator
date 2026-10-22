"""把词语转成小学试卷常用的带声调拼音。"""

from __future__ import annotations

from pypinyin import Style, pinyin


def words_to_pinyin(word: str, override: str | None = None) -> str:
    """返回以空格分隔的拼音。

    override 用于多音字或通假字，例如诗中“阁笔”的“阁”读 gē。
    不在这里猜测教材读音；数据文件未填写时才用 pypinyin。
    """
    if override:
        text = " ".join(override.strip().split())
        if not text:
            raise ValueError(f"词语 {word} 的拼音覆盖为空")
        return text
    parts = pinyin(word, style=Style.TONE, heteronym=False, errors="default")
    return " ".join(item[0] for item in parts)
