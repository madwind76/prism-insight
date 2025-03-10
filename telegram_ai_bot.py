#!/usr/bin/env python3
"""
텔레그램 AI 대화형 봇

사용자 질의에 맞춤형 응답을 제공하는 봇:
- 사용자 질의를 처리하여 보유 종목에 대한 분석 및 조언 제공
- 관련 시장 데이터 및 보고서 참조하여 정확한 정보 제공
- 친근하고 공감적인 톤으로 응답
"""
import os
import logging
import re
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

from mcp_agent.agents.agent import Agent
from mcp_agent.app import MCPApp
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM

# 환경 변수 로드
load_dotenv()

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"ai_bot_{datetime.now().strftime('%Y%m%d')}.log")
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
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("텔레그램 봇 토큰이 설정되지 않았습니다.")

        # MCPApp 초기화
        self.app = MCPApp(name="telegram_ai_bot")

        # 봇 어플리케이션 생성
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """
        핸들러 등록
        """
        # 기본 명령어
        self.application.add_handler(CommandHandler("start", self.handle_start))
        self.application.add_handler(CommandHandler("help", self.handle_help))

        # 평가 대화 핸들러
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("평가", self.handle_evaluate_start)],
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
            fallbacks=[CommandHandler("취소", self.handle_cancel)],
        )
        self.application.add_handler(conv_handler)

        # 일반 텍스트 메시지
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))

        # 오류 핸들러
        self.application.add_error_handler(self.handle_error)

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 명령어 처리"""
        user = update.effective_user
        await update.message.reply_text(
            f"안녕하세요, {user.first_name}님! 저는 주식 분석 AI 봇입니다.\n\n"
            "다음과 같은 방법으로 저와 대화할 수 있습니다:\n"
            "- /평가 명령어로 보유 종목에 대한 평가를 요청\n"
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
            "/평가 - 보유 종목 평가 시작\n"
            "/취소 - 현재 진행 중인 대화 취소\n\n"
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
        await update.message.reply_text(
            "보유하신 종목의 코드나 이름을 입력해주세요. \n"
            "예: 005930 또는 삼성전자"
        )
        return CHOOSING_TICKER

    async def handle_ticker_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """종목 입력 처리"""
        ticker = update.message.text.strip()

        # 간단한 종목 코드 검증 (6자리 숫자)
        if re.match(r'^\d{6}$', ticker):
            context.user_data['ticker'] = ticker
        else:
            # 종목명으로 입력한 경우, 실제 코드로 변환해야 함
            # 여기서는 간단하게 처리 (실제로는 API 호출 또는 DB 조회 필요)
            context.user_data['ticker_name'] = ticker
            context.user_data['ticker'] = "000000"  # 임시 코드 (실제로는 맵핑 필요)

        await update.message.reply_text(
            f"평균 매수가를 입력해주세요. (숫자만 입력)\n"
            f"예: 68500"
        )
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
            "평가 요청이 취소되었습니다. 다시 시작하려면 /평가 명령어를 입력해주세요."
        )
        return ConversationHandler.END

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """일반 메시지 처리"""
        message_text = update.message.text

        # 응답 대기 메시지
        waiting_message = await update.message.reply_text(
            "질문을 분석 중입니다... 잠시만 기다려주세요."
        )

        # AI 응답 생성
        response = await self.generate_conversation_response(message_text)

        # 대기 메시지 삭제
        await waiting_message.delete()

        # 응답 전송
        await update.message.reply_text(response)

    async def handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """오류 처리"""
        logger.error(f"오류 발생: {context.error}")

        if update:
            await update.message.reply_text(
                "죄송합니다. 오류가 발생했습니다. 다시 시도해주세요."
            )

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
                    server_names=["exa"]
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
                        model="gpt-4o",
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
                        model="gpt-4o",
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
            await self.application.updater.stop_polling()  # 제어가 여기서 유지됨
        finally:
            # 종료 시 리소스 정리
            await self.application.stop()
            await self.application.shutdown()

            logger.info("텔레그램 AI 대화형 봇이 종료되었습니다.")

# 메인 실행 부분
async def main():
    bot = TelegramAIBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())