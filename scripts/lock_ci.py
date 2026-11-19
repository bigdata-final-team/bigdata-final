"""CI(mypy 잡)용 해시 고정 lock 파일 requirements-ci.txt를 만든다.

requirements.txt를 바꿨으면 다시 실행해서 결과를 같이 커밋한다.
실행: conda run -n bigdata python scripts/lock_ci.py

SonarCloud 규칙 때문에 CI는 `pip install --only-binary :all: --require-hashes`로 설치한다.
그래서 간접 의존성까지 전부 버전과 해시가 적힌 파일이 필요하다. Windows에서도 CI(Linux, Python 3.12)
기준으로 해석하도록 pip의 --platform 옵션을 쓴다. 다만 pip는 환경 마커(`platform_system == "Linux"` 등)를
실행 중인 OS 기준으로 평가하므로, 결과의 의존성 마커를 Linux 기준으로 다시 평가해 빠진 패키지는 추가하고
Windows에서만 필요한 패키지는 뺀다. 노트북용 패키지는 Windows 전용 의존성(pywinpty)을 끌어와 해석이 깨지고
mypy에도 필요 없어서 뺀다.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

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
# GitHub Actions ubuntu-latest + setup-python 3.12
LINUX_ENV = {
    **default_environment(),
    "os_name": "posix",
    "sys_platform": "linux",
    "platform_system": "Linux",
    "platform_machine": "x86_64",
    "platform_release": "",
    "platform_version": "",
    "implementation_name": "cpython",
    "platform_python_implementation": "CPython",
    "python_version": "3.12",
}
MAX_ROUNDS = 10


def ci_requirements() -> list[str]:
    lines = []
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line and canonicalize_name(line.partition("==")[0]) not in EXCLUDE:
            lines.append(line)
    return lines


def resolve(requirements: list[str], workdir: Path) -> dict[str, dict[str, Any]]:
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
    installed = json.loads(report.read_text(encoding="utf-8"))["install"]
    return {canonicalize_name(p["metadata"]["name"]): p for p in installed}


def linux_closure(
    roots: list[Requirement], packages: dict[str, dict[str, Any]]
) -> tuple[set[str], set[str]]:
    """Linux에서 실제로 필요한 패키지 집합과, 해석 결과에 없는 요구사항(마커 뺀 문자열) 집합."""
    needed: set[str] = set()
    missing: set[str] = set()
    seen: set[tuple[str, frozenset[str]]] = set()
    stack = list(roots)
    while stack:
        req = stack.pop()
        name, extras = canonicalize_name(req.name), frozenset(req.extras)
        if name not in packages:
            req.marker = None
            missing.add(str(req))
        if (name, extras) in seen or name not in packages:
            continue
        seen.add((name, extras))
        needed.add(name)
        for spec in packages[name]["metadata"].get("requires_dist", []):
            dep = Requirement(spec)
            envs = [{**LINUX_ENV, "extra": e} for e in sorted(extras) or [""]]
            if dep.marker is None or any(dep.marker.evaluate(env) for env in envs):
                stack.append(dep)
    return needed, missing


def main() -> int:
    requirements = ci_requirements()
    roots = [Requirement(r) for r in requirements]
    extra: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for _ in range(MAX_ROUNDS):
            packages = resolve(requirements + extra, Path(tmp))
            needed, missing = linux_closure(roots, packages)
            if not missing:
                break
            extra += sorted(missing)  # 부모가 건 버전 제약을 그대로 넘긴다
        else:
            print(f"{MAX_ROUNDS}번 반복해도 의존성이 수렴하지 않음", file=sys.stderr)
            return 1

    out = [
        "# 자동 생성 파일: 직접 고치지 말고 `conda run -n bigdata python scripts/lock_ci.py`로 다시 만든다.",
        "# CI(Linux, Python 3.12) mypy 잡 전용. 원본은 requirements.txt (노트북 패키지 제외).",
    ]
    for name in sorted(needed):
        meta = packages[name]["metadata"]
        sha256 = packages[name]["download_info"]["archive_info"]["hashes"]["sha256"]
        out.append(f"{meta['name']}=={meta['version']} \\\n    --hash=sha256:{sha256}")
    TARGET.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    dropped = sorted(set(packages) - needed)
    print(
        f"{TARGET.name}: 패키지 {len(needed)}개 (Linux에서 불필요해 뺌: {dropped or '없음'})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
