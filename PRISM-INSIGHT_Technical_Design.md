# PRISM-INSIGHT 고도화 상세 설계 문서

## 1. 시스템 아키텍처

PRISM-INSIGHT 고도화 프로젝트는 마이크로서비스 아키텍처(MSA)를 기반으로 각 기능을 독립적인 모듈로 분리하여 개발 및 유지보수의 효율성을 극대화합니다. 각 모듈은 RESTful API를 통해 상호 통신하며, 모든 서비스는 Docker 컨테이너로 패키징되어 Kubernetes(K8s) 환경에서 관리됩니다.

### 1.1. 아키텍처 다이어그램

```
+-----------------+      +-----------------+      +-----------------+
|   Web UI (React)  |----->|  API Gateway    |----->|  Auth Service   |
+-----------------+      +-----------------+      +-----------------+
                             |      ^      ^
                             |      |      |
                             v      |      |
+-----------------+      +-----------------+      +-----------------+
| Data Collector  |<-----|  Task Queue     |----->| Analysis Service|
| (pykrx, etc.)   |      | (Celery, Redis) |      | (Plugin-based)  |
+-----------------+      +-----------------+      +-----------------+
                             ^      |      ^
                             |      |      |
                             |      v      |
+-----------------+      +-----------------+      +-----------------+
| Database        |<-----| Reporting       |----->| Trading Service |
| (PostgreSQL)    |      | Service         |      | (Simulation)    |
+-----------------+      +-----------------+      +-----------------+
```

### 1.2. 모듈별 역할

*   **Web UI:** React 기반의 싱글 페이지 애플리케이션(SPA)으로, 사용자에게 대시보드, 종목 분석, 백테스팅 등 다양한 기능을 제공합니다.
*   **API Gateway:** 모든 클라이언트 요청의 진입점으로, 인증, 라우팅, 로드 밸런싱 등의 역할을 수행합니다. (e.g., Nginx, Spring Cloud Gateway)
*   **Auth Service:** JWT(JSON Web Token) 기반의 사용자 인증 및 인가 서비스를 제공합니다.
*   **Data Collector:** `pykrx` 및 외부 API를 통해 주가, 재무, 뉴스 등 다양한 데이터를 수집하여 데이터베이스에 저장하는 역할을 담당합니다.
*   **Task Queue:** Celery와 Redis를 사용하여 데이터 수집, 분석, 리포트 생성 등 시간이 오래 걸리는 작업을 비동기적으로 처리합니다.
*   **Analysis Service:** 플러그인 형태로 확장 가능한 AI 기반 분석 서비스를 제공합니다. 각 분석 모델은 독립적인 플러그인으로 개발되어 동적으로 추가/제거/업데이트가 가능합니다.
*   **Reporting Service:** 분석 결과를 바탕으로 Markdown, PDF, HTML 등 다양한 형태의 리포트를 생성합니다.
*   **Trading Service:** 분석 결과를 바탕으로 모의 투자를 실행하고, 투자 내역 및 성과를 기록합니다.
*   **Database:** PostgreSQL을 사용하여 모든 데이터를 영구적으로 저장합니다.

## 2. 데이터 모델

SQLAlchemy를 사용하여 데이터베이스 스키마를 정의하고, 데이터베이스와의 상호작용을 추상화합니다.

### 2.1. ERD (Entity-Relationship Diagram)

```
[User]
- id (PK)
- username
- password_hash
- email

[Stock]
- id (PK)
- ticker
- company_name

[StockData]
- id (PK)
- stock_id (FK to Stock)
- date
- open
- high
- low
- close
- volume

[AnalysisReport]
- id (PK)
- stock_id (FK to Stock)
- user_id (FK to User)
- created_at
- content (JSON)

[BacktestResult]
- id (PK)
- user_id (FK to User)
- strategy_name
- start_date
- end_date
- result (JSON)
```

## 3. API 명세

RESTful API는 FastAPI를 사용하여 구현하며, 모든 API는 인증을 위해 JWT 토큰을 필요로 합니다.

*   **`POST /api/v1/auth/signup`**: 회원가입
*   **`POST /api/v1/auth/login`**: 로그인
*   **`GET /api/v1/stocks`**: 주식 목록 조회
*   **`GET /api/v1/stocks/{ticker}`**: 특정 주식 정보 조회
*   **`POST /api/v1/analysis`**: 특정 주식 분석 요청 (비동기 처리)
*   **`GET /api/v1/analysis/{report_id}`**: 분석 리포트 조회
*   **`POST /api/v1/backtest`**: 백테스팅 실행 요청 (비동기 처리)
*   **`GET /api/v1/backtest/{backtest_id}`**: 백테스팅 결과 조회

## 4. 웹 UI/UX 디자인

### 4.1. 와이어프레임

*   **대시보드:**
    *   상단: 주요 지수(KOSPI, KOSDAQ) 현황
    *   좌측: 사용자 포트폴리오 요약 (수익률, 보유 종목)
    *   중앙: 주요 뉴스 및 시장 동향
    *   우측: 관심 종목 실시간 시세
*   **종목 분석 페이지:**
    *   상단: 종목 검색창
    *   중앙: Plotly 기반의 상호작용 가능한 주가 차트
    *   하단: AI 분석 리포트 (기술적 분석, 기본적 분석, 뉴스 분석 등 탭으로 구성)
*   **백테스팅 페이지:**
    *   좌측: 투자 전략 설정 (종목, 기간, 매매 조건 등)
    *   우측: 백테스팅 결과 (누적 수익률 그래프, 주요 통계 지표)

## 5. 분석 플러그인 아키텍처

### 5.1. 플러그인 인터페이스

```python
from abc import ABC, abstractmethod

class AnalysisPlugin(ABC):

    @abstractmethod
    def get_name(self) -> str:
        """플러그인 이름 반환"""
        pass

    @abstractmethod
    def analyze(self, stock_data: pd.DataFrame, params: dict) -> dict:
        """분석 실행 및 결과 반환"""
        pass
```

### 5.2. 샘플 플러그인 (이동평균선 분석)

```python
class MovingAveragePlugin(AnalysisPlugin):

    def get_name(self) -> str:
        return "Moving Average Analysis"

    def analyze(self, stock_data: pd.DataFrame, params: dict) -> dict:
        short_window = params.get("short_window", 20)
        long_window = params.get("long_window", 60)

        stock_data["short_ma"] = stock_data["close"].rolling(window=short_window).mean()
        stock_data["long_ma"] = stock_data["close"].rolling(window=long_window).mean()

        # 골든 크로스/데드 크로스 시그널 생성
        signals = ...

        return {"signals": signals, "plot_data": {"short_ma": ..., "long_ma": ...}}
```

## 6. 배포 및 CI/CD

*   **인프라:** AWS EKS(Elastic Kubernetes Service)를 사용하여 컨테이너화된 애플리케이션을 배포하고 관리합니다.
*   **CI/CD:** GitHub Actions를 사용하여 CI/CD 파이프라인을 구축합니다.
    *   **CI (Continuous Integration):**
        1.  개발자가 코드를 GitHub에 푸시합니다.
        2.  GitHub Actions가 자동으로 Pytest를 사용하여 단위/통합 테스트를 실행합니다.
        3.  테스트 통과 시 Docker 이미지를 빌드하여 ECR(Elastic Container Registry)에 푸시합니다.
    *   **CD (Continuous Deployment):**
        1.  새로운 Docker 이미지가 ECR에 푸시되면, Argo CD가 이를 감지합니다.
        2.  Argo CD는 K8s 클러스터에 새로운 버전의 애플리케이션을 자동으로 배포합니다.
