"""원본 데이터(data/raw/)를 읽어 컬럼 이름과 값 표기를 하나로 맞추는 함수.

원본은 받은 그대로 두고, 여기서 읽을 때만 정리한다. 2026-11-25에 받은 파일로 확인한 차이:
- 인코딩: 대부분 cp949, 일부 UTF-8(BOM). 신규가입자 22.07-22.12는 확장자만 .csv이고 실제로는 엑셀이다.
- 머리글: 신규가입자 24.7-12에는 머리글 줄이 없다. 같은 컬럼도 파일마다 이름이 다르다
  (대여일자/대여년월, 이동거리(M)/이용거리(M), 연령대코드/연령대, 가입 수/가입수/가입건수).
- 대여소번호: "00102"와 "102"가 섞여 있다 → 5자리 문자열("00102")로 통일
- 대여구분코드: "정기"→"정기권", "일일(회원)"→"일일권"처럼 시기마다 표기가 다르다 → 이용권_대분류로 묶음
- 연령대: "~10대"와 "10대"가 섞여 있다 → "~10대"
- 성별: "M"/"F" 외에 "m"/"f", 빈칸, "\\N" → 대문자, 빈칸과 "\\N"은 결측
- 지하철 승하차 2025년 파일 끝에 빈 줄이 있다 → 버림

대여이력(OA-15182)과 대여가능 수량(OA-22382)은 압축을 풀지 않고 zip 안의 csv를 청크로 읽어
월별 parquet(data/interim/)로 바꾼 뒤, 그 parquet를 읽어 분석한다.
"""

from __future__ import annotations

import codecs
import os
import re
import warnings
import zipfile
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path

import pandas as pd

from . import config

# ---- 값 표기 통일 기준 ---------------------------------------------------------
AGE_ORDER = ("~10대", "20대", "30대", "40대", "50대", "60대", "70대이상", "기타")
AGE_ALIASES = {"10대": "~10대"}

PASS_GROUP = {  # 원본 대여구분코드 → 이용권_대분류
    "정기": "정기권",
    "정기권": "정기권",
    "일일(회원)": "일일권",
    "일일권": "일일권",
    "일일권(3시간)": "일일권",
    "일일(비회원)": "일일권(비회원)",
    "일일권(비회원)": "일일권(비회원)",
    "일일권(비회원 3시간)": "일일권(비회원)",
    "단체": "단체권",
    "단체권": "단체권",
    "가족권": "가족권",
    "가족권(2시간)": "가족권",
    "가족권(3시간)": "가족권",
    "10분이용권": "기타",
}
PASS_ORDER = ("정기권", "일일권", "일일권(비회원)", "단체권", "가족권", "기타")

MISSING_TOKENS = ("", "\\N", "nan", "NaN", "None")

_SAMPLE_BYTES = 64 * 1024


# ---- 공통 도구 ---------------------------------------------------------------
def detect_encoding(sample: bytes) -> str:
    """파일 앞부분 바이트로 인코딩을 고른다: BOM이 있으면 utf-8-sig, UTF-8로 풀리면 utf-8, 아니면 cp949."""
    if sample.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError as err:
        # 샘플 끝에서 글자가 잘린 경우는 UTF-8로 본다
        if err.start < len(sample) - 3:
            return "cp949"
    return "utf-8"


def is_excel_file(path: str | Path) -> bool:
    """확장자와 상관없이 내용이 엑셀(xlsx, zip 형식)인지 확인한다."""
    with open(path, "rb") as fh:
        return fh.read(4) == b"PK\x03\x04"


def _excel_rows(path: Path, max_blank_run: int = 1000) -> list[tuple]:
    """엑셀 첫 시트의 값을 줄 단위로 읽는다. 빈 줄은 버리고, 빈 줄이 max_blank_run번 이어지면 멈춘다.

    2018~2022 신규가입자 엑셀은 실제 데이터가 1.8만 줄인데 빈 줄이 100만 줄 넘게 잡혀 있어서
    pd.read_excel()로 읽으면 1분 가까이 걸린다.
    """
    import openpyxl

    # 파일 객체로 넘긴다: 경로로 넘기면 openpyxl이 확장자(.csv)를 보고 거부한다
    with open(path, "rb") as fh:
        wb = openpyxl.load_workbook(fh, read_only=True, data_only=True)
        try:
            rows: list[tuple] = []
            blank = 0
            for row in wb.worksheets[0].iter_rows(values_only=True):
                if all(v is None or str(v).strip() == "" for v in row):
                    blank += 1
                    if blank >= max_blank_run:
                        break
                    continue
                blank = 0
                rows.append(tuple("" if v is None else str(v) for v in row))
            return rows
        finally:
            wb.close()


