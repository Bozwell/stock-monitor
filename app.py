import os
import logging

import pytz
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from influxdb_client import InfluxDBClient, Point
from time import sleep
from tinydb import TinyDB
from kis_api import get_current_price
from utils import load_stocks, check_krx_market_time

from rich.logging import RichHandler
from rich.console import Console
from rich.theme import Theme


# 커스터마이징 
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "critical": "red reverse"
})

console = Console(theme=custom_theme)
rich_handler = RichHandler(
    console=console,
    rich_tracebacks=True,
    tracebacks_show_locals=True,
    show_time=True,
    show_path=False
)

# 기본 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[rich_handler]
)

# 로거 가져오기
logger = logging.getLogger(__name__)

# APScheduler 로거 설정
apscheduler_logger = logging.getLogger('apscheduler')
apscheduler_logger.setLevel(logging.ERROR)
apscheduler_logger.handlers = []  # 기존 핸들러 제거
apscheduler_logger.addHandler(rich_handler)

# .env 파일 로드
load_dotenv(os.path.join(os.getenv('CONFIG_DIR', 'config'), '.env'))

# TinyDB
db_path = os.path.join(os.getenv('CONFIG_DIR', 'config'), 'db.json')
db = TinyDB(db_path)



# -------------------------------------------------
def main():
    if not check_krx_market_time():
        logger.info("장 운영 시간이 아닙니다.")
        return

    logger.info("-------------------------------------------------")
    try:
        stock_list = load_stocks()
        logger.info(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 주식 시세 조회 시작")

        # InfluxDB 클라이언트 설정
        client = InfluxDBClient(url=os.getenv('INFLUXDB_URL'),
                                token=os.getenv('INFLUXDB_TOKEN'),
                                org=os.getenv('INFLUXDB_ORG'))
        write_api = client.write_api()

        for stock in stock_list:
            try:
                result = get_current_price(stock['code'], stock['name'])
                sleep(0.2)  #초당 거래건수 대응 딜레이

                if result:
                    logger.info(
                        f"종목명: {stock['name']}, 종목코드: {stock['code']} 시세 저장 중...")
                    # InfluxDB에 데이터 저장
                    point = Point("stock_price") \
                        .tag("code", stock['code']) \
                        .tag("name", stock['name'])

                    for key, value in result.items():
                        if isinstance(value, (int, float)):
                            point = point.field(key, value)

                    write_api.write(bucket=os.getenv('INFLUXDB_BUCKET'),
                                    record=point)
                    change_rate = result.get("change_rate", 0)
                    logger.info(
                        f"종목명: {stock['name']}, 현재가:{result['current_price']}원, 등락률: {change_rate}%  데이터 저장 완료"
                    )
            except Exception as e:
                logger.error(f"Error checking {stock['name']}: {str(e)}")

        write_api.close()
        client.close()

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")   
    finally:
        if write_api:
            write_api.close()
        if client:
            client.close()


# -------------------------------------------------
if __name__ == "__main__":
    scheduler = BlockingScheduler()

    # 매시 정각에 실행 (9:00 ~ 15:00)
    trigger = CronTrigger(
        day_of_week='mon-fri',  # 월요일부터 금요일까지
        hour='9-15',  # 9시부터 15시까지
        minute='*/1',  # 1분마다
        timezone=pytz.timezone('Asia/Seoul'))

    scheduler.add_job(main, trigger=trigger)

    logger.info("주식 시세 모니터링 시작...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('프로그램을 종료합니다.')
