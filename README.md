# bigdata-final

Python 빅데이터 분석 · 기계학습 프로젝트.

## 환경

```powershell
conda create -n bigdata -c conda-forge --override-channels python=3.12 pip
conda run -n bigdata python -m pip install -r requirements.txt
conda run -n bigdata python check_env.py   # 설치 확인
```

Jupyter: `conda activate bigdata; jupyter lab` (커널: `bigdata`)

## 구조

```
data/raw/        원본 데이터 (git 제외)
data/processed/  가공 데이터
notebooks/       분석 노트북
src/             재사용 코드
```
