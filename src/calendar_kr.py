"""한국 공휴일과 평일·휴일 구분, 시간대 구분.

docs 2-1 원칙대로 공휴일은 주말과 같은 "주말·공휴일"로 분류한다.

공휴일 목록 출처
- 우주항공청(2024년까지 한국천문연구원) 월력요항, 관보 게재
  https://astro.kasi.re.kr/life/post/calendarData
- 임시공휴일(2023-10-02, 2024-10-01, 2025-01-27)과 선거일은 관보 고시
- 노동절(5월 1일)·제헌절(7월 17일)은 2026년 4월 「관공서의 공휴일에 관한 규정」 개정으로 2026년부터 공휴일
토·일요일과 겹친 공휴일도 이름을 남기려고 넣었다(평일·휴일 구분 결과에는 영향 없음).
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable

import pandas as pd

from . import config

WEEKDAY = "평일"
OFFDAY = "주말·공휴일"
DAY_KINDS = (WEEKDAY, OFFDAY)
WEEKDAY_NAMES = ("월", "화", "수", "목", "금", "토", "일")

KR_HOLIDAYS: dict[str, str] = {
    # 2022
    "2022-01-01": "1월 1일",
    "2022-01-31": "설날 연휴",
    "2022-02-01": "설날",
    "2022-02-02": "설날 연휴",
    "2022-03-01": "3·1절",
    "2022-03-09": "제20대 대통령선거",
    "2022-05-05": "어린이날",
    "2022-05-08": "부처님오신날",
    "2022-06-01": "제8회 전국동시지방선거",
    "2022-06-06": "현충일",
    "2022-08-15": "광복절",
    "2022-09-09": "추석 연휴",
    "2022-09-10": "추석",
    "2022-09-11": "추석 연휴",
    "2022-09-12": "대체공휴일(추석)",
    "2022-10-03": "개천절",
    "2022-10-09": "한글날",
    "2022-10-10": "대체공휴일(한글날)",
    "2022-12-25": "기독탄신일",
    # 2023
    "2023-01-01": "1월 1일",
    "2023-01-21": "설날 연휴",
    "2023-01-22": "설날",
    "2023-01-23": "설날 연휴",
    "2023-01-24": "대체공휴일(설날)",
    "2023-03-01": "3·1절",
    "2023-05-05": "어린이날",
    "2023-05-27": "부처님오신날",
    "2023-05-29": "대체공휴일(부처님오신날)",
    "2023-06-06": "현충일",
    "2023-08-15": "광복절",
    "2023-09-28": "추석 연휴",
    "2023-09-29": "추석",
    "2023-09-30": "추석 연휴",
    "2023-10-02": "임시공휴일",
    "2023-10-03": "개천절",
    "2023-10-09": "한글날",
    "2023-12-25": "기독탄신일",
    # 2024
    "2024-01-01": "1월 1일",
    "2024-02-09": "설날 연휴",
    "2024-02-10": "설날",
    "2024-02-11": "설날 연휴",
    "2024-02-12": "대체공휴일(설날)",
    "2024-03-01": "3·1절",
    "2024-04-10": "제22대 국회의원선거",
    "2024-05-05": "어린이날",
    "2024-05-06": "대체공휴일(어린이날)",
    "2024-05-15": "부처님오신날",
    "2024-06-06": "현충일",
    "2024-08-15": "광복절",
    "2024-09-16": "추석 연휴",
    "2024-09-17": "추석",
    "2024-09-18": "추석 연휴",
    "2024-10-01": "임시공휴일(국군의 날)",
    "2024-10-03": "개천절",
    "2024-10-09": "한글날",
    "2024-12-25": "기독탄신일",
    # 2025
    "2025-01-01": "1월 1일",
    "2025-01-27": "임시공휴일",
    "2025-01-28": "설날 연휴",
    "2025-01-29": "설날",
    "2025-01-30": "설날 연휴",
    "2025-03-01": "3·1절",
    "2025-03-03": "대체공휴일(3·1절)",
    "2025-05-05": "어린이날·부처님오신날",
    "2025-05-06": "대체공휴일(부처님오신날)",
    "2025-06-03": "제21대 대통령선거",
    "2025-06-06": "현충일",
    "2025-08-15": "광복절",
    "2025-10-03": "개천절",
    "2025-10-05": "추석 연휴",
    "2025-10-06": "추석",
    "2025-10-07": "추석 연휴",
    "2025-10-08": "대체공휴일(추석)",
    "2025-10-09": "한글날",
    "2025-12-25": "기독탄신일",
    # 2026
    "2026-01-01": "1월 1일",
    "2026-02-16": "설날 연휴",
    "2026-02-17": "설날",
    "2026-02-18": "설날 연휴",
    "2026-03-01": "3·1절",
    "2026-03-02": "대체공휴일(3·1절)",
    "2026-05-01": "노동절",
    "2026-05-05": "어린이날",
    "2026-05-24": "부처님오신날",
    "2026-05-25": "대체공휴일(부처님오신날)",
    "2026-06-03": "제9회 전국동시지방선거",
    "2026-06-06": "현충일",
    "2026-07-17": "제헌절",
    "2026-08-15": "광복절",
    "2026-08-17": "대체공휴일(광복절)",
    "2026-09-24": "추석 연휴",
    "2026-09-25": "추석",
    "2026-09-26": "추석 연휴",
    "2026-10-03": "개천절",
    "2026-10-05": "대체공휴일(개천절)",
    "2026-10-09": "한글날",
    "2026-12-25": "기독탄신일",
}
HOLIDAY_YEARS = range(2022, 2027)

# 2025년까지 5월 1일은 '근로자의 날'로, 공휴일은 아니지만 많은 직장인이 쉬었다.
# 출퇴근 분석에서 이 날을 휴일로 볼지는 labor_day_as_holiday 인자로 고른다(기본: 평일).
LABOR_DAYS_BEFORE_2026: dict[str, str] = {
    f"{y}-05-01": "근로자의 날(공휴일 아님)" for y in range(2022, 2026)
}


def _as_dates(dates: Iterable) -> pd.Series:
    s = pd.Series(pd.to_datetime(pd.Series(dates)).to_numpy())
    return s.dt.normalize()


def _holiday_index(labor_day_as_holiday: bool) -> pd.DatetimeIndex:
    days = list(KR_HOLIDAYS)
    if labor_day_as_holiday:
        days += list(LABOR_DAYS_BEFORE_2026)
    return pd.DatetimeIndex(pd.to_datetime(days))


def _warn_uncovered(dates: pd.Series) -> None:
    years = set(dates.dt.year.dropna().astype(int).unique())
    outside = sorted(int(y) for y in years - set(HOLIDAY_YEARS))
    if outside:
        warnings.warn(
            f"공휴일 표에 없는 연도 {outside}가 있다. 그 해는 토·일요일만 휴일로 잡힌다.",
            stacklevel=3,
        )


def is_offday(dates: Iterable, labor_day_as_holiday: bool = False) -> pd.Series:
    """토·일요일 또는 공휴일이면 True. 입력과 같은 길이의 Series(0부터 번호), 날짜가 비면 결측."""
    d = _as_dates(dates)
    _warn_uncovered(d)
    weekend = d.dt.day_of_week >= 5
    holiday = d.isin(_holiday_index(labor_day_as_holiday))
    return (weekend | holiday).astype("boolean").mask(d.isna()).rename("휴일여부")


def day_kind(dates: Iterable, labor_day_as_holiday: bool = False) -> pd.Series:
    """'평일' / '주말·공휴일' 구분 (순서 있는 범주형)."""
    off = is_offday(dates, labor_day_as_holiday)
    values = off.map({False: WEEKDAY, True: OFFDAY})
    return pd.Series(
        pd.Categorical(values, categories=DAY_KINDS, ordered=True), name="일구분"
    )


def time_band(hours: Iterable) -> pd.Series:
    """시간대(0~23)를 '출근' / '퇴근' / '그 외'로 나눈다. 기준은 config의 임시값."""
    h = pd.Series(hours).astype("Int64")
    band = pd.Series("그 외", index=h.index)
    band[h.isin(config.COMMUTE_AM_HOURS).fillna(False)] = "출근"
    band[h.isin(config.COMMUTE_PM_HOURS).fillna(False)] = "퇴근"
    band[h.isna()] = pd.NA
    return pd.Series(
        pd.Categorical(band, categories=("출근", "퇴근", "그 외")), name="시간구분"
    )


def calendar_table(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    labor_day_as_holiday: bool = False,
) -> pd.DataFrame:
    """start~end(양 끝 포함) 하루 한 줄: 날짜, 요일, 공휴일명, 일구분."""
    days = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize())
    names = {**KR_HOLIDAYS, **(LABOR_DAYS_BEFORE_2026 if labor_day_as_holiday else {})}
    return pd.DataFrame(
        {
            "날짜": days,
            "요일": [WEEKDAY_NAMES[d] for d in days.day_of_week],
            "공휴일명": [names.get(d.strftime("%Y-%m-%d")) for d in days],
            "일구분": day_kind(days, labor_day_as_holiday).array,
        }
    )


def count_days(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    labor_day_as_holiday: bool = False,
) -> pd.Series:
    """기간 안의 평일 수와 주말·공휴일 수. 하루 평균을 낼 때 분모로 쓴다."""
    cal = calendar_table(start, end, labor_day_as_holiday)
    return cal["일구분"].value_counts().reindex(DAY_KINDS, fill_value=0).rename("일수")


def add_time_columns(
    df: pd.DataFrame,
    col: str = "대여일시",
    labor_day_as_holiday: bool = False,
    prefix: str = "",
) -> pd.DataFrame:
    """일시 컬럼에서 날짜·연도·월·요일·시간대·일구분·시간구분 컬럼을 만들어 붙인 복사본을 돌려준다.

    반납일시처럼 다른 컬럼에도 붙이려면 prefix="반납"을 주면 "반납날짜", "반납시간대"처럼 붙는다.
    """
    t = pd.to_datetime(df[col])
    out = df.copy()
    out[f"{prefix}날짜"] = t.dt.normalize()
    out[f"{prefix}연도"] = t.dt.year.astype("Int16")
    out[f"{prefix}월"] = t.dt.month.astype("Int8")
    out[f"{prefix}요일"] = pd.Categorical(
        t.dt.day_of_week.map(dict(enumerate(WEEKDAY_NAMES))),
        categories=WEEKDAY_NAMES,
        ordered=True,
    )
    out[f"{prefix}시간대"] = t.dt.hour.astype("Int8")
    out[f"{prefix}일구분"] = day_kind(t, labor_day_as_holiday).array
    out[f"{prefix}시간구분"] = time_band(t.dt.hour).array
    return out
