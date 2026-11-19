"""CI(mypy 잡)용 해시 고정 lock 파일 requirements-ci.txt를 만든다.

requirements.txt를 바꿨으면 다시 실행해서 결과를 같이 커밋한다.
실행: conda run -n bigdata python scripts/lock_ci.py

SonarCloud 규칙 때문에 CI는 `pip install --only-binary :all: --require-hashes`로 설치한다.
그래서 간접 의존성까지 전부 버전과 해시가 적힌 파일이 필요하다. Windows에서도 CI(Linux, Python 3.12)
기준으로 해석하도록 pip의 --platform 옵션을 쓴다. 노트북용 패키지는 Windows 전용 의존성(pywinpty)을
끌어와 Linux 기준 해석이 깨지고 mypy에도 필요 없어서 뺀다.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "requirements.txt"
TARGET = ROOT / "requirements-ci.txt"
EXCLUDE = {"jupyterlab", "ipykernel"}
PLATFORMS = [
    "manylinux_2_28_x86_64",
    "manylinux_2_27_x86_64",
    "manylinux_2_24_x86_64",
    "manylinux_2_17_x86_64",
    "manylinux2014_x86_64",
    "manylinux_2_5_x86_64",
    "manylinux1_x86_64",
    "linux_x86_64",
]


def ci_requirements() -> list[str]:
    lines = []
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and line.partition("==")[0].strip().lower() not in EXCLUDE:
            lines.append(line)
    return lines


def resolve(requirements: list[str], workdir: Path) -> list[dict]:
    req_file = workdir / "requirements.in"
    report = workdir / "report.json"
    req_file.write_text("\n".join(requirements) + "\n", encoding="utf-8")
    cmd = [
        sys.executable, "-m", "pip", "install",
        "--dry-run", "--ignore-installed", "--quiet",
        "--only-binary", ":all:",
        "--python-version", "3.12", "--implementation", "cp", "--abi", "cp312",
        *(arg for p in PLATFORMS for arg in ("--platform", p)),
        "--report", str(report),
        "-r", str(req_file),
    ]  # fmt: skip
    subprocess.run(cmd, check=True)
    return json.loads(report.read_text(encoding="utf-8"))["install"]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        packages = resolve(ci_requirements(), Path(tmp))

    out = [
        "# 자동 생성 파일: 직접 고치지 말고 `conda run -n bigdata python scripts/lock_ci.py`로 다시 만든다.",
        "# CI(Linux, Python 3.12) mypy 잡 전용. 원본은 requirements.txt (노트북 패키지 제외).",
    ]
    for pkg in sorted(packages, key=lambda p: p["metadata"]["name"].lower()):
        name, version = pkg["metadata"]["name"], pkg["metadata"]["version"]
        sha256 = pkg["download_info"]["archive_info"]["hashes"]["sha256"]
        out.append(f"{name}=={version} \\\n    --hash=sha256:{sha256}")
    TARGET.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print(f"{TARGET.name}: 패키지 {len(packages)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
