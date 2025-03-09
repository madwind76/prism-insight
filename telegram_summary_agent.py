import asyncio
import re
import os
import logging
from datetime import datetime
from pathlib import Path

from mcp_agent.agents.agent import Agent
from mcp_agent.app import MCPApp
from mcp_agent.workflows.llm.augmented_llm import RequestParams
from mcp_agent.workflows.llm.augmented_llm_openai import OpenAIAugmentedLLM

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MCPApp 인스턴스 생성
app = MCPApp(name="telegram_summary")

class TelegramSummaryGenerator:
    """
    보고서 파일을 읽어 텔레그램 메시지 요약을 생성하는 클래스
    """

    def __init__(self):
        """생성자"""
        pass

    async def read_report(self, report_path):
        """
        보고서 파일 읽기
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return content
        except Exception as e:
            logger.error(f"보고서 파일 읽기 실패: {e}")
            raise

    def extract_metadata_from_filename(self, filename):
        """
        파일 이름에서 종목코드, 종목명, 날짜 등을 추출
        """
        pattern = r'(\d+)_(.+)_(\d{8})_.*\.md'
        match = re.match(pattern, filename)

        if match:
            stock_code = match.group(1)
            stock_name = match.group(2)
            date_str = match.group(3)

            # YYYYMMDD 형식을 YYYY.MM.DD 형식으로 변환
            formatted_date = f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:8]}"

            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "date": formatted_date
            }
        else:
            # 파일명에서 정보를 추출할 수 없는 경우, 기본값 설정
            return {
                "stock_code": "N/A",
                "stock_name": Path(filename).stem,
                "date": datetime.now().strftime("%Y.%m.%d")
            }

    def determine_trigger_type(self, report_content):
        """
        보고서 내용을 분석하여 트리거 유형 결정
        """
        # 간단한 키워드 기반 트리거 유형 결정
        content_lower = report_content.lower()

        if "거래량" in content_lower and "폭증" in content_lower:
            return "거래량 폭증"
        elif "갭 상승" in content_lower:
            return "갭 상승 강세"
        elif "거래대금" in content_lower and "시가총액" in content_lower:
            return "시총 대비 거래대금 이상"
        elif "급등" in content_lower:
            return "장중 급등"
        elif "마감" in content_lower and "쏠림" in content_lower:
            return "마감 쏠림"
        else:
            return "주목할 패턴"

    ## todo : 고치자. 거래량,등락률은 가장 최신의 일자만. 관련 차트 부분은 빼자.
    async def generate_telegram_message(self, report_content, metadata, trigger_type):
        """
        텔레그램 메시지 생성
        """
        # 에이전트 생성
        telegram_agent = Agent(
            name="telegram_summary_agent",
            instruction=f"""당신은 주식 정보 요약 전문가입니다. 
                        상세한 주식 분석 보고서를 읽고, 일반 투자자를 위한 가치 있는 텔레그램 메시지로 요약해야 합니다.
                        메시지는 핵심 정보와 통찰력을 포함해야 하며, 아래 형식을 따라야 합니다:
                        
                        1. 이모지와 함께 트리거 유형 표시 (📊, 📈, 💰 등 적절한 이모지)
                        2. 종목명(코드) 정보 및 간략한 사업 설명 (1-2문장)
                        3. 핵심 거래 정보 - 반드시 보고서의 가장 최신 일자 기준으로 통일:
                           - 현재가
                           - 전일 대비 등락률
                           - 최근 거래량 (전일 대비 증감 퍼센트 포함)
                        4. 시가총액 정보 및 동종 업계 내 위치
                        5. 가장 관련 있는 최근 뉴스 1개와 잠재적 영향
                        6. 핵심 기술적 패턴 2-3개 (지지선/저항선 수치 포함)
                        7. 투자 관점 - 단기/중기 전망 또는 주요 체크포인트
                        
                        전체 메시지는 400자 내외로 작성하세요. 투자자가 즉시 활용할 수 있는 실질적인 정보에 집중하세요.
                        수치는 가능한 구체적으로 표현하고, 주관적 투자 조언이나 '추천'이라는 단어는 사용하지 마세요.
                        메시지 끝에는 "본 정보는 투자 참고용이며, 투자 결정과 책임은 투자자에게 있습니다." 문구를 반드시 포함하세요.
                        """
        )

        # LLM 연결
        llm = await telegram_agent.attach_llm(OpenAIAugmentedLLM)

        # 텔레그램 메시지 생성
        message = await llm.generate_str(
            message=f"""다음은 {metadata['stock_name']}({metadata['stock_code']}) 종목에 대한 상세 분석 보고서입니다. 
            이 종목은 {trigger_type} 트리거에 포착되었습니다. 
            이 내용을 기반으로 무료 사용자를 위한 간결한 텔레그램 메시지를 생성해주세요.
            
            보고서 내용:
            {report_content}
            """,
            request_params=RequestParams(
                model="gpt-4o",
                maxTokens=500,
                max_iterations=1,
                parallel_tool_calls=False,
                use_history=False
            )
        )

        return message

    def save_telegram_message(self, message, output_path):
        """
        생성된 텔레그램 메시지를 파일로 저장
        """
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(message)
            logger.info(f"텔레그램 메시지가 {output_path}에 저장되었습니다.")
        except Exception as e:
            logger.error(f"텔레그램 메시지 저장 실패: {e}")
            raise

    async def process_report(self, report_path, output_dir="telegram_messages"):
        """
        보고서 파일을 처리하여 텔레그램 요약 메시지 생성
        """
        try:
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)

            # 파일 이름에서 메타데이터 추출
            filename = os.path.basename(report_path)
            metadata = self.extract_metadata_from_filename(filename)

            logger.info(f"처리 중: {filename} - {metadata['stock_name']}({metadata['stock_code']})")

            # 보고서 내용 읽기
            report_content = await self.read_report(report_path)

            # 트리거 유형 결정
            trigger_type = self.determine_trigger_type(report_content)
            logger.info(f"감지된 트리거 유형: {trigger_type}")

            # 텔레그램 요약 메시지 생성
            telegram_message = await self.generate_telegram_message(
                report_content, metadata, trigger_type
            )

            # 출력 파일 경로 생성
            output_file = os.path.join(output_dir, f"{metadata['stock_code']}_{metadata['stock_name']}_telegram.txt")

            # 메시지 저장
            self.save_telegram_message(telegram_message, output_file)

            logger.info(f"텔레그램 메시지 생성 완료: {output_file}")

            return telegram_message

        except Exception as e:
            logger.error(f"보고서 처리 중 오류 발생: {e}")
            raise

async def process_all_reports(reports_dir="reports", output_dir="telegram_messages", date_filter=None):
    """
    지정된 디렉토리 내의 모든 보고서 파일을 처리
    """
    # 텔레그램 요약 생성기 초기화
    generator = TelegramSummaryGenerator()

    # 보고서 디렉토리 확인
    reports_path = Path(reports_dir)
    if not reports_path.exists() or not reports_path.is_dir():
        logger.error(f"보고서 디렉토리가 존재하지 않습니다: {reports_dir}")
        return

    # 보고서 파일 찾기
    report_files = list(reports_path.glob("*.md"))

    # 날짜 필터 적용
    if date_filter:
        report_files = [f for f in report_files if date_filter in f.name]

    if not report_files:
        logger.warning(f"처리할 보고서 파일이 없습니다. 디렉토리: {reports_dir}, 필터: {date_filter or '없음'}")
        return

    logger.info(f"{len(report_files)}개의 보고서 파일을 처리합니다.")

    # 각 보고서 처리
    for report_file in report_files:
        try:
            await generator.process_report(str(report_file), output_dir)
        except Exception as e:
            logger.error(f"{report_file.name} 처리 중 오류 발생: {e}")

    logger.info("모든 보고서 처리가 완료되었습니다.")

async def main():
    """
    메인 함수
    """
    import argparse

    parser = argparse.ArgumentParser(description="보고서 디렉토리의 모든 파일을 텔레그램 메시지로 요약합니다.")
    parser.add_argument("--reports-dir", default="reports", help="보고서 파일이 저장된 디렉토리 경로")
    parser.add_argument("--output-dir", default="telegram_messages", help="텔레그램 메시지 저장 디렉토리 경로")
    parser.add_argument("--date", help="특정 날짜의 보고서만 처리 (YYYYMMDD 형식)")
    parser.add_argument("--today", action="store_true", help="오늘 날짜의 보고서만 처리")
    parser.add_argument("--report", help="특정 보고서 파일만 처리")

    args = parser.parse_args()

    async with app.run() as parallel_app:
        logger = parallel_app.logger

        # 특정 보고서만 처리
        if args.report:
            report_path = args.report
            if not os.path.exists(report_path):
                logger.error(f"지정된 보고서 파일이 존재하지 않습니다: {report_path}")
                return

            generator = TelegramSummaryGenerator()
            telegram_message = await generator.process_report(report_path, args.output_dir)

            # 생성된 메시지 출력
            print("\n생성된 텔레그램 메시지:")
            print("-" * 50)
            print(telegram_message)
            print("-" * 50)

        else:
            # 오늘 날짜 필터 적용
            date_filter = None
            if args.today:
                date_filter = datetime.now().strftime("%Y%m%d")
            elif args.date:
                date_filter = args.date

            # 모든 보고서 처리
            await process_all_reports(
                reports_dir=args.reports_dir,
                output_dir=args.output_dir,
                date_filter=date_filter
            )

if __name__ == "__main__":
    asyncio.run(main())