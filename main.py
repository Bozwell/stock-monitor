import current_price   
from influxdb_client import InfluxDBClient, Point
import os
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
from current_price import get_current_price
import json
from time import sleep
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.getenv('CONFIG_DIR', 'config'), '.env'))

def load_stocks():
    stocks_path = os.path.join(os.getenv('CONFIG_DIR', 'config'), 'stocks.json')
    with open(stocks_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def check_krx_market_time():
    # 한국 시간대 설정
    korea_tz = pytz.timezone('Asia/Seoul')
    current_time = datetime.now(korea_tz)
    
    # 주중인지 확인 (0 = 월요일, 6 = 일요일)
    if current_time.weekday() >= 5:  # 주말이면 실행하지 않음
        return False
    
    # 시간이 9:00 ~ 15:30 사이인지 확인
    market_start = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
    market_end = current_time.replace(hour=15, minute=30, second=0, microsecond=0)
    
    return market_start <= current_time <= market_end

def main():
    if not check_krx_market_time():
        logger.info("장 운영 시간이 아닙니다.")
        return
    
    try:
        stock_list = load_stocks()
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 주식 시세 조회 시작")
        
        client = InfluxDBClient(
            url=os.getenv('INFLUXDB_URL'),
            token=os.getenv('INFLUXDB_TOKEN'),
            org=os.getenv('INFLUXDB_ORG')
        )
        write_api = client.write_api()
        
        for stock in stock_list:
            try:
                result = get_current_price(stock['code'], stock['name'])
                sleep(0.5) # ratelimit 대응 딜레이

                if result:
                    logger.info(f"{stock['name']} ({stock['code']}) 시세 저장 중...")
                    
                    point = Point("stock_price") \
                        .tag("code", stock['code']) \
                        .tag("name", stock['name'])
                    
                    for key, value in result.items():
                        if isinstance(value, (int, float)):
                            point = point.field(key, value)
                    
                    write_api.write(
                        bucket=os.getenv('INFLUXDB_BUCKET'),
                        record=point
                    )
                    logger.info(f"{stock['name']}, 현재가:{result['current_price']} 데이터 저장 완료")
            except Exception as e:
                logger.error(f"Error checking {stock['name']}: {str(e)}")

        client.close()
                
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        
if __name__ == "__main__":
    scheduler = BlockingScheduler()
    
    # 매시 정각에 실행 (9:00 ~ 15:00)
    trigger = CronTrigger(
        day_of_week='mon-fri',  # 월요일부터 금요일까지
        hour='9-15',           # 9시부터 15시까지
        minute='*/10',         # 10분마다
        timezone=pytz.timezone('Asia/Seoul')
    )
    
    scheduler.add_job(main, trigger=trigger)
    
    logger.info("주식 시세 모니터링 시작...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('프로그램을 종료합니다.')