"""그래프 공통 설정: 한글 폰트, 출처 표기, 저장.

노트북 맨 위에서 한 번:
    from src import viz
    viz.setup_plot()

그래프마다:
    fig, ax = plt.subplots()
    ...
    viz.add_source(fig, "rent_history", "stations", note=config.provisional_note())
    viz.save_fig(fig, "02_통근지수_지도")
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import pandas as pd
from matplotlib import font_manager
from matplotlib.axes import Axes
from matplotlib.figure import Figure, SubFigure
from matplotlib.text import Annotation
from matplotlib.ticker import FuncFormatter
from matplotlib.transforms import Bbox

from . import config

# 앞에 있는 폰트부터 찾는다: Windows → macOS → 나눔(직접 설치) → Linux·Colab
KOREAN_FONTS = (
    "Malgun Gothic",
    "AppleGothic",
    "NanumGothic",
    "Noto Sans CJK KR",
    "Noto Sans KR",
)


def korean_font() -> str:
    """이 PC에 설치된 한글 폰트 이름. 없으면 설치 방법과 함께 오류를 낸다."""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in KOREAN_FONTS:
        if name in installed:
            return name
    raise RuntimeError(
        "한글 폰트를 찾지 못했다. 나눔고딕을 설치한 뒤 커널을 재시작하거나, "
        f"viz.KOREAN_FONTS에 설치된 폰트 이름을 추가할 것. 찾은 순서: {KOREAN_FONTS}"
    )


def setup_plot(style: str | None = "whitegrid", font_scale: float = 1.0) -> str:
    """한글 폰트·마이너스 기호·해상도를 설정하고 쓰인 폰트 이름을 돌려준다.

    seaborn의 set_theme()는 폰트를 기본값으로 되돌리므로, seaborn 스타일도 여기서 같이 정한다.
    style=None이면 seaborn을 건드리지 않는다.
    """
    font = korean_font()
    if style is not None:
        import seaborn as sns

        sns.set_theme(style=style, font=font, font_scale=font_scale)
    mpl.rcParams["font.family"] = font
    mpl.rcParams["axes.unicode_minus"] = (
        False  # 한글 폰트에서 음수 기호가 네모로 깨지는 것 방지
    )
    mpl.rcParams["figure.dpi"] = 110
    mpl.rcParams["savefig.dpi"] = 200
    mpl.rcParams["savefig.bbox"] = "tight"  # 그림 아래에 붙인 출처 글자까지 저장되게
    return font


def source_text(*sources: str, note: str | None = None) -> str:
    """config.SOURCES의 키나 직접 쓴 문구로 "출처: ..." 한 줄을 만든다. note는 다음 줄에 붙는다."""
    if not sources:
        raise ValueError("출처를 하나 이상 적어야 한다 (예: 'rent_history')")
    text = "출처: " + "; ".join(config.SOURCES.get(s, s) for s in sources)
    return f"{text}\n{note}" if note else text


def add_source(
    target: Figure | SubFigure | Axes,
    *sources: str,
    note: str | None = None,
    fontsize: float = 8,
) -> Annotation:
    """그림의 모든 축(눈금·축 이름·범례 포함) 아래 왼쪽에 출처를 적는다. note는 한계·임시값 안내.

    위치는 그릴 때마다 다시 계산되므로 축 이름이나 범례와 겹치지 않는다.
    """
    fig = target.figure if isinstance(target, Axes) else target

    def below_axes(renderer):
        boxes = [ax.get_tightbbox(renderer) for ax in fig.axes if ax.get_visible()]
        boxes = [b for b in boxes if b is not None]
        return Bbox.union(boxes) if boxes else fig.bbox

    ann = Annotation(
        source_text(*sources, note=note),
        xy=(0, 0),
        xycoords=below_axes,
        xytext=(0, -6),
        textcoords="offset points",
        ha="left",
        va="top",
        fontsize=fontsize,
        color="0.35",
    )
    fig.add_artist(ann)
    return ann


def save_fig(fig: Figure, name: str, folder: str | Path | None = None) -> Path:
    """figures/<name>.png로 저장한다(출처 글자 포함). 저장한 경로를 돌려준다."""
    out_dir = Path(folder) if folder is not None else config.FIGURES
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / (name if Path(name).suffix else f"{name}.png")
    fig.savefig(path, bbox_inches="tight")
    return path


def comma_axis(ax: Axes, axis: str = "y", decimals: int = 0) -> None:
    """축 눈금을 1,234 모양으로 쓴다."""
    fmt = FuncFormatter(lambda x, _pos: f"{x:,.{decimals}f}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def percent_axis(ax: Axes, axis: str = "y", decimals: int = 0) -> None:
    """0~1 비율 값을 12% 모양으로 쓴다."""
    fmt = FuncFormatter(lambda x, _pos: f"{x:.{decimals}%}")
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)


def table_with_source(
    df: pd.DataFrame, *sources: str, note: str | None = None, **format_kw
):
    """표 아래에 출처를 단 Styler. 노트북에서 표를 보여 줄 때 df 대신 이것을 마지막 줄에 둔다.

    format_kw는 Styler.format()에 넘긴다. 예: precision=1, thousands=","
    """
    caption = source_text(*sources, note=note).replace("\n", "<br>")
    styler = df.style.set_caption(caption).set_table_styles(
        [
            {
                "selector": "caption",
                "props": "caption-side: bottom; font-size: 0.8em; color: #666; text-align: left;",
            }
        ]
    )
    return styler.format(**format_kw) if format_kw else styler
