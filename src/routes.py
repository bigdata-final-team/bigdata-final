"""출퇴근 노선 판별 준비 (README 분석 흐름 ②).

노선 = 대여 대여소 → 반납 대여소. 대여이력을 시간대 × 노선으로 모아
"평일 며칠에 나타났는지"(평일출현일수)를 센다. 반복 기준은 팀이 아직 정하지 않았으므로
여기서는 판정에 필요한 표만 만들고, 기준값은 flag_repeated_routes()에 직접 넣는다.

    from src import loaders, routes
    loaders.rent_history_to_parquet(2024)
    stats = routes.build_route_stats([f"2024-{m:02d}" for m in range(1, 13)])
    loaders.save_parquet(stats, "route_stats_2024", where="interim")
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from . import config, loaders
from .calendar_kr import OFFDAY, WEEKDAY, count_days, day_kind

KEYS = ["시간대", "대여소번호", "반납대여소번호"]
STAT_COLUMNS = ["평일건수", "평일출현일수", "휴일건수", "휴일출현일수"]


def _route_counts(rent: pd.DataFrame, labor_day_as_holiday: bool) -> pd.DataFrame:
    """(시간대, 대여소번호, 반납대여소번호) 인덱스, 값은 STAT_COLUMNS. 대여소번호는 문자열."""
    df = rent.dropna(subset=["대여일시", "대여소번호", "반납대여소번호"])
    t = pd.to_datetime(df["대여일시"])
    tmp = pd.DataFrame(
        {
            "날짜": t.dt.normalize().to_numpy(),
            "일구분": day_kind(t, labor_day_as_holiday).to_numpy(),
            "시간대": t.dt.hour.astype("int8").to_numpy(),
            "대여소번호": df["대여소번호"].astype("string").to_numpy(),
            "반납대여소번호": df["반납대여소번호"].astype("string").to_numpy(),
        }
    )
    parts = []
    for kind, prefix in ((WEEKDAY, "평일"), (OFFDAY, "휴일")):
        part = tmp[tmp["일구분"] == kind]
        parts.append(
            part.groupby(KEYS, observed=True).agg(
                **{
                    f"{prefix}건수": ("날짜", "size"),
                    f"{prefix}출현일수": ("날짜", "nunique"),
                }
            )
        )
    return pd.concat(parts, axis=1).fillna(0).astype("int64")


def route_stats(rent: pd.DataFrame, labor_day_as_holiday: bool = False) -> pd.DataFrame:
    """대여 한 건이 한 줄인 표(대여일시, 대여소번호, 반납대여소번호)에서 노선 × 시간대 통계를 만든다.

    반환: 시간대, 대여소번호, 반납대여소번호, 평일건수, 평일출현일수, 휴일건수, 휴일출현일수, 왕복
    - 출현일수: 그 시간대에 그 노선이 한 번 이상 나온 날의 수
    - 시간대는 대여 시각 기준 1시간 단위(h = h:00~h:59)
    - 반납대여소번호가 빈 기록(반납 정보 없음)은 뺀다
    """
    return _finish(_route_counts(rent, labor_day_as_holiday).reset_index())


def build_route_stats(
    months: Iterable[str], labor_day_as_holiday: bool = False, verbose: bool = True
) -> pd.DataFrame:
    """rent_history_to_parquet()로 만든 월별 parquet를 한 달씩 읽어 노선 통계를 합친다.

    달마다 날짜가 겹치지 않으므로 출현일수도 그대로 더하면 된다. 메모리를 아끼려고 한 달씩 처리한다.
    결과의 attrs["평일일수"], attrs["휴일일수"]에 고른 달들의 날 수 합을 남긴다(출현비율 계산용).
    attrs는 parquet로 저장하면 사라지므로 필요하면 따로 적어 둔다.
    """
    months = sorted(months)
    total: pd.DataFrame | None = None
    days = pd.Series(0, index=[WEEKDAY, OFFDAY])
    for ym in months:
        rent = loaders.load_rent_history(
            months=[ym], columns=["대여일시", "대여소번호", "반납대여소번호"]
        )
        part = _route_counts(rent, labor_day_as_holiday)
        total = part if total is None else total.add(part, fill_value=0)
        days = days + count_days(ym, ym, labor_day_as_holiday)
        if verbose:
            print(f"  {ym}: 대여 {len(rent):,}건, 누적 노선×시간대 {len(total):,}개")
    if total is None:
        raise ValueError("months가 비어 있다")
    out = _finish(total.fillna(0).astype("int64").reset_index())
    out.attrs.update({"평일일수": int(days[WEEKDAY]), "휴일일수": int(days[OFFDAY])})
    return out


def _finish(df: pd.DataFrame) -> pd.DataFrame:
    df["왕복"] = (
        df["대여소번호"].astype("string") == df["반납대여소번호"].astype("string")
    ).astype(bool)
    for col in ("대여소번호", "반납대여소번호"):
        df[col] = df[col].astype("category")
    df["시간대"] = df["시간대"].astype("int8")
    return df.sort_values(KEYS, kind="stable").reset_index(drop=True)


def flag_repeated_routes(
    stats: pd.DataFrame,
    min_weekdays: int,
    hours: Iterable[int] | None = None,
    exclude_round_trip: bool = True,
) -> pd.Series:
    """평일에 min_weekdays일 이상 같은 시간대에 나타난 노선이면 True.

    min_weekdays: 반복 기준(팀이 정할 값). 분포를 보고 정하고, 기준을 바꿔 가며 결과 변화를 함께 보인다.
    hours: 이 시간대만 본다. 생략하면 config.COMMUTE_HOURS(임시값). 모든 시간대를 보려면 range(24).
    exclude_round_trip: 대여소 = 반납소(왕복)는 출퇴근 노선에서 뺀다.
    """
    hours = set(config.COMMUTE_HOURS if hours is None else hours)
    flag = (stats["평일출현일수"] >= min_weekdays) & stats["시간대"].isin(hours)
    if exclude_round_trip:
        flag &= ~stats["왕복"]
    return flag.rename("반복노선")


def mark_reverse_pairs(
    stats: pd.DataFrame,
    flag: pd.Series,
    am_hours: Iterable[int] | None = None,
    pm_hours: Iterable[int] | None = None,
) -> pd.Series:
    """아침 A→B 반복 노선 중 저녁에 B→A도 반복되는 것(그 반대도)에 True. 출퇴근 근거 보강용.

    flag는 flag_repeated_routes() 결과. 시간대 기본값은 config의 출근·퇴근 임시값.
    """
    am = set(config.COMMUTE_AM_HOURS if am_hours is None else am_hours)
    pm = set(config.COMMUTE_PM_HOURS if pm_hours is None else pm_hours)
    hit = stats.loc[flag, ["시간대", "대여소번호", "반납대여소번호"]].astype(
        {"대여소번호": "string", "반납대여소번호": "string"}
    )
    am_pairs = set(zip(hit.loc[hit["시간대"].isin(am), "대여소번호"],
                       hit.loc[hit["시간대"].isin(am), "반납대여소번호"], strict=True))  # fmt: skip
    pm_pairs = set(zip(hit.loc[hit["시간대"].isin(pm), "대여소번호"],
                       hit.loc[hit["시간대"].isin(pm), "반납대여소번호"], strict=True))  # fmt: skip

    origin = stats["대여소번호"].astype("string")
    dest = stats["반납대여소번호"].astype("string")
    in_am = stats["시간대"].isin(am)
    in_pm = stats["시간대"].isin(pm)
    reverse_in_pm = pd.Series(
        [(d, o) in pm_pairs for o, d in zip(origin, dest, strict=True)],
        index=stats.index,
    )
    reverse_in_am = pd.Series(
        [(d, o) in am_pairs for o, d in zip(origin, dest, strict=True)],
        index=stats.index,
    )
    paired = flag & ((in_am & reverse_in_pm) | (in_pm & reverse_in_am))
    return paired.rename("역방향반복")
