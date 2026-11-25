"""주말 기준선 방식의 출퇴근 수요 지표 (docs/주제-및-분석방향.md 2-1).

README 분석 흐름 ②의 교차 확인용이다: 노선 반복으로 찾은 출퇴근 비중(routes.py)과 비교한다.

    출퇴근 초과 이용_h = 평일 하루 평균_h − 주말·공휴일 하루 평균_h
    통근 비중 = Σ_{h∈출퇴근 시간대} max(초과 이용_h, 0) / Σ_h 평일 하루 평균_h

평일 여가 이용은 보통 주말보다 적으므로 통근 비중은 실제 통근량보다 작게 나오는 하한(보수적 추정)이다.
입력은 대여 한 건이 한 줄인 표(대여이력)나 건수 컬럼이 있는 집계표(시간대별 이용정보) 모두 된다.
날짜·시간대 컬럼은 calendar_kr.add_time_columns()로 만들 수 있다.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from . import config
from .calendar_kr import (
    DAY_KINDS,
    OFFDAY,
    WEEKDAY,
    count_days,
    day_kind,
    period_end,
    period_start,
)

HOURS = tuple(range(24))


def _as_list(by: str | Iterable[str] | None) -> list[str]:
    if by is None:
        return []
    return [by] if isinstance(by, str) else list(by)


def _counts(df: pd.DataFrame, count_col: str | None):
    """건수 컬럼(결측은 0). count_col이 없으면 행마다 1건."""
    if count_col is None:
        return pd.Series(1, index=df.index).to_numpy()
    return df[count_col].astype("float64").fillna(0).to_numpy()


def hourly_daily_mean(
    df: pd.DataFrame,
    date_col: str = "날짜",
    hour_col: str = "시간대",
    count_col: str | None = None,
    by: str | Iterable[str] | None = None,
    start: str | pd.Timestamp | None = None,
    end: str | pd.Timestamp | None = None,
    labor_day_as_holiday: bool = False,
) -> pd.DataFrame:
    """시간대별 '하루 평균' 이용건수를 평일과 주말·공휴일로 나눠 구한다.

    하루 평균 = 기간 안 합계 ÷ 기간 안 그 일구분의 날 수. 이용이 0건인 날도 날 수에 들어간다
    (그래서 groupby().mean()과 다르다). 0건인 시간대는 0으로 채운다.
    start/end는 "2024-01"처럼 달로 주면 그 달 첫날·마지막 날로 읽는다.
    count_col=None이면 행 하나를 1건으로 센다(대여이력). start/end를 생략하면 데이터의 첫날~마지막 날.

    반환: [by..., 일구분, 시간대, 합계, 일수, 하루평균]
    """
    keys = _as_list(by)
    dates = pd.to_datetime(df[date_col]).dt.normalize()
    start = period_start(start) if start is not None else dates.min()
    end = period_end(end) if end is not None else dates.max()
    inside = ((dates >= start) & (dates <= end)).to_numpy()

    tmp = pd.DataFrame(
        {
            **{k: df[k].to_numpy()[inside] for k in keys},
            "일구분": day_kind(dates[inside], labor_day_as_holiday).to_numpy(),
            "시간대": df[hour_col].astype("float64").to_numpy()[inside].astype("int64"),
            "건수": _counts(df, count_col)[inside],
        }
    )
    total = tmp.groupby([*keys, "일구분", "시간대"], observed=True)["건수"].sum()

    # 빠진 (그룹, 일구분, 시간대) 조합을 0으로 채운다
    groups = (
        tmp[keys].drop_duplicates().itertuples(index=False, name=None) if keys else [()]
    )
    full = pd.MultiIndex.from_tuples(
        [(*g, kind, h) for g in groups for kind in DAY_KINDS for h in HOURS],
        names=[*keys, "일구분", "시간대"],
    )
    total = total.reindex(full, fill_value=0)

    ndays = count_days(start, end, labor_day_as_holiday)
    out = total.rename("합계").reset_index()
    out["일구분"] = pd.Categorical(out["일구분"], categories=DAY_KINDS, ordered=True)
    out["일수"] = out["일구분"].map(ndays.to_dict()).astype("int64")
    out["하루평균"] = out["합계"] / out["일수"].where(out["일수"] > 0)
    return out


def commute_share(
    hourly: pd.DataFrame,
    by: str | Iterable[str] | None = None,
    commute_hours: Iterable[int] | None = None,
) -> pd.DataFrame:
    """hourly_daily_mean() 결과로 통근 비중을 구한다 (docs 2-1 식).

    반환: [by...] + 평일하루평균(전 시간대 합), 출퇴근초과이용(하루 평균), 통근비중
    """
    keys = _as_list(by)
    hours = set(config.COMMUTE_HOURS if commute_hours is None else commute_hours)
    wide = hourly.pivot_table(
        index=[*keys, "시간대"],
        columns="일구분",
        values="하루평균",
        observed=True,
        aggfunc="sum",
    ).reindex(columns=list(DAY_KINDS), fill_value=0)
    excess = (wide[WEEKDAY] - wide[OFFDAY]).clip(lower=0)
    in_commute = wide.index.get_level_values("시간대").isin(hours)

    if keys:
        weekday_total = wide[WEEKDAY].groupby(level=keys).sum()
        commute_excess = excess[in_commute].groupby(level=keys).sum()
    else:
        weekday_total = pd.Series([wide[WEEKDAY].sum()])
        commute_excess = pd.Series([excess[in_commute].sum()])
    out = pd.DataFrame(
        {"평일하루평균": weekday_total, "출퇴근초과이용": commute_excess}
    )
    out["출퇴근초과이용"] = out["출퇴근초과이용"].fillna(0)
    out["통근비중"] = out["출퇴근초과이용"] / out["평일하루평균"]
    return out.reset_index() if keys else out.reset_index(drop=True)


def station_commute_index(
    df: pd.DataFrame,
    station_col: str = "대여소번호",
    date_col: str = "날짜",
    hour_col: str = "시간대",
    count_col: str | None = None,
    commute_hours: Iterable[int] | None = None,
    min_count: int | None = None,
    labor_day_as_holiday: bool = False,
) -> pd.DataFrame:
    """대여소 통근 지수 = 평일 중 출퇴근 시간대 비중 − 주말·공휴일 중 같은 시간대 비중.

    0보다 크면 평일 출퇴근 시간에 몰리는 대여소, 0 근처나 음수면 주말형·여가형 패턴으로 볼 수 있다.
    비중은 각 대여소 안에서 일구분별 합계로 나누므로 날 수 보정이 따로 필요 없다.
    min_count: 평일 건수나 주말·공휴일 건수가 이보다 적으면 지수를 비워 둔다(비중이 들쭉날쭉해서).
      기준은 팀이 데이터를 보고 정한다(docs "이용이 적은 대여소 제외 기준").

    반환: 대여소마다 평일건수, 휴일건수, 평일출퇴근비중, 휴일출퇴근비중, 통근지수
    """
    hours = set(config.COMMUTE_HOURS if commute_hours is None else commute_hours)
    tmp = pd.DataFrame(
        {
            station_col: df[station_col].to_numpy(),
            "일구분": day_kind(df[date_col], labor_day_as_holiday).to_numpy(),
            "출퇴근": df[hour_col].astype("float64").isin(hours).to_numpy(),
            "건수": _counts(df, count_col),
        }
    )
    total = (
        tmp.pivot_table(
            index=station_col,
            columns="일구분",
            values="건수",
            aggfunc="sum",
            observed=True,
        )
        .reindex(columns=list(DAY_KINDS), fill_value=0)
        .fillna(0)
    )
    commute = (
        tmp[tmp["출퇴근"]]
        .pivot_table(
            index=station_col,
            columns="일구분",
            values="건수",
            aggfunc="sum",
            observed=True,
        )
        .reindex(index=total.index, columns=list(DAY_KINDS), fill_value=0)
        .fillna(0)
    )

    out = pd.DataFrame(
        {
            "평일건수": total[WEEKDAY],
            "휴일건수": total[OFFDAY],
            "평일출퇴근비중": commute[WEEKDAY]
            / total[WEEKDAY].where(total[WEEKDAY] > 0),
            "휴일출퇴근비중": commute[OFFDAY] / total[OFFDAY].where(total[OFFDAY] > 0),
        }
    )
    out["통근지수"] = out["평일출퇴근비중"] - out["휴일출퇴근비중"]
    if min_count is not None:
        few = (out["평일건수"] < min_count) | (out["휴일건수"] < min_count)
        out.loc[few, "통근지수"] = float("nan")
    out.columns.name = None
    return out.reset_index()
