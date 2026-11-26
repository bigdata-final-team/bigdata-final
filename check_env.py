"""환경 점검: Python 버전, requirements.txt 고정 버전과 설치 버전 비교, BLAS·그림 저장, 모델 학습 테스트.

실행: conda run -n bigdata-final python check_env.py
문제가 하나라도 있으면 마지막에 모아서 보여 주고 종료 코드 1로 끝난다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

EXPECTED_PYTHON = (3, 12)
REQUIREMENTS = Path(__file__).with_name("requirements.txt")

# 별도 프로세스에서 돌리는 점검. BLAS·OpenMP DLL이 어긋나면 예외가 아니라 프로세스 크래시
# (Windows 0xC06D007F 등)로 나타나서, 같은 프로세스에서 돌리면 결과 요약도 못 남기고 죽는다.
# matplotlib은 그림을 그릴 때마다 np.dot을 부르므로 BLAS가 깨지면 Jupyter 커널이 그래프 셀에서 죽는다.
# Jupyter 커널처럼 env를 활성화하지 않은 상태로 돌린다 (kernel_like_env 참고).
NATIVE_CHECKS = {
    "BLAS 행렬 곱": """
import numpy as np
a = np.arange(1.0, 10.0).reshape(3, 3) + np.eye(3)
assert np.allclose(np.dot(a, np.eye(3)), a)
assert np.allclose(a @ np.linalg.solve(a, np.ones(3)), np.ones(3))
try:
    from threadpoolctl import threadpool_info
    libs = [f"{i['internal_api']} {i['version']}" for i in threadpool_info() if i["user_api"] == "blas"]
except ImportError:
    libs = []
print(f"BLAS 행렬 곱 ({', '.join(libs) or 'BLAS 종류 확인 불가'})  OK")
""",
    "matplotlib 그림 저장": """
