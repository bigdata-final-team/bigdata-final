"""환경 점검: Python 버전, requirements.txt 고정 버전과 설치 버전 비교, 모델 학습 테스트.

실행: conda run -n bigdata python check_env.py
문제가 하나라도 있으면 마지막에 모아서 보여 주고 종료 코드 1로 끝난다.
"""

from __future__ import annotations

import os
import sys
from importlib import metadata
from pathlib import Path

EXPECTED_PYTHON = (3, 12)
REQUIREMENTS = Path(__file__).with_name("requirements.txt")

problems: list[str] = []


def section(title: str) -> None:
    print(f"\n== {title}")


def read_pins(path: Path) -> list[tuple[str, str]]:
    """requirements.txt에서 (패키지, 고정 버전) 목록을 읽는다. 주석과 빈 줄은 건너뛴다."""
    pins: list[tuple[str, str]] = []
    for lineno, raw in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        name, sep, wanted = line.partition("==")
        if not sep:
            problems.append(
                f"requirements.txt {lineno}행 '{line}': 버전이 고정되지 않음 (==버전 필요)"
            )
            continue
        pins.append((name.strip(), wanted.strip()))
    return pins


def installer_of(name: str) -> str:
    """conda로 설치했는지 pip로 설치했는지 (dist-info의 INSTALLER 파일)."""
    try:
        text = metadata.distribution(name).read_text("INSTALLER")
    except metadata.PackageNotFoundError:
        return "-"
    return (text or "?").strip()


def check_python() -> None:
    section("Python")
    current = sys.version_info[:3]
    print(f"버전   {'.'.join(map(str, current))}")
    print(f"실행   {sys.executable}")
    if current[:2] != EXPECTED_PYTHON:
        want = ".".join(map(str, EXPECTED_PYTHON))
        problems.append(
            f"Python {want}.x 필요, 현재 {'.'.join(map(str, current))} (conda env 'bigdata'로 실행했는지 확인)"
        )

    # python.exe를 직접 실행하면 env가 활성화되지 않아 CmdStan(Prophet)·DLL 경로가 잡히지 않는다.
    conda_prefix = os.environ.get("CONDA_PREFIX")
    print(f"활성 env {conda_prefix or '(없음)'}")
    if not conda_prefix or Path(conda_prefix).resolve() != Path(sys.prefix).resolve():
        problems.append(
            "conda env가 활성화되지 않음: 'conda run -n bigdata python check_env.py'로 실행"
        )


def check_versions() -> None:
    section(f"패키지 버전 ({REQUIREMENTS.name} 기준)")
    pins = read_pins(REQUIREMENTS)
    width = max((len(name) for name, _ in pins), default=10)
    print(f"{'패키지':<{width}}  {'고정':<22}{'설치':<22}{'설치 도구':<10}결과")
    for name, wanted in pins:
        try:
            installed = metadata.version(name)
        except metadata.PackageNotFoundError:
            installed = "(없음)"
        if installed == wanted:
            status = "OK"
        elif installed == "(없음)":
            status = "없음"
            problems.append(f"{name}: 설치되지 않음 (필요 {wanted})")
        else:
            status = "불일치"
            problems.append(f"{name}: 설치 {installed}, 필요 {wanted}")
        print(
            f"{name:<{width}}  {wanted:<22}{installed:<22}{installer_of(name):<10}{status}"
        )


def check_training() -> None:
    section("동작 테스트")
    import numpy as np
    import pandas as pd
    from prophet import Prophet
    from sklearn.datasets import load_iris
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split

    x_tr, x_te, y_tr, y_te = train_test_split(
        *load_iris(return_X_y=True), random_state=0
    )
    acc = RandomForestClassifier(random_state=0).fit(x_tr, y_tr).score(x_te, y_te)
    if acc > 0.9:
        print(f"iris 랜덤포레스트 정확도 {acc:.3f}  OK")
    else:
        problems.append(f"iris 랜덤포레스트 정확도가 낮음: {acc:.3f}")

    # Prophet 학습은 같이 설치되는 CmdStan을 쓰는데, Windows에서 가장 자주 깨지는 부분이다.
    df = pd.DataFrame(
        {"ds": pd.date_range("2024-01-01", periods=200), "y": np.arange(200) * 0.01}
    )
    future = pd.DataFrame({"ds": pd.date_range("2024-07-19", periods=30)})
    forecast = Prophet().fit(df).predict(future)
    if len(forecast) == 30:
        print("Prophet 30일 예측  OK")
    else:
        problems.append(f"Prophet 예측 길이가 30이 아님: {len(forecast)}")


def main() -> int:
    check_python()
    check_versions()
    try:
        check_training()
    except Exception as exc:  # 라이브러리가 깨졌을 때 원인을 요약에 남긴다
        problems.append(f"동작 테스트 실패: {type(exc).__name__}: {exc}")

    section("결과")
    if not problems:
        print("모든 점검 통과")
        return 0
    print(f"문제 {len(problems)}개:")
    for p in problems:
        print(f"  - {p}")
    print("\n고치는 법: conda run -n bigdata python -m pip install -r requirements.txt")
    return 1


if __name__ == "__main__":
    sys.exit(main())
