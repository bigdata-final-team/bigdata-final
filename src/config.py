"""프로젝트 공통 설정: 폴더 경로, 팀이 아직 정하지 않은 임시값, 그래프에 적을 출처 문구.

노트북에서:
    import sys; sys.path.append("..")
    from src import config
    config.DATA_RAW / "stations"
"""

from __future__ import annotations

from pathlib import Path

# ---- 경로 -----------------------------------------------------------------
# src/의 부모 폴더가 프로젝트 루트다. 어느 PC, 어느 폴더에서 노트북을 열어도 같은 위치를 가리킨다.
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"  # 원본. 읽기만 한다
DATA_INTERIM = (
    ROOT / "data" / "interim"
)  # 대여이력 parquet 같은 큰 중간 결과 (git 제외)
DATA_PROCESSED = (
    ROOT / "data" / "processed"
)  # 분석용 결과 (git 포함, 공개 저장소에 올라감)
FIGURES = ROOT / "figures"  # 발표용 그림

# ---- 팀이 아직 정하지 않은 값 (임시값) ----------------------------------------
# docs/주제-및-분석방향.md "팀이 정할 것" 표와 같은 값이다. 팀이 정하면 여기 한 곳만 고친다.
# 시간대 h는 h:00~h:59를 뜻한다. 예: 7 → 07:00~07:59
COMMUTE_AM_HOURS: tuple[int, ...] = (7, 8)  # 출근 07~09시 (임시값)
COMMUTE_PM_HOURS: tuple[int, ...] = (17, 18, 19)  # 퇴근 17~20시 (임시값)
COMMUTE_HOURS: tuple[int, ...] = COMMUTE_AM_HOURS + COMMUTE_PM_HOURS
TREND_PERIOD = ("2022-01-01", "2026-06-30")  # 추세·예측 기간 (임시값)
DETAIL_YEAR = 2024  # 대여·반납 상세 분석 연도 (임시값)
NEAR_STATION_M = 300  # 역 인근 반경, m (임시값)
FAR_STATION_M = 1000  # 이보다 멀면 "역에서 먼" 대여소, m (임시값)


def provisional_note() -> str:
    """그래프 아래에 붙일 임시값 안내 문구. 팀이 값을 확정하면 이 함수는 지워도 된다."""
    am = f"{COMMUTE_AM_HOURS[0]:02d}~{COMMUTE_AM_HOURS[-1] + 1:02d}시"
    pm = f"{COMMUTE_PM_HOURS[0]:02d}~{COMMUTE_PM_HOURS[-1] + 1:02d}시"
    return (
        f"임시 기준: 출퇴근 시간대 {am}·{pm}, 역 인근 {NEAR_STATION_M}m, "
        f"역에서 먼 대여소 {FAR_STATION_M / 1000:g}km 초과"
    )


# ---- 데이터 출처 ------------------------------------------------------------
# viz.add_source(fig, "rent_history", "stations")처럼 키로 쓴다. README "데이터 출처" 표와 같은 이름이다.
SOURCES: dict[str, str] = {
    "usage_monthly": "서울 열린데이터광장 「서울시 공공자전거 따릉이 이용정보(월별)」(OA-15248)",
    "usage_hourly": "서울 열린데이터광장 「서울시 공공자전거 이용정보(시간대별)」(OA-15245)",
    "new_members": "서울 열린데이터광장 「서울시 공공자전거 따릉이 신규가입자 정보(일별)」(OA-15243)",
    "rent_history": "서울 열린데이터광장 「서울시 공공자전거 따릉이 대여이력 정보」(OA-15182)",
    "availability": "서울 열린데이터광장 「서울시 대여소별 공공자전거 따릉이 대여가능 수량」(OA-22382)",
    "stations": "서울 열린데이터광장 「서울시 공공자전거 따릉이 대여소 정보」(OA-13252)",
    "subway_ridership": "서울 열린데이터광장 「서울교통공사 역별 일별 시간대별 승하차인원」(OA-12921)",
    "subway_stations": "서울 열린데이터광장 「서울시 역사마스터 정보」(OA-21232)",
    "asos": "기상청 기상자료개방포털 「종관기상관측(ASOS)」 서울 지점",
    "holidays": "우주항공청 월력요항(관보), 관공서의 공휴일에 관한 규정",
    "osm": "© OpenStreetMap contributors",
}
