# 협업 규칙

2명 팀 기준의 최소 규칙입니다.

## 흐름

1. **이슈**: 할 일을 이슈로 만들고 담당자를 지정합니다 (템플릿: 작업 / 버그).
2. **브랜치**: `main`에서 새 브랜치를 만듭니다.
   ```powershell
   git switch main; git pull
   git switch -c feature/eda-sales
   ```
   | 접두어 | 용도 |
   |--------|------|
   | `feature/` | 분석·모델·기능 추가 |
   | `fix/` | 버그 수정 |
   | `docs/` | README 등 문서 |
3. **커밋**: 작게, 무엇을 했는지 한 줄로. 예: `전처리: 결측치 중앙값 대체`
4. **PR**: push 전에 `conda run -n bigdata ruff check --fix .`로 검사합니다 ([코드 검사](#코드-검사)). 첫 push는 `git push -u origin <브랜치>`, 그다음 GitHub에서 PR을 엽니다. 템플릿 체크리스트를 채웁니다.
5. **리뷰**: 팀원 1명이 확인하고 Approve합니다. 승인과 필수 체크가 모두 통과해야 머지 버튼이 열립니다.
6. **머지**: **Squash and merge**만 사용합니다. GitHub의 브랜치는 자동 삭제되고, 내 PC의 브랜치는 직접 지웁니다.
   ```powershell
   git switch main; git pull
   git branch -D feature/eda-sales   # squash 머지라 -d로는 안 지워진다
   ```

## main 보호

저장소가 공개라서 GitHub 규칙(ruleset `protect-main`)이 실제로 적용됩니다.

- `main`에 직접 push, 강제 push, 삭제가 막힙니다. 모든 변경은 PR로 들어갑니다.
- PR 머지 조건: 승인 1명 + 필수 체크 `lint`, `SonarCloud Code Analysis` 통과.
- 조직 소유자는 PR 화면에서 이 조건을 건너뛰고 머지할 수 있습니다. 팀원이 리뷰할 수 없는 급한 경우에만 씁니다. 직접 push는 소유자도 막힙니다.

## 노트북 규칙

- **한 노트북은 한 사람이 담당**합니다. `.ipynb`는 동시에 고치면 충돌을 풀기 어렵습니다.
- 다른 사람 노트북을 고쳐야 하면 담당자에게 먼저 말하거나, 복사본(`03_modeling_kim.ipynb`)에서 작업합니다.
- PR 전에 **Restart & Run All**로 처음부터 끝까지 돌아가는지 확인합니다.
- 두 노트북 이상에서 쓰는 코드는 `src/`로 옮깁니다.

## 코드 검사

PR과 `main` push마다 GitHub Actions가 검사합니다.

| 체크 | 검사 내용 | 머지에 필수 |
|------|-----------|:-----------:|
| `lint` | ruff: `.py`·`.ipynb`의 미사용 import, 정의 안 된 변수, 문법 오류 | ✅ |
| `SonarCloud Code Analysis` | 버그·취약점·중복 코드. 결과는 PR 코멘트와 [SonarCloud 대시보드](https://sonarcloud.io/project/overview?id=bigdata-final-team_bigdata-final) | ✅ |
| `sonar` | 위 분석을 SonarCloud로 보내는 잡 | |

`lint`는 push 전에 내 PC에서 같은 버전의 ruff로 미리 돌려 볼 수 있습니다.

```powershell
conda run -n bigdata ruff check --fix .
```

`--fix`로 고쳐지지 않은 문제는 출력에 나온 파일과 줄을 보고 직접 고칩니다. CI에서 실패했다면 Actions 탭 로그에 같은 메시지가 있습니다. 고친 뒤 다시 push하면 체크가 다시 돕니다.

ruff 버전은 `requirements.txt`에 고정되어 있고 CI도 이 버전을 읽어 씁니다. 버전을 올릴 때는 PR에 적어 주세요.

## 권한

| 대상 | 권한 | 비고 |
|------|------|------|
| 조직 소유자 | admin | 조직·저장소 설정, 팀원 초대, 급할 때 머지 조건 건너뛰기 |
| `dev` 팀 | `bigdata-final` write | 팀원은 이 팀에 넣어 초대합니다 |
| 그 밖의 조직 멤버 | read | 조직 기본 권한 |

- 새 팀원 초대: 조직 **People → Invite member**에서 `dev` 팀을 선택합니다.
- GitHub Actions는 조직 정책으로 GitHub 공식 액션과 `astral-sh/ruff-action`, `SonarSource/sonarqube-scan-action`만 실행됩니다 (모든 저장소에 적용). 새 액션이 필요하면 소유자가 **조직 Settings → Actions → General**의 허용 목록에 추가하고, 워크플로에는 태그 대신 커밋 SHA로 적습니다.
- 워크플로의 `GITHUB_TOKEN`은 읽기 전용입니다.

## 공개 저장소 주의

누구나 코드, 커밋 기록, `data/processed/`를 볼 수 있습니다.

- 재배포가 금지된 데이터(대회 데이터, 이용 약관이 있는 자료 등)는 `data/processed/`에도 올리지 않습니다. 출처만 README **데이터 출처**에 적습니다.
- 커밋에 개인 이메일이 남지 않도록 GitHub noreply 주소를 씁니다. 주소는 GitHub **Settings → Emails**에 나옵니다.
  ```powershell
  git config --global user.email "<번호>+<아이디>@users.noreply.github.com"
  ```
