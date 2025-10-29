# PRISM-INSIGHT: Web UI 분리 개발 방안

## 1. 개요

본 문서는 PRISM-INSIGHT 프로젝트의 Web UI를 별도의 레포지토리로 분리하여 개발하는 방안을 제안합니다. 이 접근 방식은 현재 백엔드 레포지토리는 그대로 유지하면서, 프론트엔드 개발의 독립성과 유연성을 확보하는 것을 목표로 합니다.

## 2. Web UI 분리 개발의 장점

*   **독립적인 개발 및 배포:** 프론트엔드와 백엔드 팀은 서로의 개발 및 배포 일정에 영향을 받지 않고 독립적으로 작업할 수 있습니다.
*   **기술 스택 유연성:** 각 팀은 자신의 요구사항에 가장 적합한 기술 스택을 자유롭게 선택하고 발전시킬 수 있습니다. (e.g., 프론트엔드: React, Vue.js, 백엔드: Python, Node.js)
*   **명확한 관심사 분리:** 프론트엔드와 백엔드 코드베이스를 물리적으로 분리함으로써, 시스템 전체의 구조를 더 쉽게 이해하고 유지보수할 수 있습니다.
*   **팀 전문성 강화:** 각 팀은 자신의 전문 분야에 집중하여 더 높은 품질의 결과물을 만들어낼 수 있습니다.

## 3. 개발 전제 조건

Web UI 개발을 시작하기 전에 다음 조건들이 충족되어야 합니다.

*   **Node.js 및 npm/yarn 설치:** React 프로젝트 생성 및 의존성 관리를 위해 Node.js와 npm 또는 yarn이 설치되어 있어야 합니다.
*   **React 프로젝트 생성:** `create-react-app` 또는 `Vite`를 사용하여 `prism-insight-web` 디렉토리 내에 React 프로젝트가 생성되어 있어야 합니다.
*   **백엔드 API 서버 실행:** `prism-insight` 백엔드 API 서버가 실행 중이고, Web UI 개발 환경에서 접근 가능해야 합니다.
*   **API 명세 확정:** 프론트엔드와 백엔드 간의 API 계약(엔드포인트, 요청/응답 형식 등)이 명확하게 정의되고 공유되어야 합니다.

## 4. 개발 방안

### 3.1. 신규 Web UI 레포지토리 생성

*   `prism-insight-web`이라는 이름의 새로운 GitHub 레포지토리를 생성합니다.
*   해당 레포지토리에는 React 기반의 프론트엔드 애플리케이션 코드를 위치시킵니다.
*   `create-react-app` 또는 `Vite`를 사용하여 초기 프로젝트를 구성합니다.

### 3.2. API 계약 정의 (API Contract)

프론트엔드와 백엔드 간의 원활한 통신을 위해 명확한 API 계약을 정의해야 합니다. 이는 `OpenAPI (Swagger)`와 같은 도구를 사용하여 문서화하고, 지속적으로 최신 상태를 유지해야 합니다.

*   **API 엔드포인트:** 각 기능에 대한 API 엔드포인트 URL을 정의합니다. (e.g., `/api/v1/stocks`, `/api/v1/analysis`)
*   **요청/응답 형식:** 각 API의 요청 및 응답 데이터 형식을 JSON 스키마로 명확하게 정의합니다.
*   **인증 방식:** JWT(JSON Web Token)를 사용한 인증 방식을 정의하고, 토큰의 발급, 갱신, 검증 절차를 명시합니다.

### 3.3. Web UI 개발

*   정의된 API 계약을 바탕으로 프론트엔드 개발을 진행합니다.
*   API 클라이언트 라이브러리(e.g., `axios`)를 사용하여 백엔드 API와 통신합니다.
*   `PRISM-INSIGHT_Technical_Design.md`에 정의된 와이어프레임을 기반으로 UI를 구현합니다.

### 3.4. Web UI 배포

*   Web UI는 정적 웹사이트 형태로 빌드하여 AWS S3, Google Cloud Storage, Vercel, Netlify와 같은 클라우드 스토리지 또는 정적 호스팅 서비스에 배포합니다.
*   GitHub Actions를 사용하여 CI/CD 파이프라인을 구축하고, `main` 브랜치에 코드가 머지되면 자동으로 빌드 및 배포가 이루어지도록 설정합니다.

### 3.5. CORS (Cross-Origin Resource Sharing) 설정

백엔드 API 서버는 프론트엔드 애플리케이션으로부터의 API 요청을 허용하도록 CORS 설정을 추가해야 합니다. 이는 `FastAPI`의 `CORSMiddleware`를 사용하여 구현할 수 있습니다.

```python
# PRISM-INSIGHT 백엔드 API 서버 (main.py 예시)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정
origins = [
    "http://localhost:3000",  # 로컬 개발 환경
    "https://prism-insight-web.vercel.app",  # 배포된 프론트엔드 URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... API 라우터 설정 ...
```

## 4. 기대 효과

*   **빠른 개발 속도:** 프론트엔드와 백엔드 팀이 병렬로 개발을 진행하여 전체적인 개발 속도를 높일 수 있습니다.
*   **유연한 확장:** 향후 모바일 앱 등 새로운 클라이언트를 추가할 때, 기존 백엔드 API를 재사용하여 쉽게 확장할 수 있습니다.
*   **안정적인 서비스 운영:** 프론트엔드와 백엔드의 배포가 분리되어 있어, 한쪽의 변경 사항이 다른 쪽에 미치는 영향을 최소화하고 안정적인 서비스 운영이 가능합니다.
