#!/bin/bash

# 로그 파일 설정
LOG_FILE="/root/kospi-kosdaq-stock-analyzer/stock_scheduler.log"
SCRIPT_DIR="/root/kospi-kosdaq-stock-analyzer"  # 실제 프로젝트 경로로 변경

# 로그 함수
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 현재 디렉토리를 스크립트 디렉토리로 변경
cd $SCRIPT_DIR

# 시장 영업일 체크
log "주식 시장 영업일 체크 시작"
python check_market_day.py
MARKET_CHECK=$?

if [ $MARKET_CHECK -ne 0 ]; then
    log "오늘은 주식 시장 영업일이 아닙니다. 스크립트 실행을 건너뜁니다."
    exit 0
fi

# 실행할 프로그램 모드
MODE=$1
ACCOUNT_TYPE="premium"

# 로그 출력
log "실행 모드: $MODE"

# 가상환경 활성화 (있는 경우)
if [ -f "venv/bin/activate" ]; then
    log "가상환경 활성화"
    source venv/bin/activate
fi

# 스크립트 실행
log "$MODE 배치 실행 시작"
python stock_analysis_orchestrator.py --mode $MODE --account-type $ACCOUNT_TYPE >> $LOG_FILE 2>&1
RESULT=$?

if [ $RESULT -eq 0 ]; then
    log "$MODE 배치 실행 완료: 성공"
else
    log "$MODE 배치 실행 완료: 실패 (종료 코드: $RESULT)"
fi

# 가상환경 비활성화 (활성화한 경우)
if [ -f "venv/bin/activate" ]; then
    deactivate
fi

exit $RESULT