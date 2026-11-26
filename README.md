<div align="center">

# 🚲 bigdata-final

**따릉이는 어떻게 이용되고 있고, 앞으로 어떤 이용이 늘어날까** (가제)

빅데이터분석 기말 팀프로젝트 · 서울시 공공자전거 따릉이 이용 실태 분석과 이용 방향 예측

[![CI](https://github.com/bigdata-final-team/bigdata-final/actions/workflows/ci.yml/badge.svg)](https://github.com/bigdata-final-team/bigdata-final/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![Prophet](https://img.shields.io/badge/Prophet-time%20series-0467DF)

[주제](#주제) · [분석 흐름](#분석-흐름) · [데이터 출처](#데이터-출처) · [환경](#환경) · [폴더 구조](#폴더-구조) · [작업 흐름](#작업-흐름) · [협업 규칙](CONTRIBUTING.md)

</div>

## 주제

따릉이 이용 데이터를 여러 각도로 나눠 보고, 따릉이가 지금 무엇에 쓰이고 있는지와 앞으로 어떤 이용이 늘거나 줄지를 예측합니다.

1. **현재 이용 실태** — 따릉이 이용을 출퇴근·여가·생활 이용으로 나누고, 유형별 규모와 특징을 비교해 현재 이용 결과를 산출한다
2. **이용 방향 예측** — 이용 유형별·연령대별 추세를 학습해 어떤 이용이 증가하고 어떤 이용이 감소할지 예측한다

### 출퇴근 이용을 찾는 방법

데이터에는 이용 목적이 없습니다. 그래서 대여이력의 노선(대여 대여소 → 반납 대여소)을 단위로 보고, **평일 같은 시간대에 반복해서 나타나는 노선**을 출퇴근 노선으로 봅니다.

```text
예) 평일 아침 8시대에 A 대여소 → B 대여소 이동이 거의 매일 나타나고,
    저녁 6시대에 B → A 이동도 반복된다  →  출퇴근 노선
```

출퇴근 노선의 수와 이용 건수를 센 뒤, 반복되지 않는 이용(주말 이용, 왕복 이용 등)과 비교해 여가·생활 이용을 나눕니다.

> "날씨가 좋으면 많이 탄다", "20대가 가장 많이 탄다"처럼 당연한 결과는 결론으로 삼지 않습니다. 날씨는 예측에서 보조 변수로만 씁니다.

### 분석 질문

새 분석을 추가할 때는 아래 질문 중 어디에 답하는지 먼저 밝힙니다.

| 질문 | 보는 것 | 단계 |
|------|---------|:----:|
| 얼마나 타는가 | 연도별·월별 이용 규모, 정기권 비중, 신규가입자 | ① |
| 무엇에 타는가 | 출퇴근 노선 수, 출퇴근·여가·생활 이용 비중 | ② ③ |
| 어디서 타는가 | 출퇴근 노선과 여가 이용이 몰리는 대여소 | ② ③ |
| 누가 타는가 | 연령대별 이용 유형 구성과 그 변화 | ④ |
| 앞으로 어떤 이용이 늘고 줄까 | 유형별·연령대별 추세 예측 | ⑤ |

## 분석 흐름

1. **이용현황** · `02_usage.ipynb`
   - 연도별·월별 이용 규모, 정기·비정기 비중, 신규가입자 추세
   - 계절성이 크므로 같은 달끼리(전년 동월) 비교한다
2. **출퇴근 노선 판별** · `03_routes.ipynb` (핵심)
   - 대여이력을 날짜 × 대여 시간대 × 노선(대여 대여소 → 반납 대여소)으로 집계한다
   - 평일 같은 시간대에 반복 기준 이상 나타나는 노선을 출퇴근 노선으로 표시한다
   - 아침 A → B, 저녁 B → A처럼 반대 방향이 함께 반복되면 출퇴근 근거를 보강한다
   - 반복되지 않는 이용은 주말·공휴일 이용, 왕복 이용(대여소 = 반납소) 등을 기준으로 여가와 생활·기타로 나눈다
   - 출퇴근 노선 수와 노선별 이용 건수를 산출한다
   - 교차 확인: 시간대별 이용정보로 주말을 여가 기준선으로 삼아 구한 통근 비중과 비교한다
3. **출퇴근 vs 여가 비교, 현재 이용 결과** · `04_compare.ipynb`
   - 유형별 시간대·요일 분포, 이용시간·이동거리, 정기권 비중 비교
   - 대여소 유형 군집(K-means). 기대 유형은 출퇴근형·여가형·생활형이고, 이름은 결과를 보고 붙인다
   - 지도: 출퇴근 노선, 여가 이용이 몰리는 대여소
   - (선택) 출퇴근 노선의 출발·도착 대여소가 지하철역 인근인지
   - 산출: 현재 이용 구성(출퇴근·여가·생활 이용 건수와 비중, 출퇴근 노선 수)
4. **연령대별** · `05_age.ipynb`
   - "누가 가장 많이 타는가"가 아니라 연령대마다 무엇에 타는지를 본다
   - 연령대 × 이용 유형 교차, 연령 구성의 연도별 변화
5. **이용 방향 예측** · `06_forecast.ipynb`
   - 이용 유형별·연령대별 시계열을 만들고 Prophet으로 추세와 계절성을 분해한다
   - 기온·강수량(ASOS)은 보조 변수로 넣어 날씨 효과를 뺀 추세를 본다
   - 2022~2025년으로 학습하고 2026년 1~6월 실제값으로 정확도(MAPE 등)를 검증한 뒤, 이후 기간의 증가·감소 방향을 제시한다

**제외·축소한 것**

- 자치구별 공간 확산: 제외
- 지하철 연계: ③의 선택 항목 (출퇴근 노선 해석 보조)
- 공급 신뢰성(대여가능 수량): 여유가 있을 때만
- 날씨: ⑤ 예측의 보조 변수

## 팀이 정할 것 (임시값)

아직 확정하지 않은 값입니다. 임시값으로 진행한 결과에는 임시값임을 표시하고, 확정되면 이 표를 고칩니다. 노트북마다 값을 따로 적지 말고 `src/config.py`의 상수를 불러 씁니다. 확정되면 그 파일 한 곳만 고칩니다.

| 항목 | 임시값 | 단계 |
|------|--------|:----:|
| 노선 판정 시간 단위 | 미정 (제안: 대여 시각 1시간 단위) | ② |
| 출퇴근 노선 반복 기준 | 미정. 평일 중 며칠 이상 나타나야 하는지 분포를 보고 정한다 | ② |
| 출퇴근 시간대 | 07~09시, 17~20시 (끝 시각 포함 여부도 함께 정한다) | ② ⑤ |
| 출퇴근 시간대 밖 반복 노선 | 미정. 출퇴근에 넣을지, 생활 반복 이용으로 따로 볼지 | ② |
| 여가·생활 구분 기준 | 미정 (주말·공휴일, 왕복 이용, 이용시간 등) | ② |
| 노선 판정·현재 이용 기간 | 대여이력 2024년 1년 (2026년 6월분까지 있음) | ② ③ |
| 예측용 유형별 시계열 | 미정. 대여이력 여러 해에 노선 판정을 적용(용량 큼)하거나, 시간대별 이용정보로 만든다 | ⑤ |
| 분석 기간: 추세·예측 | 2022년 1월 ~ 2026년 6월 | ① ④ ⑤ |
| 이용이 적은 노선·대여소 제외 기준 | 미정 | ② ③ |
| 연령대 '기타' 범주 처리 | 미정 | ④ |
| 역 인근 반경 (선택 분석) | 300m | ③ |

판정 기준에 따라 출퇴근 노선 수가 달라지므로, 기준을 바꿔 가며 결과가 얼마나 변하는지도 함께 보여 줍니다. 발표 전 선행연구를 RISS·DBpia에서 추가로 찾습니다.

## 해석 원칙과 한계

- 대여이력으로는 같은 노선을 반복해서 탄 사람이 같은 사람인지 확인할 수 없습니다 (받은 뒤 컬럼으로 다시 확인). 출퇴근 노선은 "출퇴근으로 볼 수 있는 반복 패턴"으로 표현하고, 인과로 단정하지 않습니다.
- 출퇴근·여가·생활 구분은 노선·요일·시간대로 추정한 값입니다. 결과마다 판정 기준을 함께 적습니다.
- 예측은 과거 추세를 늘린 것이라 요금 개편이나 대여소 증설 같은 정책 변화는 반영하지 못합니다.
- 날씨는 기상청 ASOS 서울(108) 관측소 한 곳의 값으로 서울 전체를 대신합니다.
- 대여소 정보는 6월·12월 기준 스냅샷이라, 기간 중 생기거나 없어진 대여소는 시점이 어긋날 수 있습니다.
- 지하철 자료를 쓸 때는 서울교통공사 1~8호선 중 공사 관할 구간만 포함된다는 점을 적습니다.
- 그래프·표마다 해당하는 한계를 함께 적습니다.

## 팀

| 이름 | GitHub | 역할 |
|------|--------|------|
| 전시원 | [@WoogaJJangka](https://github.com/WoogaJJangka) | 팀장 |
| 김상진 | [@Jin-Y00n](https://github.com/Jin-Y00n) | 팀원 |

## 환경

conda 환경 `bigdata-final` (Python 3.12, conda-forge)을 사용합니다. 패키지와 버전은 [`environment.yml`](environment.yml)에 있습니다. conda는 PowerShell에서만 동작합니다.

```powershell
# 처음 한 번만
git lfs install   # png·jpg·parquet를 Git LFS로 올리기 위해 PC마다 한 번
conda env create -f environment.yml
conda run -n bigdata-final python -m ipykernel install --user --name bigdata-final --display-name bigdata-final

# 설치 확인 (라이브러리 버전 + 행렬 곱·그림 저장 + 랜덤포레스트·Prophet 학습 테스트)
conda run -n bigdata-final python check_env.py
```

VS Code와 PyCharm의 인터프리터도 `bigdata-final`로 선택합니다.

| 용도 | 라이브러리 |
|------|-----------|
| 데이터 처리 | numpy, pandas, polars, pyarrow |
| 통계 | scipy, statsmodels |
| 기계학습 | scikit-learn, xgboost, lightgbm |
| 시계열 예측 | prophet |
| 시각화 | matplotlib, seaborn, plotly |
| 노트북·엑셀 | jupyterlab, ipykernel, openpyxl |
| 코드 검사 | ruff (CI와 같은 버전), mypy (선택) |

라이브러리를 추가하거나 버전을 바꿀 때는 `environment.yml`과 `requirements.txt`에 **같은 버전** 한 줄씩 적고, 아래 명령으로 반영합니다. 두 파일이 어긋나면 `check_env.py`가 "불일치"로 알려 줍니다. conda-forge에 없는 패키지만 `environment.yml`의 `- pip:` 아래에 적습니다.

```powershell
conda env update -n bigdata-final -f environment.yml --prune
```

한글이 깨지면 `$env:PYTHONIOENCODING='utf-8'`을 먼저 실행합니다.

numpy·scipy의 BLAS는 `environment.yml`의 `libblas` 줄로 OpenBLAS에 고정되어 있습니다. Windows 기본값인 MKL은 Jupyter 커널(env 활성화 없이 실행됨)에서 행렬 곱 한 번에 죽어, 그래프 셀마다 커널이 재시작됩니다. 이렇게 되면 위 `conda env update` 명령을 실행한 뒤 `check_env.py`의 "BLAS·그림 저장"이 OK인지 확인합니다.

## 폴더 구조

```
bigdata-final/
├─ data/
│  ├─ raw/         원본 데이터. 데이터셋별 폴더에 받은 그대로 둔다 (git 제외)
│  ├─ interim/     대여이력 월별 parquet 같은 큰 중간 결과 (git 제외, src가 만든다)
│  └─ processed/   전처리·집계를 마친 데이터 (git 포함)
├─ notebooks/      분석 단계별 Jupyter 노트북
├─ src/            여러 노트북에서 같이 쓰는 함수와 설정값 (.py)
├─ figures/        발표용 그림 (viz.save_fig가 저장)
├─ check_env.py      환경 설치 확인 스크립트
├─ environment.yml   conda env 정의 (로컬 설치용)
└─ requirements.txt  같은 버전 목록 (check_env.py와 CI가 읽음)
```

### data/raw/ — 원본 데이터

데이터셋마다 폴더를 나눠 받은 파일을 **그대로** 넣습니다.

```
data/raw/
├─ usage_monthly/      이용정보(월별)        OA-15248
├─ usage_hourly/       이용정보(시간대별)    OA-15245
├─ rent_history/       대여이력              OA-15182
├─ stations/           대여소 정보           OA-13252
├─ new_members/        신규가입자(일별)      OA-15243
├─ weather/            기상청 ASOS
├─ subway_stations/    서울시 역사마스터 (선택, 결과값만 저장소에 올림)
├─ subway_ridership/   서울교통공사 승하차인원 OA-12921 (선택)
└─ availability/       대여가능 수량         OA-22382 (선택)
```

- `src/loaders.py`가 이 폴더 이름으로 파일을 찾습니다. 아직 만들지 않은 폴더(`usage_hourly`, `weather`)도 받을 때 이 이름에 맞춥니다.
- 원본은 절대 덮어쓰지 않습니다. 정리한 결과는 항상 `data/processed/`에 새 파일로 저장합니다. 그래야 실수해도 원본에서 다시 시작할 수 있습니다.
- 용량이 커서 git에 올리지 않습니다. 대신 아래 데이터 출처의 **받은 파일 기록** 표에 받은 범위와 날짜를 적어 두면 다른 컴퓨터에서도 같은 데이터를 다시 받을 수 있습니다.
- 대여이력은 2024년 파일 하나가 zip으로 약 2GB입니다. 디스크 여유 공간을 먼저 확인합니다.

### data/processed/ — 가공 데이터

- 결측치 처리, 형 변환, 병합, 집계 등을 마친 분석용 데이터입니다.
- 큰 데이터는 csv 대신 **parquet** 형식으로 저장합니다. 더 작고 빠르며 자료형이 유지됩니다. parquet 파일은 Git LFS로 관리됩니다 (`git lfs install`을 안 했으면 push가 거부될 수 있습니다).
- GitHub은 100MB가 넘는 일반 파일을 받지 않고, LFS에도 용량 한도가 있습니다. 대여이력은 행 단위 그대로 올리지 말고 날짜 × 시간대 × 노선 같은 집계 결과를 올립니다.
- 저장소가 공개이므로, 재배포가 제한된 데이터는 가공한 것도 올리지 않습니다. 서울시 역사마스터는 원본과 역 좌표를 올리지 않고, 대여소별 역 인근 여부 같은 결과값만 올립니다.

```python
loaders.save_parquet(df, "routes_2024")            # data/processed/routes_2024.parquet
df = loaders.read_parquet("routes_2024")
loaders.save_parquet(df, "tmp", where="interim")   # 올리지 않을 중간 결과는 data/interim/
```

### data/interim/ — 큰 중간 결과

- `loaders.rent_history_to_parquet()`가 대여이력 zip을 풀지 않고 읽어 `data/interim/rent_history/2024-01.parquet`처럼 달마다 저장합니다. 대여가능 수량도 같은 방식(`availability/`)입니다.
- 원본에서 다시 만들 수 있는 파일이라 git에 올리지 않습니다. 이미 만든 달은 건너뛰므로 노트북을 다시 실행해도 빠릅니다.

### notebooks/ — 분석 노트북

분석 흐름의 단계 번호와 맞춰 번호를 붙입니다. [협업 규칙](CONTRIBUTING.md#노트북-규칙)대로 한 노트북은 한 사람이 맡습니다.

| 노트북 | 내용 | 담당 |
|--------|------|------|
| [`00_src_guide.ipynb`](notebooks/00_src_guide.ipynb) | `src/` 공용 함수 사용법. 실제 데이터로 실행한 예시이고 분석 결과가 아님 | |
| `01_preprocessing.ipynb` | raw → processed (필요한 컬럼만 읽기, 청크 처리, 노선 집계) | |
| `02_usage.ipynb` | ① 이용현황 | |
| `03_routes.ipynb` | ② 출퇴근 노선 판별, 이용 유형 나누기 | |
| `04_compare.ipynb` | ③ 출퇴근 vs 여가 비교, 대여소 군집, 현재 이용 결과 | |
| `05_age.ipynb` | ④ 연령대별 | |
| `06_forecast.ipynb` | ⑤ 이용 방향 예측과 2026년 상반기 검증 | |

- 노트북을 열 때 커널로 **bigdata-final** 환경을 고릅니다 (VS Code 오른쪽 위 커널 선택, 또는 `jupyter lab`).
- 노트북 안에서 경로는 `notebooks/` 기준이므로 데이터는 `../data/...`로 접근합니다.
- 같은 코드를 두 번 이상 복사하게 되면 `src/`로 옮길 때입니다.

### src/ — 공용 코드

여러 노트북에서 쓰는 함수와 [팀이 정할 것](#팀이-정할-것-임시값)의 설정값을 모아 둔 곳입니다. 노트북 첫 셀:

```python
%load_ext autoreload
%autoreload 2          # src/ 파일을 고치면 커널 재시작 없이 바로 반영
import sys

sys.path.append("..")

import matplotlib.pyplot as plt
import pandas as pd

from src import calendar_kr, config, geo, loaders, metrics, routes, viz

viz.setup_plot()       # 한글 폰트, 마이너스 기호, seaborn 스타일
```

import 순서는 ruff의 정렬 규칙(I001)에 맞춘 것입니다. 순서가 다르면 CI `lint`가 실패하니 `ruff check --fix`로 고칩니다.

| 모듈 | 하는 일 | 주요 함수 |
|------|---------|-----------|
| `config` | 폴더 경로, 임시값(출퇴근 시간대·역 반경·분석 기간), 출처 문구 | `DATA_RAW`, `COMMUTE_HOURS`, `NEAR_STATION_M`, `SOURCES`, `provisional_note()` |
| `loaders` | 원본 읽기. 인코딩·컬럼명·값 표기를 통일한다 | `load_usage_monthly()`, `load_new_members()`, `load_stations()`, `load_stations_union()`, `load_subway_ridership()`, `load_subway_stations()` |
| | 대여이력·대여가능 수량 zip → 월별 parquet | `rent_history_to_parquet(2024)`, `load_rent_history(months=...)`, `availability_to_parquet()`, `load_availability()` |
| | 저장·캐시 | `save_parquet()`, `read_parquet()`, `cached(name, 함수)` |
| `calendar_kr` | 공휴일(2022~2026), 평일/주말·공휴일 구분, 출근/퇴근 시간대 | `add_time_columns(df, "대여일시")`, `day_kind()`, `count_days()`, `calendar_table()` |
| `routes` | ② 출퇴근 노선 판별 준비: 노선 × 시간대별 평일 출현일수 | `build_route_stats(months)`, `flag_repeated_routes(stats, min_weekdays=...)`, `mark_reverse_pairs()` |
| `metrics` | ② 교차 확인: 주말 기준선 통근 비중 | `hourly_daily_mean()`, `commute_share()`, `station_commute_index()` |
| `geo` | 거리, 가장 가까운 지하철역, 역 인근 구분 | `add_station_proximity(대여소, 역)`, `haversine_m()` |
| `viz` | 그래프·표 출처 표기, 숫자 축, 그림 저장 | `add_source(fig, "rent_history")`, `table_with_source()`, `comma_axis()`, `save_fig()` |

함수마다 무엇을 받고 무엇을 돌려주는지는 [`notebooks/00_src_guide.ipynb`](notebooks/00_src_guide.ipynb)에서 실제 데이터로 실행한 예시로 볼 수 있습니다.

원본마다 다른 표기를 이렇게 맞춥니다 (2026-11-25 받은 파일로 확인).

- 대여소번호는 모두 5자리 문자열(`"00102"`). 파일에 따라 `102`와 `00102`가 섞여 있다.
- 이용권은 원본 표기(`정기`, `정기권`, `일일(회원)`, `일일권` …)를 `이용권_대분류`(정기권·일일권·일일권(비회원)·단체권·가족권·기타)로 묶는다.
- 연령대 `10대`와 `~10대`는 `~10대`로, 성별 `m`/`f`는 대문자로, 빈칸과 `\N`은 결측으로 바꾼다.
- 확장자만 .csv인 엑셀 파일, 머리글 없는 파일, UTF-8과 cp949가 섞인 것도 알아서 읽는다.
- 원본에 있는 이상값(생년 0·2099, 센터·정비 대여소 코드 등)은 지우지 않는다. 각 함수 설명에 적어 두었으니 분석에서 기준을 정해 거른다.

## 분석 규칙

- 노트북은 처음부터 순서대로 실행하면 같은 결과가 나와야 합니다. PR 전에 **Restart & Run All** 실행으로 확인하고, 파일 경로는 상대경로로 씁니다.
- 수치는 추측하지 않고 코드로 계산한 값만 씁니다. 발표 자료의 숫자도 노트북 출력에서 가져옵니다.
- 모든 그래프와 표에 데이터 출처를 적습니다.
- 서울시 보도자료는 공공누리 4유형(변경금지)입니다. 출처를 밝히고 내용을 바꾸지 않고 인용만 합니다.

### 한글 폰트와 출처 표기

`viz.setup_plot()`이 Windows(맑은 고딕)·macOS·Linux에서 한글 폰트를 찾아 설정합니다. 출처는 `config.SOURCES`의 키로 적습니다.

```python
fig, ax = plt.subplots()
# ... 그래프 그리기 ...
viz.add_source(fig, "rent_history", "stations", note=config.provisional_note())  # 출처 + 임시값 안내
viz.save_fig(fig, "03_출퇴근노선_시간대")     # figures/03_출퇴근노선_시간대.png

viz.table_with_source(df, "usage_monthly", precision=1)   # 표 아래에 출처를 단다
```

### 대용량 데이터 읽기

대여이력은 한 번에 읽으면 메모리가 부족합니다. `loaders`가 zip을 풀지 않고 필요한 컬럼만 청크로 읽어 달마다 parquet로 저장합니다. 시험해 본 환경에서 2024년 12월분(csv 약 430MB)이 30초쯤 걸렸고, 1년이면 그 열 배 이상 걸립니다.

```python
loaders.rent_history_to_parquet(2024, months=["2024-05"])   # 처음엔 한 달로 시험
loaders.rent_history_to_parquet(2024)                       # 1년 전체 (이미 만든 달은 건너뜀)

rent = loaders.load_rent_history(months=["2024-05"])        # 필요한 달·컬럼만 읽기
rent = calendar_kr.add_time_columns(rent, "대여일시")        # 날짜·요일·시간대·일구분·시간구분

# ② 노선 × 시간대별 평일 출현일수 (한 달씩 읽어 합치므로 1년도 메모리에 부담이 적다)
stats = routes.build_route_stats([f"2024-{m:02d}" for m in range(1, 13)])
flag = routes.flag_repeated_routes(stats, min_weekdays=5)   # 반복 기준은 팀이 정할 값 (예시 5일)
stats["역방향반복"] = routes.mark_reverse_pairs(stats, flag)
```

## 작업 흐름

1. 아래 데이터 출처에서 필요한 데이터를 받아 `data/raw/<데이터셋 폴더>/`에 넣고 **받은 파일 기록** 표에 적기
2. `01_preprocessing`에서 필요한 컬럼만 읽어 정리·집계하고 `data/processed/`에 parquet로 저장
3. `02`~`05`에서 분석 단계별로 집계·시각화 (그래프마다 출처와 한계 표기)
4. `06_forecast`에서 예측 모델 학습과 2026년 상반기 검증
5. 반복해서 쓰는 코드와 설정값은 `src/`로 옮기기
6. 임시값을 쓴 결과는 임시값임을 표시하고, 값이 확정되면 다시 실행
7. 브랜치에서 커밋 → `conda run -n bigdata-final ruff check --fix .` → push → PR → 팀원 1명 승인 → Squash 머지 ([협업 규칙](CONTRIBUTING.md))

## git에 올라가지 않는 것

`.gitignore`에 정의되어 있습니다.

- `data/raw/` 안의 파일 (`.gitkeep`만 올라감)
- `data/interim/` (대여이력 월별 parquet 등, 원본에서 다시 만들 수 있음)
- `.ipynb_checkpoints/`, `__pycache__/`, `.mypy_cache/`
- `.vscode/`, `.idea/` 등 IDE 설정, `.env`(비밀키), `.claude/settings.local.json`

## 데이터 출처

공공기관이 직접 제공하는 원자료만 씁니다. 새 데이터를 추가하기 전에 이용허락범위나 공공누리 유형을 확인하고, 저장소에 올려도 되는지 이 표에 적습니다.

### 사용 데이터

이용허락의 "제한 없음"은 열린데이터광장의 "이용허락범위 제한 없음" 표기입니다 (2026-11-25 확인). 제한이 없어도 그래프·표·발표 자료에는 출처를 적습니다.

**필수**

| 데이터 | 제공 | 주요 항목 | 단계 | 이용허락 | 저장소 |
|--------|------|-----------|:----:|----------|--------|
| [공공자전거 따릉이 대여이력 정보](https://data.seoul.go.kr/dataList/OA-15182/F/1/datasetView.do) `OA-15182` | 서울특별시 | 건별 대여·반납 대여소와 일시 (노선 판정의 기준 자료) | ② ③ ⑤ | 제한 없음 | 집계본만 (용량) |
| [공공자전거 따릉이 이용정보(시간대별)](https://data.seoul.go.kr/dataList/OA-15245/F/1/datasetView.do) `OA-15245` | 서울특별시 | 대여일시·대여시간·대여소·정기권유무·성별·연령대 | ② ③ ④ ⑤ | 제한 없음 | 가공본 가능 |
| [공공자전거 따릉이 이용정보(월별)](https://data.seoul.go.kr/dataList/OA-15248/F/1/datasetView.do) `OA-15248` | 서울특별시 | 대여소·대여구분(정기·비정기)·성별·연령대·이용건수 | ① ④ | 제한 없음 | 가공본 가능 |
| [공공자전거 따릉이 대여소 정보](https://data.seoul.go.kr/dataList/OA-13252/F/1/datasetView.do) `OA-13252` | 서울특별시 | 대여소 이름·관리번호·위치·거치대수 (6월·12월 기준) | ② ③ | 제한 없음 | 가공본 가능 |

**보조**

| 데이터 | 제공 | 주요 항목 | 단계 | 이용허락 | 저장소 |
|--------|------|-----------|:----:|----------|--------|
| [공공자전거 따릉이 신규가입자 정보(일별)](https://data.seoul.go.kr/dataList/OA-15243/S/1/datasetView.do) `OA-15243` | 서울특별시 | 일별 신규가입자 (사용자구분·성별·연령대) | ① ④ | 공공누리 1유형 (출처표시) | 가공본 가능 |
| [종관기상관측(ASOS) 시간자료](https://data.kma.go.kr/data/grnd/selectAsosRltmList.do?pgmNo=36) 서울(108) | 기상청 기상자료개방포털 | 기온·강수량 등 | ⑤ | 받기 전 확인 | 확인 후 결정 |

**선택 (여유가 있을 때)**

| 데이터 | 제공 | 주요 항목 | 단계 | 이용허락 | 저장소 |
|--------|------|-----------|:----:|----------|--------|
| [서울시 역사마스터 정보](https://data.seoul.go.kr/bsp/wgs/dataView/data300View/10048.do) | 서울특별시 | 역 ID·역명·호선·좌표 | ③ | 다운로드 권한 요청 필요 | 결과값만 |
| [서울교통공사 역별 일별 시간대별 승하차인원](https://data.seoul.go.kr/dataList/OA-12921/F/1/datasetView.do) `OA-12921` | 서울교통공사 | 1~8호선 역별·시간대별 승차·하차 인원 | ③ | 제한 없음 | 가공본 가능 |
| [대여소별 공공자전거 따릉이 대여가능 수량](https://data.seoul.go.kr/dataList/OA-22382/F/1/datasetView.do) `OA-22382` | 서울특별시 | 대여소별 1시간 단위 대여가능 수량 (2022년 1분기~2025년 4분기) | ③ | 제한 없음 | 집계본만 (용량) |

### 받은 파일 기록

| 폴더 | 데이터셋 | 받은 범위 | 받은 날짜 | 받은 사람 |
|------|----------|-----------|-----------|-----------|
| `usage_monthly/` | OA-15248 | 2022년 1~6월 월별 CSV 6개 | | |
| `stations/` | OA-13252 | 24.6월, 24.12월, 25.6월, 25.12월 기준 xlsx 4개 | | |
| `new_members/` | OA-15243 | 2018.07.20~2022.06.30 xlsx 1개, 2022년 7월~2026년 6월 반기별 CSV 8개 | | |
| `subway_ridership/` | OA-12921 | 2024년 1~12월 CSV, 2025년(20251231 기준) CSV | | |
| `subway_stations/` | 역사마스터 | CSV 1개 (저장소에 올리지 않음) | | |
| `usage_hourly/` | OA-15245 | 아직 안 받음 | | |
| `rent_history/` | OA-15182 | 아직 안 받음 | | |
| `weather/` | ASOS | 아직 안 받음 | | |
