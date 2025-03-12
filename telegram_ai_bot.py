#!/usr/bin/env python3
"""
텔레그램 AI 대화형 봇

사용자 질의에 맞춤형 응답을 제공하는 봇:
- 사용자 질의를 처리하여 보유 종목에 대한 분석 및 조언 제공
- 관련 시장 데이터 및 보고서 참조하여 정확한 정보 제공
- 친근하고 공감적인 톤으로 응답
"""
import asyncio
import json
import logging
import os
import re
import signal
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from mcp_agent.agents.agent import Agent
from mcp_agent.app import MCPApp
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
)

# 환경 변수 로드
load_dotenv()

# 로거 설정
from logging.handlers import RotatingFileHandler
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            f"ai_bot_{datetime.now().strftime('%Y%m%d')}.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)

# 상수 정의
REPORTS_DIR = Path("reports")
CHOOSING_TICKER, ENTERING_AVGPRICE, ENTERING_PERIOD = range(3)

class TelegramAIBot:
    """텔레그램 AI 대화형 봇"""

    def __init__(self):
        """초기화"""
        self.token = os.getenv("TELEGRAM_AI_BOT_TOKEN")
        if not self.token:
            raise ValueError("텔레그램 봇 토큰이 설정되지 않았습니다.")

        # 종목 정보 초기화
        self.stock_map = {}
        self.stock_name_map = {}
        self.load_stock_map()

        self.stop_event = asyncio.Event()

        # MCPApp 초기화
        self.app = MCPApp(name="telegram_ai_bot")

        # 봇 어플리케이션 생성
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

    def load_stock_map(self):
        """
        종목 코드와 이름을 매핑하는 딕셔너리 로드
        """
        try:
            # 종목 정보 파일 경로
            stock_map_file = "stock_map.json"

            logger.info(f"종목 매핑 정보 로드 시도: {stock_map_file}")

            if os.path.exists(stock_map_file):
                with open(stock_map_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.stock_map = data.get("code_to_name", {})
                    self.stock_name_map = data.get("name_to_code", {})

                logger.info(f"{len(self.stock_map)} 개의 종목 정보 로드 완료")
            else:
                logger.warning(f"종목 정보 파일이 존재하지 않습니다: {stock_map_file}")
                # 기본 데이터를 제공 (테스트용)
                self.stock_map = {"005930": "삼성전자", "013700": "까뮤이앤씨"}
                self.stock_name_map = {"삼성전자": "005930", "까뮤이앤씨": "013700"}

        except Exception as e:
            logger.error(f"종목 정보 로드 실패: {e}")
            # 기본 데이터라도 제공
            self.stock_map = {"005930": "삼성전자", "013700": "까뮤이앤씨"}
            self.stock_name_map = {"삼성전자": "005930", "까뮤이앤씨": "013700"}

    def setup_handlers(self):
        """
        핸들러 등록
        """
        # 기본 명령어
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))

        # 평가 대화 핸들러
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("evaluate", self.handle_evaluate_start),
                # 그룹 채팅을 위한 패턴 추가
                MessageHandler(filters.Regex(r'^/evaluate(@\w+)?$'), self.handle_evaluate_start)
            ],
            states={
                CHOOSING_TICKER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_ticker_input)
                ],
                ENTERING_AVGPRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_avgprice_input)
                ],
                ENTERING_PERIOD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_period_input)
                ],
            },
            fallbacks=[
                CommandHandler("cancel", self.handle_cancel),
                # 다른 명령어도 추가
                CommandHandler("start", self.handle_cancel),
                CommandHandler("help", self.handle_cancel)
            ],
            # 그룹 채팅에서 다른 사용자의 메시지 구분
            per_chat=False,
            per_user=True,
            # 대화 시간 제한 (초)
            conversation_timeout=300,
        )
        self.application.add_handler(conv_handler)

        # 일반 텍스트 메시지
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))

        # 오류 핸들러
        self.application.add_error_handler(self.handle_error)

    def is_stock_inquiry(self, message_text):
        """
        메시지가 특정 종목에 대한 질문인지 확인

        Args:
            message_text (str): 사용자 메시지

        Returns:
            bool: 종목 질문 여부
        """
        # 종목 코드 패턴 (6자리 숫자)
        if re.search(r'\b\d{6}\b', message_text):
            return True

        # 종목명 포함 여부 확인
        for stock_name in self.stock_name_map.keys():
            if stock_name in message_text:
                return True

        # 종목 관련 키워드 확인
        stock_keywords = ["주가", "종목", "주식", "전망", "실적", "투자", "매수", "매도"]
        return any(keyword in message_text for keyword in stock_keywords)

    def extract_stock_info(self, message_text):
        """
        메시지에서 종목 코드나 이름 추출

        Args:
            message_text (str): 사용자 메시지

        Returns:
            tuple: (종목 코드, 종목 이름) 또는 (None, None)
        """
        # 종목 코드 패턴 (6자리 숫자) 찾기
        code_match = re.search(r'\b(\d{6})\b', message_text)
        if code_match:
            stock_code = code_match.group(1)
            stock_name = self.stock_map.get(stock_code)
            if stock_name:
                return stock_code, stock_name

        # 종목명 찾기
        for stock_name, stock_code in self.stock_name_map.items():
            if stock_name in message_text:
                return stock_code, stock_name

        return None, None

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어 처리"""
        user = update.effective_user
        await update.message.reply_text(
            f"안녕하세요, {user.first_name}님! 저는 주식 분석 AI 봇입니다.\n\n"
            "다음과 같은 방법으로 저와 대화할 수 있습니다:\n"
            "- /evaluate 명령어로 보유 종목에 대한 평가를 요청\n"
            "- 종목이나 시장에 관한 질문을 직접 물어보기\n\n"
            "더 자세한 정보는 /help 명령어를 입력해주세요."
        )

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말 명령어 처리"""
        await update.message.reply_text(
            "📊 <b>주식 분석 AI 봇 도움말</b> 📊\n\n"
            "<b>기본 명령어:</b>\n"
            "/start - 봇 시작\n"
            "/help - 도움말 보기\n"
            "/evaluate - 보유 종목 평가 시작\n"
            "/cancel - 현재 진행 중인 대화 취소\n\n"
            "<b>보유 종목 평가 방법:</b>\n"
            "1. /평가 명령어 입력\n"
            "2. 종목 코드 또는 이름 입력\n"
            "3. 평균 매수가 입력\n"
            "4. 보유 기간 입력\n\n"
            "<b>일반 질문:</b>\n"
            "종목이나 시장에 관한 궁금한 점을 자유롭게 물어보세요!\n"
            "예: \"삼성전자 전망이 어떤가요?\", \"코스피 지수 상승 하락 이유는?\"",
            parse_mode="HTML"
        )

    async def handle_evaluate_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """평가 명령어 처리 - 첫 단계"""
        # 그룹 채팅인지 개인 채팅인지 확인
        is_group = update.effective_chat.type in ["group", "supergroup"]
        user_name = update.effective_user.first_name

        logger.info(f"평가 명령 시작 - 사용자: {user_name}, 채팅타입: {'그룹' if is_group else '개인'}")

        # 그룹 채팅에서는 사용자 이름을 언급
        greeting = f"{user_name}님, " if is_group else ""

        await update.message.reply_text(
            f"{greeting}보유하신 종목의 코드나 이름을 입력해주세요. \n"
            "예: 005930 또는 삼성전자"
        )
        return CHOOSING_TICKER

    async def handle_ticker_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """종목 입력 처리"""
        user_id = update.effective_user.id
        user_input = update.message.text.strip()
        logger.info(f"종목 입력 받음 - 사용자: {user_id}, 입력: {user_input}")

        # 종목 코드 또는 이름을 처리
        stock_code, stock_name, error_message = await self.get_stock_code(user_input)

        if error_message:
            # 오류가 있으면 사용자에게 알리고 다시 입력 받음
            await update.message.reply_text(error_message)
            return CHOOSING_TICKER

        # 종목 정보 저장
        context.user_data['ticker'] = stock_code
        context.user_data['ticker_name'] = stock_name

        logger.info(f"종목 선택: {stock_name} ({stock_code})")

        await update.message.reply_text(
            f"{stock_name} ({stock_code}) 종목을 선택하셨습니다.\n\n"
            f"평균 매수가를 입력해주세요. (숫자만 입력)\n"
            f"예: 68500"
        )

        logger.info(f"상태 전환: ENTERING_AVGPRICE - 사용자: {user_id}")
        return ENTERING_AVGPRICE

    async def handle_avgprice_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """평균 매수가 입력 처리"""
        try:
            avg_price = float(update.message.text.strip().replace(',', ''))
            context.user_data['avg_price'] = avg_price

            await update.message.reply_text(
                f"보유 기간을 입력해주세요. (개월 수)\n"
                f"예: 6 (6개월)"
            )
            return ENTERING_PERIOD

        except ValueError:
            await update.message.reply_text(
                "숫자 형식으로 입력해주세요. 콤마는 제외해주세요.\n"
                "예: 68500"
            )
            return ENTERING_AVGPRICE

    async def handle_period_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """보유 기간 입력 처리"""
        try:
            period = int(update.message.text.strip())
            context.user_data['period'] = period

            # 응답 대기 메시지
            waiting_message = await update.message.reply_text(
                "종목 분석 중입니다... 잠시만 기다려주세요."
            )

            # AI 에이전트로 분석 요청
            ticker = context.user_data['ticker']
            ticker_name = context.user_data.get('ticker_name', f"종목_{ticker}")
            avg_price = context.user_data['avg_price']
            period = context.user_data['period']

            # 최신 보고서 찾기
            latest_report = self.find_latest_report(ticker)

            # AI 응답 생성
            response = await self.generate_evaluation_response(
                ticker, ticker_name, avg_price, period, latest_report
            )

            # 대기 메시지 삭제
            await waiting_message.delete()

            # 응답 전송
            await update.message.reply_text(response)

            # 대화 종료
            return ConversationHandler.END

        except ValueError:
            await update.message.reply_text(
                "숫자 형식으로 입력해주세요.\n"
                "예: 6"
            )
            return ENTERING_PERIOD

    async def handle_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """대화 취소 처리"""
        # 사용자 데이터 초기화
        context.user_data.clear()

        await update.message.reply_text(
            "평가 요청이 취소되었습니다. 다시 시작하려면 /evaluate 명령어를 입력해주세요."
        )
        return ConversationHandler.END

    async def handle_stock_inquiry(self, update, context, stock_code, stock_name):
        """
        종목 관련 질문 처리

        Args:
            update (Update): 텔레그램 업데이트 객체
            context (CallbackContext): 콜백 컨텍스트
            stock_code (str): 종목 코드
            stock_name (str): 종목 이름
        """
        # 응답 대기 메시지
        waiting_message = await update.message.reply_text(
            f"{stock_name} 종목에 대한 정보를 분석 중입니다... 잠시만 기다려주세요."
        )

        # 최신 보고서 찾기
        latest_report = self.find_latest_report(stock_code)

        # AI 응답 생성
        try:
            # 사용자 질문 추출
            question = update.message.text

            # 종목 정보와 질문을 바탕으로 AI 응답 생성
            response = await self.generate_stock_inquiry_response(
                stock_code, stock_name, question, latest_report
            )

            # 대기 메시지 삭제
            try:
                await waiting_message.delete()
            except Exception as e:
                logger.warning(f"대기 메시지 삭제 실패: {e}")

            # 응답 전송
            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"종목 질의 응답 생성 중 오류: {e}")

            # 대기 메시지 삭제 시도
            try:
                await waiting_message.delete()
            except:
                pass

            await update.message.reply_text(
                f"죄송합니다. {stock_name} 종목에 대한 정보를 분석하는 중 오류가 발생했습니다. 다시 시도해주세요."
            )

    async def generate_stock_inquiry_response(self, ticker, ticker_name, question, report_path=None):
        """
        종목 질의에 대한 AI 응답 생성

        Args:
            ticker (str): 종목 코드
            ticker_name (str): 종목 이름
            question (str): 사용자 질문
            report_path (str, optional): 보고서 파일 경로

        Returns:
            str: AI 응답
        """
        try:
            async with self.app.run() as app:
                logger = app.logger

                # 에이전트 생성
                agent = Agent(
                    name="stock_inquiry_agent",
                    instruction=f"""당신은 주식 종목 정보 제공 전문가입니다. 사용자의 종목 관련 질문에 전문적이고 친근한 톤으로 응답해야 합니다.
                    
                    ## 정보
                    - 종목 코드: {ticker}
                    - 종목 이름: {ticker_name}
                    - 사용자 질문: {question}
                    
                    ## 응답 스타일
                    - 친한 친구가 조언하는 것처럼 편안하고 공감적인 톤 유지
                    - "~님"이나 존칭 대신 친구에게 말하듯 casual한 표현 사용
                    - 질문의 의도를 정확히 파악하고 핵심에 집중
                    - 전문 지식을 바탕으로 한 실질적인 정보 제공
                    """,
                    server_names=["exa", "kospi_kosdaq"]
                )

                # LLM 연결
                llm = await agent.attach_llm(OpenAIAugmentedLLM)

                # 보고서 내용 확인
                report_content = ""
                if report_path and os.path.exists(report_path):
                    with open(report_path, 'r', encoding='utf-8') as f:
                        report_content = f.read()

                # 응답 생성
                response = await llm.generate_str(
                    message=f"""다음 종목에 관한 질문에 답변해주세요:
                    
                    ## 정보
                    - 종목 코드: {ticker}
                    - 종목 이름: {ticker_name}
                    - 사용자 질문: {question}
                    
                    ## 참고 자료
                    {report_content if report_content else "관련 보고서가 없습니다. 일반적인 시장 지식과 최근 동향을 바탕으로 답변해주세요."}
                    """,
                    request_params=RequestParams(
                        model="gpt-4o-mini",
                        maxTokens=1500,
                        max_iterations=1,
                        parallel_tool_calls=False,
                        use_history=False
                    )
                )

                return response

        except Exception as e:
            logger.error(f"종목 질의 응답 생성 중 오류: {str(e)}")
            return f"죄송합니다. {ticker_name} 종목에 대한 정보를 분석하는 중 오류가 발생했습니다. 다시 시도해주세요."

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일반 메시지 처리"""
        message_text = update.message.text
        logger.info(f"사용자 메시지 수신: {message_text[:50]}...")

        # 특정 종목에 대한 질문인지 확인
        if self.is_stock_inquiry(message_text):
            # 종목 코드 또는 이름 추출
            stock_code, stock_name = self.extract_stock_info(message_text)
            if stock_code:
                # 종목에 대한 AI 응답 생성
                await self.handle_stock_inquiry(update, context, stock_code, stock_name)
                return

        # 응답 대기 메시지
        waiting_message = await update.message.reply_text(
            "질문을 분석 중입니다... 잠시만 기다려주세요."
        )

        # AI 응답 생성 (일반 대화용)
        try:
            response = await self.generate_conversation_response(message_text)

            # 대기 메시지 삭제
            try:
                await waiting_message.delete()
            except Exception as e:
                logger.warning(f"대기 메시지 삭제 실패: {e}")

            # 응답 전송
            await update.message.reply_text(response)

        except Exception as e:
            logger.error(f"응답 생성 중 오류: {e}")
            await update.message.reply_text(
                "죄송합니다. 응답 생성 중 오류가 발생했습니다. 다시 시도해주세요."
            )

    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """오류 처리"""
        error_msg = str(context.error)
        logger.error(f"오류 발생: {error_msg}")

        # 사용자에게 보여줄 오류 메시지
        user_msg = "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."

        # 타임아웃 오류 처리
        if "timed out" in error_msg.lower():
            user_msg = "요청 처리 시간이 초과되었습니다. 네트워크 상태를 확인하고 다시 시도해주세요."
        # 권한 오류 처리
        elif "permission" in error_msg.lower():
            user_msg = "봇이 메시지를 보낼 권한이 없습니다. 그룹 설정을 확인해주세요."
        # 다양한 오류 정보 로깅
        logger.error(f"오류 상세 정보: {traceback.format_exc()}")

        # 오류 응답 전송
        if update and update.effective_message:
            await update.effective_message.reply_text(user_msg)

    def find_latest_report(self, ticker):
        """
        특정 종목의 최신 보고서 찾기

        Args:
            ticker (str): 종목 코드

        Returns:
            str or None: 최신 보고서 파일 경로 또는 None
        """
        if not REPORTS_DIR.exists():
            return None

        # 종목 코드로 시작하는 보고서 파일 찾기
        report_files = list(REPORTS_DIR.glob(f"{ticker}_*.md"))

        if not report_files:
            return None

        # 최신 파일 찾기 (수정 시간 기준)
        latest_report = max(report_files, key=lambda p: p.stat().st_mtime)

        return str(latest_report)

    async def get_stock_code(self, stock_input):
        """
        종목명 또는 코드를 입력받아 종목 코드로 변환

        Args:
            stock_input (str): 종목 코드 또는 이름

        Returns:
            tuple: (종목 코드, 종목 이름, 오류 메시지)
        """
        stock_input = stock_input.strip()

        # 이미 종목 코드인 경우 (6자리 숫자)
        if re.match(r'^\d{6}$', stock_input):
            stock_code = stock_input
            stock_name = self.stock_map.get(stock_code)

            if stock_name:
                return stock_code, stock_name, None
            else:
                return stock_code, f"종목_{stock_code}", "해당 종목 코드에 대한 정보가 없습니다. 코드가 정확한지 확인해주세요."

        # 종목명으로 입력한 경우 - 정확히 일치하는 경우 확인
        if stock_input in self.stock_name_map:
            stock_code = self.stock_name_map[stock_input]
            return stock_code, stock_input, None

        # 종목명 부분 일치 검색
        possible_matches = []
        for name, code in self.stock_name_map.items():
            if stock_input.lower() in name.lower():
                possible_matches.append((name, code))

        if len(possible_matches) == 1:
            # 단일 일치 항목이 있으면 사용
            stock_name, stock_code = possible_matches[0]
            return stock_code, stock_name, None
        elif len(possible_matches) > 1:
            # 여러 일치 항목이 있으면 오류 메시지 반환
            match_info = "\n".join([f"{name} ({code})" for name, code in possible_matches[:5]])
            if len(possible_matches) > 5:
                match_info += f"\n... 외 {len(possible_matches)-5}개"

            return None, None, f"'{stock_input}'에 여러 일치하는 종목이 있습니다. 정확한 종목명이나 종목코드를 입력해주세요:\n{match_info}"
        else:
            # 일치하는 항목이 없으면 오류 메시지 반환
            return None, None, f"'{stock_input}'에 해당하는 종목을 찾을 수 없습니다. 정확한 종목명이나 종목코드를 입력해주세요."

    async def generate_evaluation_response(self, ticker, ticker_name, avg_price, period, report_path=None):
        """
        종목 평가 AI 응답 생성

        Args:
            ticker (str): 종목 코드
            ticker_name (str): 종목 이름
            avg_price (float): 평균 매수가
            period (int): 보유 기간 (개월)
            report_path (str, optional): 보고서 파일 경로

        Returns:
            str: AI 응답
        """
        try:
            async with self.app.run() as app:
                logger = app.logger

                # 에이전트 생성
                agent = Agent(
                    name="evaluation_agent",
                    instruction=f"""당신은 주식 종목 평가 전문가입니다. 사용자가 보유한 종목에 대해 친근하고 공감적인 톤으로 평가와 조언을 제공해야 합니다.

                                ## 평가 정보
                                - 종목 코드: {ticker}
                                - 종목 이름: {ticker_name}
                                - 평균 매수가: {avg_price}원
                                - 보유 기간: {period}개월

                                ## 응답 스타일
                                - 친한 친구가 조언하는 것처럼 편안하고 공감적인 톤 유지
                                - 투자 심리에 대한 공감과 이해 표현
                                - "~님"이나 존칭 대신 친구에게 말하듯 casual한 표현 사용
                                - 전문 지식을 바탕으로 한 실질적인 조언 제공
                                - 긍정적인 측면과 주의해야 할 측면을 균형있게 설명
                                - 너무 조심스럽거나 책임 회피적인 표현 지양

                                ## 응답 구성
                                1. 간단한 인사와 현재 상황 요약
                                2. 현재 주가와 매수가 비교 및 손익 언급
                                3. 해당 종목의 최근 동향 설명
                                4. 향후 전망에 대한 의견 (단기/중기)
                                5. 손익 실현 또는 추가 매수에 대한 의견
                                6. 심리적 조언 (투자 심리 관련)
                                7. 응원과 마무리

                                ## 주의사항
                                - 실제 보유 종목의 최신 정보 참조하여 정확한 내용 포함
                                - 종목 정보뿐 아니라 최신 업계 흐름이나 경제 동향을 웹서치하여 참조하여 응답에 활용
                                - 지나치게 낙관적이거나 비관적인 표현 지양
                                - 투자 결정은 최종적으로 사용자가 하도록 유도
                                - 불확실한 내용은 정직하게 인정
                                """,
                    server_names=["exa", "kospi_kosdaq"]
                )

                # LLM 연결
                llm = await agent.attach_llm(OpenAIAugmentedLLM)

                # 보고서 내용 확인
                report_content = ""
                if report_path and os.path.exists(report_path):
                    with open(report_path, 'r', encoding='utf-8') as f:
                        report_content = f.read()

                # 응답 생성
                response = await llm.generate_str(
                    message=f"""보유한 주식 종목에 대한 평가와 조언을 친근하고 공감적인 톤으로 해줘.

                            ## 평가 정보
                            - 종목 코드: {ticker}
                            - 종목 이름: {ticker_name}
                            - 평균 매수가: {avg_price}원
                            - 보유 기간: {period}개월

                            ## 참고 자료
                            {report_content if report_content else "관련 보고서가 없습니다. 일반적인 시장 지식과 최근 동향을 바탕으로 평가해주세요."}
                            """,
                    request_params=RequestParams(
                        model="gpt-4o-mini",
                        maxTokens=1500,
                        max_iterations=1,
                        parallel_tool_calls=False,
                        use_history=False
                    )
                )

                return response

        except Exception as e:
            logger.error(f"응답 생성 중 오류: {str(e)}")
            return "죄송합니다. 평가 중 오류가 발생했습니다. 다시 시도해주세요."

    async def generate_conversation_response(self, message_text):
        """
        일반 대화 AI 응답 생성

        Args:
            message_text (str): 사용자 메시지

        Returns:
            str: AI 응답
        """
        try:
            async with self.app.run() as app:
                logger = app.logger

                # 에이전트 생성
                agent = Agent(
                    name="conversation_agent",
                    instruction=f"""당신은 주식 및 투자 상담 전문가입니다. 사용자의 다양한 질문에 친근하고 공감적인 톤으로 전문적인 답변을 제공해야 합니다.

                                ## 응답 스타일
                                - 친한 친구가 조언하는 것처럼 편안하고 공감적인 톤 유지
                                - "~님"이나 존칭 대신 친구에게 말하듯 casual한 표현 사용
                                - 질문의 의도를 정확히 파악하고 핵심에 집중
                                - 전문 지식을 바탕으로 한 실질적인 정보 제공
                                - 너무 조심스럽거나 책임 회피적인 표현 지양
                                - 필요한 경우 추가 질문 유도

                                ## 응답 구성
                                1. 질문 의도 확인 또는 인사
                                2. 핵심 정보 제공
                                3. 관련 배경 지식 또는 맥락 설명
                                4. 실질적인 조언이나 관점 제시
                                5. 필요시 추가 질문이나 마무리

                                ## 주의사항
                                - 최신 시장 정보 및 종목 동향 참조하여 정확한 내용 포함
                                - 지나치게 낙관적이거나 비관적인 표현 지양
                                - 투자 결정은 최종적으로 사용자가 하도록 유도
                                - 불확실한 내용은 정직하게 인정
                                """
                )

                # LLM 연결
                llm = await agent.attach_llm(OpenAIAugmentedLLM)

                # 응답 생성
                response = await llm.generate_str(
                    message=f"""다음 질문에 친근하고 공감적인 톤으로 답변해주세요:

                            질문: {message_text}
                            """,
                    request_params=RequestParams(
                        model="gpt-4o-mini",
                        maxTokens=1500,
                        max_iterations=1,
                        parallel_tool_calls=False,
                        use_history=False
                    )
                )

                return response

        except Exception as e:
            logger.error(f"응답 생성 중 오류: {str(e)}")
            return "죄송합니다. 응답 생성 중 오류가 발생했습니다. 다시 시도해주세요."

    async def run(self):
        """봇 실행"""
        # 봇 실행
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        logger.info("텔레그램 AI 대화형 봇이 시작되었습니다.")

        try:
            # 봇이 중단될 때까지 실행 유지
            # 무한 대기하기 위한 간단한 방법
            await self.stop_event.wait()
        except asyncio.CancelledError:
            pass
        finally:
            # 종료 시 리소스 정리
            await self.application.stop()
            await self.application.shutdown()

            logger.info("텔레그램 AI 대화형 봇이 종료되었습니다.")


async def shutdown(sig, loop, *args):
    """Cleanup tasks tied to the service's shutdown."""
    logger.info(f"Received signal {sig.name}, shutting down...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        task.cancel()

    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

# 메인 실행 부분
async def main():
    """
    메인 함수
    """
    # 시그널 핸들러 설정
    loop = asyncio.get_event_loop()
    signals = (signal.SIGINT, signal.SIGTERM)

    def create_signal_handler(sig):
        return lambda: asyncio.create_task(shutdown(sig, loop))

    for s in signals:
        loop.add_signal_handler(s, create_signal_handler(s))

    bot = TelegramAIBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())