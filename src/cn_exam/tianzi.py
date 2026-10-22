"""绘制空的田字格，供学生卷粘贴。答案不画进格子。"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

# 约 12 毫米见方、打印时接近 300 dpi。
CELL_PX = 140
INK = (31, 78, 121)
GUIDE = (170, 180, 190)


def render_tianzi_png(count: int, cell: int = CELL_PX) -> bytes:
    """生成一行 count 个田字格的 PNG。"""
    if count < 1:
        raise ValueError("田字格数量至少为 1")
    if count > 12:
        raise ValueError("单行田字格过多")
    pad = 4
    width = cell * count + pad * 2
    height = cell + pad * 2
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    left = pad
    top = pad
    right = pad + cell * count - 1
    bottom = pad + cell - 1
    draw.rectangle([left, top, right, bottom], outline=INK, width=4)
    for index in range(1, count):
        x_pos = left + index * cell
        draw.line([(x_pos, top), (x_pos, bottom)], fill=INK, width=4)
    for index in range(count):
        x0 = left + index * cell
        x1 = x0 + cell
        mid_x = (x0 + x1) // 2
        mid_y = (top + bottom) // 2
        _dashed(draw, mid_x, top + 10, mid_x, bottom - 10, vertical=True)
        _dashed(draw, x0 + 10, mid_y, x1 - 10, mid_y, vertical=False)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _dashed(
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    vertical: bool,
) -> None:
    """画田字格中线。横竖分开写，避免斜线。"""
    dash = 8
    gap = 6
    if vertical:
        y_pos = y0
        while y_pos < y1:
            y_end = min(y_pos + dash, y1)
            draw.line([(x0, y_pos), (x0, y_end)], fill=GUIDE, width=2)
            y_pos = y_end + gap
        return
    x_pos = x0
    while x_pos < x1:
        x_end = min(x_pos + dash, x1)
        draw.line([(x_pos, y0), (x_end, y0)], fill=GUIDE, width=2)
        x_pos = x_end + gap
