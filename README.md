<div align="center">

# 📊 bigdata-final

**Python 빅데이터 분석 · 기계학습 프로젝트**

[![CI](https://github.com/bigdata-final-team/bigdata-final/actions/workflows/ci.yml/badge.svg)](https://github.com/bigdata-final-team/bigdata-final/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=white)
![Prophet](https://img.shields.io/badge/Prophet-time%20series-0467DF)

[환경](#환경) · [폴더 구조](#폴더-구조) · [작업 흐름](#작업-흐름) · [협업 규칙](CONTRIBUTING.md) · [데이터 출처](#데이터-출처)

</div>

## 팀

| 이름 | GitHub | 담당 |
|------|--------|------|
| 전시원 | [@WoogaJJangka](https://github.com/WoogaJJangka) | 팀장|
| | | |
| | | |

## 환경

conda 환경 `bigdata` (Python 3.12)를 사용합니다. conda는 PowerShell에서만 동작합니다.

```powershell
# 처음 한 번만
conda create -n bigdata -c conda-forge --override-channels python=3.12 pip
conda run -n bigdata python -m pip install -r requirements.txt
conda run -n bigdata python -m ipykernel install --user --name bigdata --display-name bigdata

# 설치 확인 (라이브러리 버전 출력 + 랜덤포레스트·Prophet 학습 테스트)
conda run -n bigdata python check_env.py
```

| 용도 | 라이브러리 |
|------|-----------|
| 데이터 처리 | numpy, pandas, polars, pyarrow |
| 통계 | scipy, statsmodels |
| 기계학습 | scikit-learn, xgboost, lightgbm |
| 시계열 예측 | prophet |
| 시각화 | matplotlib, seaborn, plotly |
| 노트북·엑셀 | jupyterlab, ipykernel, openpyxl |
| 타입 검사 | mypy, pandas-stubs, types-seaborn |

`requirements.txt`는 모든 버전을 `==`로 고정합니다. 라이브러리를 추가할 때는 `conda run -n bigdata python -m pip install <패키지>==<버전>`으로 설치하고 `requirements.txt`에 같은 버전으로 한 줄 추가합니다. `check_env.py`가 고정 버전과 설치 버전을 비교해 다르면 알려 줍니다. `python.exe`를 직접 실행하면 env가 활성화되지 않아 Prophet이 실패하므로 꼭 `conda run`으로 실행합니다.

타입 검사는 `conda run -n bigdata mypy`로 돌립니다(설정: `pyproject.toml`). PR마다 CI에서도 같은 검사를 합니다.

한글이 깨지면 `$env:PYTHONIOENCODING='utf-8'`을 먼저 실행합니다.

## 폴더 구조

```
bigdata-final/
├─ data/
│  ├─ raw/         원본 데이터. 받은 그대로 두고 수정하지 않는다 (git 제외)
│  └─ processed/   전처리를 마친 데이터 (git 포함)
├─ notebooks/      탐색·시각화·실험용 Jupyter 노트북
├─ src/            여러 노트북에서 같이 쓰는 함수 (.py)
├─ check_env.py    환경 설치 확인 스크립트
└─ requirements.txt
```

### data/raw/ — 원본 데이터

- 다운로드하거나 받은 파일(csv, xlsx, json 등)을 **그대로** 넣습니다.
- 원본은 절대 덮어쓰지 않습니다. 정리한 결과는 항상 `data/processed/`에 새 파일로 저장합니다. 그래야 실수해도 원본에서 다시 시작할 수 있습니다.
- 용량이 커서 git에 올리지 않습니다. 대신 어디서 받았는지(URL, 날짜)를 이 README 아래 **데이터 출처**에 적어 두면 다른 컴퓨터에서도 같은 데이터를 다시 받을 수 있습니다.

### data/processed/ — 가공 데이터

- 결측치 처리, 형 변환, 병합 등을 마친 분석용 데이터입니다.
- 큰 데이터는 csv 대신 **parquet**으로 저장하는 것을 권장합니다. 더 작고 빠르며 자료형이 유지됩니다. parquet 파일은 Git LFS로 관리됩니다.

```python
df.to_parquet("../data/processed/sales_clean.parquet")
df = pd.read_parquet("../data/processed/sales_clean.parquet")
```

### notebooks/ — 분석 노트북

- 작업 순서가 보이도록 번호를 붙입니다.

```
notebooks/
├─ 01_eda.ipynb             데이터 둘러보기 (분포, 결측치, 상관관계)
├─ 02_preprocessing.ipynb   raw → processed 변환
├─ 03_modeling.ipynb        모델 학습·비교 (sklearn, xgboost, lightgbm)
└─ 04_forecast.ipynb        시계열 예측 (prophet)
```

- 노트북을 열 때 커널은 **bigdata**를 선택합니다 (VS Code 오른쪽 위 커널 선택, 또는 `jupyter lab`).
- 노트북 안에서 경로는 `notebooks/` 기준이므로 데이터는 `../data/...`로 접근합니다.
- 같은 코드를 두 번 이상 복사하게 되면 `src/`로 옮길 때입니다.

### src/ — 공용 코드

여러 노트북에서 쓰는 함수를 `.py` 파일로 모아 둡니다. 예:

```python
# src/preprocess.py
import pandas as pd

def load_raw(name: str) -> pd.DataFrame:
    return pd.read_csv(f"../data/raw/{name}")
```

노트북에서 불러오기:

```python
import sys; sys.path.append("..")
%load_ext autoreload
%autoreload 2          # src/ 파일을 고치면 커널 재시작 없이 바로 반영

from src.preprocess import load_raw
df = load_raw("sales.csv")
```

## 작업 흐름

1. 원본 파일을 `data/raw/`에 넣고 아래 **데이터 출처**에 기록
2. `notebooks/01_eda.ipynb`에서 데이터 탐색
3. `02_preprocessing`에서 정리한 결과를 `data/processed/`에 저장
4. `03_modeling`, `04_forecast`에서 processed 데이터로 모델 학습·평가
5. 반복해서 쓰는 코드는 `src/`로 옮기기
6. 브랜치에서 커밋·push한 뒤 PR → 팀원 1명 리뷰 → Squash 머지 ([협업 규칙](CONTRIBUTING.md))

## git에 올라가지 않는 것

`.gitignore`에 정의되어 있습니다.

- `data/raw/` 안의 파일 (`.gitkeep`만 올라감)
- `.ipynb_checkpoints/`, `__pycache__/`
- `.vscode/` 등 IDE 설정, `.env`(비밀키)

## 데이터 출처

| 파일 | 출처 | 받은 날짜 |
|------|------|-----------|
| | | |