def read_table(path: str | Path, header: int | None = 0) -> pd.DataFrame:
    """csv든 xlsx든 내용을 보고 읽는다. 모든 값을 문자열로 읽고 빈칸은 ""로 둔다.

    엑셀은 빈 줄을 버린다. header=0이면 첫 줄을 컬럼명으로, None이면 컬럼명 없이 0, 1, 2...로 둔다.
    """
    path = Path(path)
    if is_excel_file(path):
        rows = _excel_rows(path)
        if header is None:
            return pd.DataFrame(rows, dtype=str)
        return pd.DataFrame(rows[header + 1 :], columns=list(rows[header]), dtype=str)
    with open(path, "rb") as fh:
        encoding = detect_encoding(fh.read(_SAMPLE_BYTES))
    return pd.read_csv(
        path, header=header, dtype=str, keep_default_na=False, encoding=encoding
    )


def normalize_station_id(ids: pd.Series) -> pd.Series:
    """대여소번호를 5자리 문자열로 맞춘다: 102 → "00102", "102.0" → "00102". 빈칸은 결측."""
    s = ids.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    s = s.mask(s.isin(MISSING_TOKENS))
    return s.str.zfill(5)


def normalize_sex(values: pd.Series) -> pd.Series:
    """성별을 "M"/"F"로 맞춘다. 빈칸, "\\N"은 결측."""
    s = values.astype("string").str.strip().str.upper()
    s = s.mask(s.isin([t.upper() for t in MISSING_TOKENS]))
    return s.astype("category")


def normalize_age(values: pd.Series) -> pd.Series:
    """연령대를 AGE_ORDER 순서의 범주형으로. 표에 없는 값(예: "AGE_009")은 지우지 않고 맨 뒤에 붙인다."""
    s = values.astype("string").str.strip().replace(AGE_ALIASES)
    s = s.mask(s.isin(MISSING_TOKENS))
    extra = sorted(set(s.dropna().unique()) - set(AGE_ORDER))
    if extra:
        warnings.warn(f"연령대 표에 없는 값: {extra} (그대로 둠)", stacklevel=2)
    return pd.Series(
        pd.Categorical(s, categories=[*AGE_ORDER, *extra], ordered=True),
        index=values.index,
    )


def _to_number(values: pd.Series, dtype: str = "float64") -> pd.Series:
    s = pd.to_numeric(values.astype("string").str.strip(), errors="coerce")
    if dtype.startswith(("Int", "int")):
        return s.round().astype(dtype)
    return s.astype(dtype)


def _standard_names(
    names: Iterable[object], mapping: dict[str, str], where: object
) -> list[str]:
    """원본 컬럼명을 표준 이름으로 바꾼다. 처음 보는 컬럼이 있으면 바로 알린다."""
    cols = [str(c).strip() for c in names]
    unknown = [c for c in cols if c not in mapping]
    if unknown:
        raise ValueError(
            f"{where}: 처음 보는 컬럼 {unknown}. loaders.py의 컬럼 표를 고쳐야 한다."
        )
    return [mapping[c] for c in cols]


def _rename_known(
    df: pd.DataFrame, mapping: dict[str, str], where: object
) -> pd.DataFrame:
    return df.set_axis(_standard_names(df.columns, mapping, where), axis=1)


def _bound(value: str | None, side: str) -> pd.Timestamp | None:
    """ "2024", "2024-06"은 그 기간의 처음(start)이나 끝(end)으로, "2024-06-15"는 그날로 바꾼다."""
    if value is None:
        return None
    if re.fullmatch(r"\d{4}(-\d{2})?", str(value)):
        period = pd.Period(str(value))
        return period.start_time if side == "start" else period.end_time
    ts = pd.Timestamp(value)
    return ts if side == "start" else ts + pd.Timedelta(days=1) - pd.Timedelta(1, "ns")


def _period_mask(dates: pd.Series, start: str | None, end: str | None) -> pd.Series:
    """start~end(양 끝 포함) 안이면 True. end="2024-06"이면 6월 30일까지 들어간다."""
    mask = pd.Series(True, index=dates.index)
    lo, hi = _bound(start, "start"), _bound(end, "end")
    if lo is not None:
        mask &= dates >= lo
    if hi is not None:
        mask &= dates <= hi
    return mask


# ---- 따릉이 이용정보(월별) OA-15248 ---------------------------------------------
USAGE_MONTHLY_COLUMNS = {
    "대여일자": "대여월",
    "대여년월": "대여월",
    "대여소번호": "대여소번호",
    "대여소명": "대여소명",
    "대여구분코드": "이용권",
    "성별": "성별",
    "연령대코드": "연령대",
    "이용건수": "이용건수",
    "운동량": "운동량",
    "탄소량": "탄소량",
    "이동거리(M)": "이동거리_m",
    "이용거리(M)": "이동거리_m",
    "이용시간(분)": "이용시간_분",
}


