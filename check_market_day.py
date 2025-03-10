#!/usr/bin/env python3
import holidays
import datetime
import sys
import logging

# 로깅 설정
logging.basicConfig(
    filename='/root/kospi-kosdaq-stock-analyzer/stock_scheduler.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_market_day():
    """한국 주식 시장 영업일인지 확인"""
    today = datetime.date.today()

    # 주말 체크 (5:금요일, 6:토요일)
    if today.weekday() >= 5:
        logging.info(f"오늘은 주말입니다: {today}")
        return False

    # 한국 공휴일 체크
    kr_holidays = holidays.KR()
    if today in kr_holidays:
        logging.info(f"오늘은 공휴일입니다: {today} - {kr_holidays[today]}")
        return False

    # 영업일
    logging.info(f"오늘은 주식 시장 영업일입니다: {today}")
    return True

if __name__ == "__main__":
    if is_market_day():
        # 영업일이면 종료 코드 0 (정상)
        sys.exit(0)
    else:
        # 영업일이 아니면 종료 코드 1 (비정상)
        sys.exit(1)