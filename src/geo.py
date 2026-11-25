"""좌표 계산: 거리, 가장 가까운 지하철역, 역 인근 구분.

from src import geo, loaders
bikes = loaders.load_stations_union()
subway = loaders.load_subway_stations()
bikes = geo.add_station_proximity(bikes, subway)   # 최근접역, 역거리_m, 역근접구분 추가
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

EARTH_RADIUS_M = 6_371_008.8  # 지구 평균 반지름(m)
PROXIMITY_ORDER = ("역 인근", "중간", "역에서 먼")


def haversine_m(lat1, lon1, lat2, lon2) -> np.ndarray:
    """두 지점(위도·경도, 도 단위) 사이 거리(m). 배열끼리 넣으면 원소별로 계산한다."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = p2 - p1
    dl = np.radians(lon2) - np.radians(lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def nearest(
    points: pd.DataFrame,
    targets: pd.DataFrame,
    k: int = 1,
    lat: str = "위도",
    lon: str = "경도",
    target_cols: tuple[str, ...] = ("역사_ID", "역사명", "호선"),
) -> pd.DataFrame:
    """points 각 행에서 가장 가까운 targets k개. points와 같은 인덱스로 돌려준다.

    k=1이면 컬럼: <target_cols...>, 거리_m. k>1이면 컬럼 이름 뒤에 _1, _2...가 붙는다.
    좌표가 비어 있는 행은 결과도 비어 있다.
    """
    from sklearn.neighbors import BallTree

    tgt = targets.dropna(subset=[lat, lon]).reset_index(drop=True)
    tree = BallTree(
        np.radians(tgt[[lat, lon]].to_numpy(dtype=float)), metric="haversine"
    )
    ok = points[[lat, lon]].notna().all(axis=1)
    dist, idx = tree.query(
        np.radians(points.loc[ok, [lat, lon]].to_numpy(dtype=float)), k=k
    )

    ok_pos = np.flatnonzero(ok.to_numpy())
    cols: dict[str, np.ndarray] = {}
    for j in range(k):
        suffix = "" if k == 1 else f"_{j + 1}"
        picked = tgt.iloc[idx[:, j]]
        for col in target_cols:
            values = np.full(len(points), None, dtype=object)
            values[ok_pos] = picked[col].to_numpy(dtype=object)
            cols[f"{col}{suffix}"] = values
        d = np.full(len(points), np.nan)
        d[ok_pos] = dist[:, j] * EARTH_RADIUS_M
        cols[f"거리_m{suffix}"] = d
    out = pd.DataFrame(cols, index=points.index)
    return out


def classify_distance(
    dist_m: pd.Series, near_m: float | None = None, far_m: float | None = None
) -> pd.Series:
    """거리(m)를 '역 인근'(≤near_m) / '중간' / '역에서 먼'(>far_m)으로 나눈다. 기준 기본값은 config 임시값."""
    near_m = config.NEAR_STATION_M if near_m is None else near_m
    far_m = config.FAR_STATION_M if far_m is None else far_m
    cut = pd.cut(
        dist_m,
        bins=[-np.inf, near_m, far_m, np.inf],
        labels=PROXIMITY_ORDER,
        right=True,
    )
    return pd.Series(cut, index=dist_m.index, name="역근접구분")


def add_station_proximity(
    stations: pd.DataFrame,
    subway: pd.DataFrame,
    near_m: float | None = None,
    far_m: float | None = None,
) -> pd.DataFrame:
    """대여소 표에 최근접역_ID, 최근접역, 최근접역_호선, 역거리_m, 역근접구분을 붙인 복사본.

    subway는 loaders.load_subway_stations() 결과(위도·경도 컬럼). 환승역은 호선마다 좌표가 따로 있어
    그중 가장 가까운 좌표까지의 거리가 된다. 출입구가 아니라 역사마스터의 역 대표 좌표 기준이다.
    """
    near = nearest(stations, subway, k=1, target_cols=("역사_ID", "역사명", "호선"))
    out = stations.copy()
    out["최근접역_ID"] = near["역사_ID"].astype("string")
    out["최근접역"] = near["역사명"].astype("string")
    out["최근접역_호선"] = near["호선"].astype("string")
    out["역거리_m"] = near["거리_m"].astype("float64").round(1)
    out["역근접구분"] = classify_distance(out["역거리_m"], near_m, far_m)
    return out