import io
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([0, 1, 2], [0, 1, 4])
buf = io.BytesIO()
fig.savefig(buf, format="png")
assert buf.getvalue().startswith(b"\\x89PNG")
print("matplotlib 그림 저장 (Agg, png)  OK")
""",
}

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


def installed_version(name: str) -> tuple[str, str]:
    """(설치 버전, 설치 도구). 설치되지 않았으면 ("(없음)", "-").

    conda-forge의 ruff처럼 파이썬 패키지 정보 없이 실행 파일만 설치하는 패키지는
    env 안의 `<이름> --version` 출력에서 버전을 읽는다.
    """
    try:
        return metadata.version(name), installer_of(name)
    except metadata.PackageNotFoundError:
        pass
    env_bins = [Path(sys.prefix) / d for d in ("Scripts", "Library/bin", "bin")]
    exe = shutil.which(name, path=os.pathsep.join(map(str, env_bins)))
    if exe is None:
        return "(없음)", "-"
    result = subprocess.run(
        [exe, "--version"], capture_output=True, text=True, timeout=30, check=False
    )
    words = result.stdout.split()
    return (words[-1] if words else "?"), "exe"


def check_python() -> None:
    section("Python")
    current = sys.version_info[:3]
    print(f"버전   {'.'.join(map(str, current))}")
    print(f"실행   {sys.executable}")
    if current[:2] != EXPECTED_PYTHON:
        want = ".".join(map(str, EXPECTED_PYTHON))
        problems.append(
            f"Python {want}.x 필요, 현재 {'.'.join(map(str, current))} (conda env 'bigdata-final'로 실행했는지 확인)"
        )

    # python.exe를 직접 실행하면 env가 활성화되지 않아 CmdStan(Prophet)·DLL 경로가 잡히지 않는다.
    conda_prefix = os.environ.get("CONDA_PREFIX")
    print(f"활성 env {conda_prefix or '(없음)'}")
    if not conda_prefix or Path(conda_prefix).resolve() != Path(sys.prefix).resolve():
        problems.append(
            "conda env가 활성화되지 않음: 'conda run -n bigdata-final python check_env.py'로 실행"
        )


def check_versions() -> None:
    section(f"패키지 버전 ({REQUIREMENTS.name} 기준)")
    pins = read_pins(REQUIREMENTS)
    width = max((len(name) for name, _ in pins), default=10)
    print(f"{'패키지':<{width}}  {'고정':<22}{'설치':<22}{'설치 도구':<10}결과")
    for name, wanted in pins:
        installed, tool = installed_version(name)
        if installed == wanted:
            status = "OK"
        elif installed == "(없음)":
            status = "없음"
            problems.append(f"{name}: 설치되지 않음 (필요 {wanted})")
        else:
            status = "불일치"
            problems.append(f"{name}: 설치 {installed}, 필요 {wanted}")
        print(f"{name:<{width}}  {wanted:<22}{installed:<22}{tool:<10}{status}")


def kernel_like_env() -> dict[str, str]:
    """Jupyter 커널이 뜰 때처럼 env 활성화가 PATH에 넣은 경로(env 안 폴더)를 뺀 환경 변수.

    kernelspec(kernel.json)은 env의 python.exe를 활성화 없이 바로 실행한다. 그래서
    `conda run`으로는 통과하고 노트북에서만 죽는 DLL 문제가 있다 (MKL + llvm-openmp가 그랬다).
    """
    prefix = os.path.normcase(os.path.abspath(sys.prefix))

    def in_env(entry: str) -> bool:
        try:
            full = os.path.normcase(os.path.abspath(entry))
            return os.path.commonpath([prefix, full]) == prefix
        except ValueError:  # Windows에서 드라이브가 다르면 commonpath가 실패한다
            return False

    entries = os.environ.get("PATH", "").split(os.pathsep)
    path = os.pathsep.join(e for e in entries if e and not in_env(e))
    return {**os.environ, "PATH": path, "PYTHONIOENCODING": "utf-8"}


def run_isolated(label: str, code: str) -> bool:
    """code를 새 파이썬 프로세스에서 실행한다. 예외든 크래시든 0이 아닌 종료 코드면 실패로 기록."""
    try:
        result = subprocess.run(
            [sys.executable, "-X", "faulthandler", "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=kernel_like_env(),
            timeout=300,
            check=False,
        )
    except subprocess.TimeoutExpired:
        problems.append(f"{label}: 300초 안에 끝나지 않음")
        print(f"{label}  실패 (시간 초과)")
        return False
    if result.returncode == 0:
        print(result.stdout.strip())
        return True

    rc = result.returncode
    code_text = f"시그널 {-rc}" if rc < 0 else f"0x{rc & 0xFFFFFFFF:08X}"
    lines = [line for line in result.stderr.splitlines() if line.strip()]
    # 크래시면 faulthandler의 "Windows fatal exception: ..." 줄, 예외면 마지막 줄이 원인이다
    reason = next(
        (line for line in lines if "fatal" in line.lower()),
        lines[-1] if lines else "오류 출력 없음",
    )
    problems.append(
        f"{label}: 프로세스가 종료 코드 {code_text}로 끝남 ({reason.strip()})"
    )
    print(f"{label}  실패 (종료 코드 {code_text})")
    return False


def check_native() -> bool:
    section("BLAS·그림 저장 (별도 프로세스, Jupyter 커널처럼 env 활성화 없이)")
    results = [run_isolated(label, code) for label, code in NATIVE_CHECKS.items()]
    return all(results)


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
    native_ok = check_native()
    if native_ok:
        try:
            check_training()
        except Exception as exc:  # noqa: BLE001 - 라이브러리가 깨졌을 때 원인을 요약에 남긴다
            problems.append(f"동작 테스트 실패: {type(exc).__name__}: {exc}")
    else:
        # Prophet·scikit-learn도 BLAS를 쓰므로 여기서 돌리면 이 프로세스가 요약 전에 죽을 수 있다
        section("동작 테스트")
        print("BLAS·그림 저장 점검이 실패해 건너뜀")

    section("결과")
    if not problems:
        print("모든 점검 통과")
        return 0
    print(f"문제 {len(problems)}개:")
    for p in problems:
        print(f"  - {p}")
    print("\n고치는 법: conda env update -n bigdata-final -f environment.yml --prune")
    if not native_ok:
        print(
            "BLAS 점검이 실패하면 위 명령 뒤 'conda list -n bigdata-final libblas'의 빌드가"
            " *_openblas인지 확인 (README '환경')"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
