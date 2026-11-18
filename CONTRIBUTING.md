# 협업 규칙

3명 이하 소규모 팀 기준의 최소 규칙입니다.

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
4. **PR**: 첫 push는 `git push -u origin <브랜치>`, 그다음 GitHub에서 PR을 엽니다. 템플릿 체크리스트를 채웁니다.
5. **리뷰**: 팀원 1명이 확인하고 Approve합니다. CI(ruff)가 통과해야 합니다.
6. **머지**: **Squash and merge**만 사용합니다. 머지된 브랜치는 자동 삭제됩니다.

`main`에 직접 push하지 않습니다. 무료 플랜의 비공개 저장소라 GitHub이 막아 주지 않으므로 서로 지키는 규칙입니다.

## 노트북 규칙

- **한 노트북은 한 사람이 담당**합니다. `.ipynb`는 동시에 고치면 충돌을 풀기 어렵습니다.
- 다른 사람 노트북을 고쳐야 하면 담당자에게 먼저 말하거나, 복사본(`03_modeling_kim.ipynb`)에서 작업합니다.
- PR 전에 **Restart & Run All**로 처음부터 끝까지 돌아가는지 확인합니다.
- 두 노트북 이상에서 쓰는 코드는 `src/`로 옮깁니다.

## 코드 검사

PR과 `main` push마다 GitHub Actions가 두 가지를 검사합니다.

- **ruff**: `.py`·`.ipynb`의 미사용 import, 정의 안 된 변수, 문법 오류
- **SonarQube Cloud**: 버그·취약점·중복 코드. 결과는 PR 코멘트와 [SonarCloud 대시보드](https://sonarcloud.io/project/overview?id=bigdata-final-team_bigdata-final)에서 봅니다. Quality Gate가 실패하면 PR에 빨간 표시가 뜹니다.

실패하면 Actions 탭에서 어느 줄인지 확인하고 고쳐서 다시 push합니다.

## 권한

| 대상 | 권한 | 비고 |
|------|------|------|
| 조직 소유자 | admin | 조직·저장소 설정, 팀원 초대 |
| `dev` 팀 | `bigdata-final` write | 팀원은 이 팀에 넣어 초대합니다 |
| 그 밖의 조직 멤버 | read | 조직 기본 권한 |

- 새 팀원 초대: 조직 **People → Invite member**에서 `dev` 팀을 선택합니다.
- GitHub Actions는 조직 정책으로 GitHub 공식 액션과 `astral-sh/ruff-action`, `SonarSource/sonarqube-scan-action`만 실행됩니다 (모든 저장소에 적용). 새 액션이 필요하면 소유자가 **조직 Settings → Actions → General**의 허용 목록에 추가하고, 워크플로에는 태그 대신 커밋 SHA로 적습니다.
- 워크플로의 `GITHUB_TOKEN`은 읽기 전용입니다.