def load_usage_monthly(
    start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    """월별 이용정보 전체(대여소 × 이용권 × 성별 × 연령대 × 월). start/end는 "2024-01"처럼 준다.

    반환 컬럼: 대여월(그 달 1일), 대여소번호, 대여소명, 이용권(원본 표기), 이용권_대분류, 정기권여부,
    성별, 연령대, 이용건수, 운동량, 탄소량, 이동거리_m, 이용시간_분

    대여소번호에는 실제 대여소가 아닌 센터·정비 코드도 있다(예: 00003 중랑센터, 09997 강남센터,
    99999 영남단말기정비). 대여소 단위로 볼 때는 load_stations_union()의 대여소번호로 걸러낸다.
    한 해 전체를 읽는 데 1분쯤 걸리므로 노트북에서는 cached("usage_monthly", load_usage_monthly)를 쓴다.
    """
    frames = []
    seen: dict[pd.Timestamp, str] = {}
    for path in sorted((config.DATA_RAW / "usage_monthly").glob("*.csv")):
        df = _rename_known(read_table(path), USAGE_MONTHLY_COLUMNS, path.name)
        month = pd.to_datetime(
            df["대여월"].str.replace("-", "", regex=False).str[:6], format="%Y%m"
        )
        for m in month.unique():
            if m in seen:
                warnings.warn(
                    f"{m:%Y-%m}이 {seen[m]}와 {path.name}에 둘 다 있다", stacklevel=2
                )
            seen[m] = path.name
        frames.append(df.assign(대여월=month)[_period_mask(month, start, end)])
    if not frames:
        raise FileNotFoundError(config.DATA_RAW / "usage_monthly")
    df = pd.concat(frames, ignore_index=True)

    passes = df["이용권"].str.strip()
    group = passes.map(PASS_GROUP)
    unknown = sorted(passes[group.isna()].unique())
    if unknown:
        warnings.warn(f"이용권 표에 없는 값: {unknown} → '기타'로 묶음", stacklevel=2)
    group = group.fillna("기타")

    return pd.DataFrame(
        {
            "대여월": df["대여월"],
            "대여소번호": normalize_station_id(df["대여소번호"]).astype("category"),
            "대여소명": df["대여소명"].str.strip().astype("category"),
            "이용권": passes.astype("category"),
            "이용권_대분류": pd.Categorical(group, categories=PASS_ORDER),
            "정기권여부": group.eq("정기권"),
            "성별": normalize_sex(df["성별"]),
            "연령대": normalize_age(df["연령대"]),
            "이용건수": _to_number(df["이용건수"], "Int64"),
            "운동량": _to_number(df["운동량"]),
            "탄소량": _to_number(df["탄소량"]),
            "이동거리_m": _to_number(df["이동거리_m"]),
            "이용시간_분": _to_number(df["이용시간_분"]),
        }
    )


# ---- 따릉이 신규가입자(일별) OA-15243 --------------------------------------------
NEW_MEMBER_COLUMNS = ("가입일자", "사용자코드", "연령대", "성별", "가입건수")


def load_new_members(start: str | None = None, end: str | None = None) -> pd.DataFrame:
    """일별 신규가입자(2018-07-20~). 반환 컬럼: 가입일자, 사용자코드, 연령대, 성별, 가입건수.

    - 같은 날·연령대·성별이 여러 줄로 나뉜 경우가 원본에 있다. 집계할 때 반드시 합계(sum)를 쓴다.
    - 2019년 말 시스템 개편 전에는 성별을 모으지 않았다(2018~2022 엑셀 파일의 메모). 그 기간 성별은 결측이다.
    """
    frames = []
    folder = config.DATA_RAW / "new_members"
    for path in sorted(
        p for p in folder.iterdir() if p.suffix.lower() in (".csv", ".xlsx")
    ):
        raw = read_table(path, header=None).iloc[:, : len(NEW_MEMBER_COLUMNS)]
        raw = raw.set_axis(list(NEW_MEMBER_COLUMNS), axis=1)
        first = str(raw.iat[0, 0]).strip()
        if not re.match(
            r"\d{4}-\d{2}-\d{2}", first
        ):  # 머리글 줄이면 뺀다 (머리글 없는 파일도 있음)
            raw = raw.iloc[1:]
        raw = raw[raw["가입일자"].str.strip() != ""]
        frames.append(raw)
    df = pd.concat(frames, ignore_index=True)

    date = pd.to_datetime(df["가입일자"].str.strip().str[:10], format="%Y-%m-%d")
    out = pd.DataFrame(
        {
            "가입일자": date,
            "사용자코드": df["사용자코드"].str.strip().astype("category"),
            "연령대": normalize_age(df["연령대"]),
            "성별": normalize_sex(df["성별"]),
            "가입건수": _to_number(df["가입건수"], "Int64"),
        }
    )
    out = out[_period_mask(out["가입일자"], start, end)]
    return out.sort_values("가입일자", kind="stable").reset_index(drop=True)


# ---- 따릉이 대여소 정보 OA-13252 ----------------------------------------------
STATION_COLUMNS = (
    "대여소번호", "대여소명", "자치구", "상세주소", "위도", "경도",
    "설치일시", "LCD거치대수", "QR거치대수", "운영방식",
)  # fmt: skip
_STATION_HEADER_ROWS = 5  # 엑셀 위쪽 5줄이 병합된 머리글이다


def list_station_snapshots() -> dict[str, Path]:
    """대여소 정보 파일을 기준 시점("2024-06" 등) 순으로 돌려준다."""
    found = {}
    for path in (config.DATA_RAW / "stations").glob("*.xlsx"):
        m = re.search(r"(\d{2})\.(\d{1,2})월", path.name)
        if m:
            found[f"20{m.group(1)}-{int(m.group(2)):02d}"] = path
    return dict(sorted(found.items()))


def load_stations(asof: str | None = None) -> pd.DataFrame:
    """대여소 목록 한 시점. asof="2024-12"처럼 주고, 생략하면 가장 최근 시점.

    반환 컬럼: 대여소번호, 대여소명, 자치구, 상세주소, 위도, 경도, 설치일시, LCD거치대수, QR거치대수,
    거치대수(LCD+QR), 운영방식, 기준시점
    """
    snaps = list_station_snapshots()
    if not snaps:
        raise FileNotFoundError(config.DATA_RAW / "stations")
    asof = asof or list(snaps)[-1]
    if asof not in snaps:
        raise KeyError(f"{asof} 기준 파일이 없다. 있는 시점: {list(snaps)}")
    path = snaps[asof]

    raw = pd.read_excel(path, header=None, dtype=object, engine="openpyxl")
    if not (
        str(raw.iat[2, 4]).strip() == "위도" and str(raw.iat[2, 5]).strip() == "경도"
    ):
        raise ValueError(
            f"{path.name}: 머리글 모양이 예상과 다르다. load_stations()를 고쳐야 한다."
        )
    df = raw.iloc[_STATION_HEADER_ROWS:, : len(STATION_COLUMNS)]
    df = df.set_axis(list(STATION_COLUMNS), axis=1)
    df = df[df["대여소번호"].astype(str).str.strip().str.fullmatch(r"\d+(\.0)?")]

    lcd = _to_number(df["LCD거치대수"], "Int16")
    qr = _to_number(df["QR거치대수"], "Int16")
    return pd.DataFrame(
        {
            "대여소번호": normalize_station_id(df["대여소번호"]),
            "대여소명": df["대여소명"].astype("string").str.strip(),
            "자치구": df["자치구"].astype("string").str.strip().astype("category"),
            "상세주소": df["상세주소"].astype("string").str.strip(),
            "위도": _to_number(df["위도"]),
            "경도": _to_number(df["경도"]),
            "설치일시": pd.to_datetime(df["설치일시"], errors="coerce"),
            "LCD거치대수": lcd,
            "QR거치대수": qr,
            "거치대수": (lcd.fillna(0) + qr.fillna(0)).astype("Int16"),
            "운영방식": df["운영방식"].astype("string").str.strip().astype("category"),
            "기준시점": asof,
        }
    ).reset_index(drop=True)


def load_stations_union() -> pd.DataFrame:
    """모든 시점의 대여소를 합친 목록. 대여소마다 가장 최근 시점의 정보를 남긴다.

    대여이력에는 중간에 없어진 대여소도 나오므로, 좌표를 붙일 때는 이 목록이 빠짐이 적다.
    처음확인·마지막확인은 받은 파일 시점 기준이다(실제 설치·폐쇄일이 아님).
    """
    allsnap = pd.concat(
        [load_stations(s) for s in list_station_snapshots()], ignore_index=True
    )
    seen = allsnap.groupby("대여소번호")["기준시점"].agg(
        처음확인="min", 마지막확인="max"
    )
    latest = allsnap.sort_values("기준시점").drop_duplicates("대여소번호", keep="last")
    return latest.merge(seen, on="대여소번호").reset_index(drop=True)


# ---- 서울교통공사 역별 시간대별 승하차 OA-12921 -----------------------------------
SUBWAY_ID_COLUMNS = ("연번", "날짜", "호선", "역번호", "역명", "구분")
# 시간대 컬럼 20개: "06시 이전", 06-07 ... 23-24, "24시 이후"
SUBWAY_HOURS = (5, *range(6, 24), 24)  # 5 = 06시 이전, 24 = 24시 이후


def load_subway_ridership(
    years: Iterable[int] | None = None, long: bool = True
) -> pd.DataFrame:
    """역별·일별·시간대별 승하차 인원(1~8호선, 서울교통공사 관할만).

    long=True(기본): 한 줄 = 날짜·역·승하차구분·시간대. 컬럼: 날짜, 호선, 역번호, 역사_ID, 역명, 구분, 시간대, 인원
      - 시간대 5는 "06시 이전", 24는 "24시 이후"를 뜻한다(나머지는 h:00~h:59).
    long=False: 시간대가 컬럼("05"~"24")으로 펼쳐진 원본 모양.
    역사_ID는 역사마스터(load_subway_stations)와 바로 합칠 수 있는 4자리 번호다(역번호 205 → "0205").
    역명은 시기마다 바뀐 경우가 있으니(당고개→불암산 등) 역 단위로 합칠 때는 역사_ID를 쓴다.
    """
    frames = []
    for path in sorted((config.DATA_RAW / "subway_ridership").glob("*.csv")):
        raw = read_table(path)
        hour_cols = list(raw.columns[len(SUBWAY_ID_COLUMNS) :])
        if (
            len(hour_cols) != len(SUBWAY_HOURS)
            or "이전" not in hour_cols[0]
            or "이후" not in hour_cols[-1]
        ):
            raise ValueError(
                f"{path.name}: 시간대 컬럼 모양이 예상과 다르다: {hour_cols[:2]} ... {hour_cols[-1:]}"
            )
        raw = raw.set_axis(
            [*SUBWAY_ID_COLUMNS, *[f"{h:02d}" for h in SUBWAY_HOURS]], axis=1
        )
        raw = raw[raw["날짜"].str.strip() != ""]  # 2025년 파일 끝의 빈 줄
        frames.append(raw.drop(columns="연번"))
    df = pd.concat(frames, ignore_index=True)

    df["날짜"] = pd.to_datetime(df["날짜"].str.strip(), format="%Y-%m-%d")
    if years is not None:
        df = df[df["날짜"].dt.year.isin(list(years))]
    df["역번호"] = df["역번호"].str.strip()
    df.insert(df.columns.get_loc("역번호") + 1, "역사_ID", df["역번호"].str.zfill(4))
    for col in ("호선", "역명", "구분"):
        df[col] = df[col].str.strip().astype("category")
    hour_names = [f"{h:02d}" for h in SUBWAY_HOURS]
    for col in hour_names:
        df[col] = _to_number(df[col], "Int32")
    if not long:
        return df.reset_index(drop=True)

    out = df.melt(
        id_vars=["날짜", "호선", "역번호", "역사_ID", "역명", "구분"],
        value_vars=hour_names,
        var_name="시간대",
        value_name="인원",
    )
    out["시간대"] = out["시간대"].astype("int8")
    return out.sort_values(
        ["날짜", "역사_ID", "구분", "시간대"], kind="stable"
    ).reset_index(drop=True)


# ---- 서울시 역사마스터 OA-21232 -------------------------------------------------
def load_subway_stations(lines: Iterable[str] | None = None) -> pd.DataFrame:
    """지하철역 좌표(역사_ID, 역사명, 호선, 위도, 경도). 환승역은 호선마다 한 줄씩 있다.

    주의: 이 데이터는 다운로드 권한을 받아 쓰는 자료라 원본·가공본 모두 공개 저장소에 올리지 않는다.
    data/processed/에 저장하지 말고, 대여소별 "역 거리" 같은 결과값만 저장한다.
    """
    path = config.DATA_RAW / "subway_stations" / "서울시 역사마스터 정보.csv"
    df = read_table(path)
    df = df.assign(
        역사_ID=df["역사_ID"].str.strip().str.zfill(4),
        역사명=df["역사명"].str.strip(),
        호선=df["호선"].str.strip(),
        위도=_to_number(df["위도"]),
        경도=_to_number(df["경도"]),
    )
    if lines is not None:
        df = df[df["호선"].isin(list(lines))]
    return df.reset_index(drop=True)


# ---- zip 속 월별 csv (대여이력, 대여가능 수량) ---------------------------------------
def zip_csv_members(zip_path: str | Path) -> list[tuple[str, zipfile.ZipInfo]]:
    """zip 안의 csv를 ("2024-01", ZipInfo) 목록으로. 월은 파일명 끝 4자리(YYMM)에서 읽는다."""
    members = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            m = re.search(r"(\d{2})(\d{2})\.csv$", info.filename, flags=re.IGNORECASE)
            if not info.is_dir() and m:
                members.append((f"20{m.group(1)}-{m.group(2)}", info))
    return sorted(members, key=lambda x: x[0])


def _zip_paths(folder: str, year: int) -> list[Path]:
    paths = sorted(
        p for p in (config.DATA_RAW / folder).glob("*.zip") if str(year) in p.name
    )
    if not paths:
        raise FileNotFoundError(f"data/raw/{folder}/에 {year}년 zip이 없다")
    return paths


def available_months(folder: str, year: int) -> list[str]:
    """data/raw/<folder>/의 그 해 zip들에 들어 있는 달 목록 ("2024-01", ...)."""
    return sorted(
        {ym for p in _zip_paths(folder, year) for ym, _ in zip_csv_members(p)}
    )


def _iter_zip_chunks(
    folder: str,
    year: int,
    months: Iterable[str] | None,
    mapping: dict[str, str],
    read_columns: Iterable[str],
    clean: Callable[[pd.DataFrame], pd.DataFrame],
    chunksize: int,
) -> Iterator[tuple[str, pd.DataFrame]]:
    """zip 속 월별 csv를 청크로 읽어 (월, clean(청크))를 내놓는다. read_columns는 표준 컬럼명."""
    wanted = set(months) if months is not None else None
    read = set(read_columns)
    for zip_path in _zip_paths(folder, year):
        with zipfile.ZipFile(zip_path) as zf:
            for ym, info in zip_csv_members(zip_path):
                if wanted is not None and ym not in wanted:
                    continue
                with zf.open(info) as fh:
                    encoding = detect_encoding(fh.read(_SAMPLE_BYTES))
                with zf.open(info) as fh:
                    header = list(pd.read_csv(fh, nrows=0, encoding=encoding).columns)
                std = _standard_names(header, mapping, info.filename)
                usecols = [
                    raw for raw, name in zip(header, std, strict=True) if name in read
                ]
                with zf.open(info) as fh:
                    reader = pd.read_csv(
                        fh,
                        usecols=usecols,
                        dtype=str,
                        keep_default_na=False,
                        encoding=encoding,
                        encoding_errors="replace",
                        chunksize=chunksize,
                    )
                    for chunk in reader:
                        chunk.columns = [mapping[str(c).strip()] for c in chunk.columns]
                        yield ym, clean(chunk)


def _months_to_build(
    folder: str, year: int, months: Iterable[str] | None, out_dir: Path, overwrite: bool
) -> list[str]:
    todo = available_months(folder, year)
    if months is not None:
        wanted = set(months)
        missing = sorted(wanted - set(todo))
        if missing:
            raise ValueError(
                f"{folder} {year}년 zip에 없는 달: {missing}. 있는 달: {todo}"
            )
        todo = [m for m in todo if m in wanted]
    if not overwrite:
        done = [m for m in todo if (out_dir / f"{m}.parquet").exists()]
        if done:
            print(
                f"  이미 있어서 건너뜀: {', '.join(done)} (다시 만들려면 overwrite=True)"
            )
        todo = [m for m in todo if m not in done]
    return todo


def _write_monthly_parquet(
    chunks: Iterator[tuple[str, pd.DataFrame]], out_dir: Path
) -> list[Path]:
    """(월, 청크) 흐름을 월별 parquet로 쓴다. 쓰는 중에는 .partial 파일이라 중간에 멈춰도 안전하다."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    writer: pq.ParquetWriter | None = None
    month: str | None = None

    def finish() -> None:
        nonlocal writer
        if writer is None or month is None:
            return
        writer.close()
        writer = None
        final = out_dir / f"{month}.parquet"
        os.replace(out_dir / f"{month}.parquet.partial", final)
        written.append(final)
        print(f"  저장: {final.relative_to(config.ROOT)}")

    for ym, chunk in chunks:
        # 범주형은 청크마다 범주가 달라 스키마가 어긋나므로 문자열로 저장한다(읽을 때 다시 범주형으로)
        cats = chunk.select_dtypes("category").columns
        table = pa.Table.from_pandas(
            chunk.astype(dict.fromkeys(cats, "string")), preserve_index=False
        )
        if ym != month:
            finish()
            month = ym
            writer = pq.ParquetWriter(
                out_dir / f"{ym}.parquet.partial", table.schema, compression="zstd"
            )
        assert writer is not None
        writer.write_table(table.cast(writer.schema))
    finish()
    return written


def _read_monthly_parquet(
    folder: Path,
    months: Iterable[str] | None,
    columns: Iterable[str] | None,
    filters: list | None,
    categories: Iterable[str],
) -> pd.DataFrame:
    paths = sorted(folder.glob("*.parquet"))
    if months is not None:
        wanted = set(months)
        paths = [p for p in paths if p.stem in wanted]
    if not paths:
        raise FileNotFoundError(
            f"{folder}에 parquet가 없다. 먼저 *_to_parquet()를 실행할 것"
        )
    cols = list(columns) if columns is not None else None
    frames = []
    for p in paths:
        part = pd.read_parquet(p, columns=cols, filters=filters)
        for col in categories:
            if col in part.columns:
                part[col] = part[col].astype("category")
        frames.append(part)
    # 달마다 범주 목록이 달라 그냥 이어 붙이면 범주형이 풀린다 → 범주 목록을 합쳐 맞춘다
    for col in categories:
        if col in frames[0].columns:
            union = sorted(set().union(*(f[col].cat.categories for f in frames)))
            for f in frames:
                f[col] = f[col].cat.set_categories(union)
    return pd.concat(frames, ignore_index=True)


def cached(
    name: str, build: Callable[[], pd.DataFrame], refresh: bool = False
) -> pd.DataFrame:
    """data/interim/<name>.parquet가 있으면 읽고, 없으면 build()로 만들어 저장한 뒤 돌려준다.

    원본을 읽는 데 오래 걸리는 표를 노트북에서 다시 실행할 때 쓴다(원본이 바뀌면 refresh=True).
        usage = loaders.cached("usage_monthly", loaders.load_usage_monthly)
    """
    path = _parquet_path(name, "interim")
    if path.exists() and not refresh:
        return pd.read_parquet(path)
    df = build()
    save_parquet(df, name, where="interim")
    return df


# ---- 따릉이 대여이력 OA-15182 ---------------------------------------------------
RENT_COLUMNS = {
    "자전거번호": "자전거번호",
    "대여일시": "대여일시",
    "대여 대여소번호": "대여소번호",
    "대여 대여소명": "대여소명",
    "대여거치대": "대여거치대",
    "반납일시": "반납일시",
    "반납대여소번호": "반납대여소번호",
    "반납대여소명": "반납대여소명",
    "반납거치대": "반납거치대",
    "이용시간(분)": "이용시간_분",
    "이용거리(M)": "이용거리_m",
    "생년": "생년",
    "성별": "성별",
    "이용자종류": "이용자종류",
    "대여대여소ID": "대여대여소ID",
    "반납대여소ID": "반납대여소ID",
    "자전거구분": "자전거구분",
}
# 기본으로 남기는 컬럼. 자전거번호(개별 자전거 식별)와 대여소명(대여소 정보로 붙임)은 뺀다.
RENT_DEFAULT_COLUMNS = (
    "대여일시", "대여소번호", "반납일시", "반납대여소번호",
    "이용시간_분", "이용거리_m", "생년", "성별", "이용자종류", "자전거구분",
)  # fmt: skip
RENT_CATEGORIES = ("대여소번호", "반납대여소번호", "성별", "이용자종류", "자전거구분")


def _check_columns(cols: Iterable[str], allowed: Iterable[str]) -> None:
    bad = sorted(set(cols) - set(allowed))
    if bad:
        raise ValueError(f"없는 컬럼 {bad}. 쓸 수 있는 컬럼: {list(allowed)}")


def _clean_rent(chunk: pd.DataFrame) -> pd.DataFrame:
    out = chunk.copy()
    for col in ("대여일시", "반납일시"):
        if col in out:
            out[col] = pd.to_datetime(
                out[col].str.strip(), format="%Y-%m-%d %H:%M:%S", errors="coerce"
            )
    for col in ("대여소번호", "반납대여소번호"):
        if col in out:
            out[col] = normalize_station_id(out[col])
    numeric = {"이용시간_분": "Int32", "이용거리_m": "float64", "생년": "Int16",
               "대여거치대": "Int16", "반납거치대": "Int16"}  # fmt: skip
    for col, dtype in numeric.items():
        if col in out:
            out[col] = _to_number(out[col], dtype)
    if "성별" in out:
        out["성별"] = normalize_sex(out["성별"])
    for col in ("이용자종류", "자전거구분"):
        if col in out:
            s = out[col].astype("string").str.strip()
            out[col] = s.mask(s.isin(MISSING_TOKENS)).astype("category")
    return out


def iter_rent_history(
    year: int,
    months: Iterable[str] | None = None,
    columns: Iterable[str] = RENT_DEFAULT_COLUMNS,
    chunksize: int = 1_000_000,
) -> Iterator[tuple[str, pd.DataFrame]]:
    """대여이력 zip을 풀지 않고 청크 단위로 읽는다. ("2024-01", 정리된 청크)를 차례로 내놓는다.

    months=["2024-03"]처럼 일부 달만 읽을 수 있다. 한 달 csv가 수백 MB라 통째로 읽지 않는다.
    """
    cols = list(columns)
    _check_columns(cols, RENT_COLUMNS.values())

    def clean(chunk: pd.DataFrame) -> pd.DataFrame:
        return _clean_rent(chunk)[cols]

    yield from _iter_zip_chunks(
        "rent_history", year, months, RENT_COLUMNS, cols, clean, chunksize
    )


def rent_history_to_parquet(
    year: int,
    months: Iterable[str] | None = None,
    columns: Iterable[str] = RENT_DEFAULT_COLUMNS,
    overwrite: bool = False,
    chunksize: int = 1_000_000,
) -> list[Path]:
    """대여이력 한 해를 data/interim/rent_history/YYYY-MM.parquet 월별 파일로 바꾼다.

    이미 만든 달은 건너뛰므로 노트북을 다시 실행해도 빠르다. 컬럼을 바꿨으면 overwrite=True로 다시 만든다.
    한 해 전체는 시간이 오래 걸린다(csv 약 7GB). 처음에는 months=["2024-05"]처럼 한 달로 시험해 본다.
    """
    out_dir = config.DATA_INTERIM / "rent_history"
    todo = _months_to_build("rent_history", year, months, out_dir, overwrite)
    if not todo:
        return []
    return _write_monthly_parquet(
        iter_rent_history(year, todo, columns, chunksize), out_dir
    )


def load_rent_history(
    months: Iterable[str] | None = None,
    columns: Iterable[str] | None = None,
    filters: list | None = None,
) -> pd.DataFrame:
    """rent_history_to_parquet()로 만든 parquet를 읽는다.

    months=["2024-05", "2024-06"], columns=["대여일시", "대여소번호"]처럼 필요한 만큼만 읽는다.
    filters는 pyarrow 형식: [("이용시간_분", ">", 0)]

    원본 값은 거르지 않고 그대로 둔다. 2024-12 기준으로 확인한 것:
    - 생년에 0, 2099 같은 값이 있다 → 연령 분석 전에 범위를 정해 거른다
    - 반납대여소번호가 빈 기록이 있다(약 0.5%). 대여소 목록에 없는 반납 번호(00003, 099xx, 88888)도
      아주 조금 있다(센터·정비 코드로 보임)
    - 이용시간 0분, 이용거리 0m 기록이 있다 → 제외 기준은 분석에서 정한다
    """
    return _read_monthly_parquet(
        config.DATA_INTERIM / "rent_history", months, columns, filters, RENT_CATEGORIES
    )


# ---- 대여소별 대여가능 수량(1시간) OA-22382 ------------------------------------------
AVAILABILITY_COLUMNS = {
    "일시": "날짜",
    "대여소번호": "대여소번호",
    "대여소명": "대여소명",
    "시간대": "시간대",
    "거치대수량": "거치대수량",
}
# "거치대수량"은 원본 컬럼명 그대로다. 데이터셋 이름은 "대여가능 수량"이다(그 시각 대여소에 있는 자전거 수).
AVAILABILITY_DEFAULT_COLUMNS = ("일시", "대여소번호", "거치대수량")
AVAILABILITY_CATEGORIES = ("대여소번호", "대여소명")


def _clean_availability(chunk: pd.DataFrame) -> pd.DataFrame:
    out = chunk.copy()
    date = pd.to_datetime(out["날짜"].str.strip(), format="%Y-%m-%d", errors="coerce")
    hour = _to_number(out["시간대"], "Int8")
    out["일시"] = date + pd.to_timedelta(hour.astype("float64"), unit="h")
    out["날짜"] = date
    out["시간대"] = hour
    if "대여소번호" in out:
        out["대여소번호"] = normalize_station_id(out["대여소번호"])
    if "거치대수량" in out:
        out["거치대수량"] = _to_number(out["거치대수량"], "Int16")
    if "대여소명" in out:
        out["대여소명"] = out["대여소명"].str.strip()
    return out


def iter_availability(
    year: int,
    months: Iterable[str] | None = None,
    columns: Iterable[str] = AVAILABILITY_DEFAULT_COLUMNS,
    chunksize: int = 2_000_000,
) -> Iterator[tuple[str, pd.DataFrame]]:
    """대여가능 수량 zip(분기별)을 풀지 않고 청크로 읽는다. ("2024-01", 청크)를 내놓는다.

    2024-04 파일은 4월 20일부터만 들어 있다(받은 파일 기준). 하루 평균을 낼 때 기간을 맞출 것.
    """
    cols = list(columns)
    _check_columns(cols, ["일시", *AVAILABILITY_COLUMNS.values()])
    read = set(cols) - {"일시"} | {"날짜", "시간대"}  # 일시는 날짜 + 시간대로 만든다

    def clean(chunk: pd.DataFrame) -> pd.DataFrame:
        return _clean_availability(chunk)[cols]

    yield from _iter_zip_chunks(
        "availability", year, months, AVAILABILITY_COLUMNS, read, clean, chunksize
    )


def availability_to_parquet(
    year: int,
    months: Iterable[str] | None = None,
    columns: Iterable[str] = AVAILABILITY_DEFAULT_COLUMNS,
    overwrite: bool = False,
) -> list[Path]:
    """대여가능 수량 한 해를 data/interim/availability/YYYY-MM.parquet로 바꾼다."""
    out_dir = config.DATA_INTERIM / "availability"
    todo = _months_to_build("availability", year, months, out_dir, overwrite)
    if not todo:
        return []
    return _write_monthly_parquet(iter_availability(year, todo, columns), out_dir)


def load_availability(
    months: Iterable[str] | None = None,
    columns: Iterable[str] | None = None,
    filters: list | None = None,
) -> pd.DataFrame:
    """availability_to_parquet()로 만든 parquet를 읽는다."""
    return _read_monthly_parquet(
        config.DATA_INTERIM / "availability",
        months,
        columns,
        filters,
        AVAILABILITY_CATEGORIES,
    )


# ---- 중간·결과 파일 저장 ---------------------------------------------------------
def _parquet_path(name: str, where: str) -> Path:
    base = {"processed": config.DATA_PROCESSED, "interim": config.DATA_INTERIM}.get(
        where
    )
    if base is None:
        raise ValueError('where는 "processed" 또는 "interim"')
    return base / (name if name.endswith(".parquet") else f"{name}.parquet")


def save_parquet(df: pd.DataFrame, name: str, where: str = "processed") -> Path:
    """data/processed/(기본, git에 올라감) 또는 data/interim/(git 제외)에 parquet로 저장한다.

    processed/는 공개 저장소에 올라가므로 역사마스터 원본처럼 재배포가 안 되는 데이터는
    where="interim"에 둔다.
    """
    path = _parquet_path(name, where)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def read_parquet(name: str, where: str = "processed", **kwargs) -> pd.DataFrame:
    """save_parquet()로 저장한 파일을 읽는다. columns=[...], filters=[...]를 넘길 수 있다."""
    return pd.read_parquet(_parquet_path(name, where), **kwargs)
