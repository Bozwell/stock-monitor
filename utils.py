import os
import pytz
import json
import datetime
import logging
from dotenv import load_dotenv
from tinydb import TinyDB

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

# .env 파일 로드
load_dotenv(os.path.join(os.getenv('CONFIG_DIR', 'config'), '.env'))

# TinyDB
db = TinyDB(os.path.join(os.getenv('CONFIG_DIR', 'config'), 'db.json'))


# -------------------------------------------------
def check_krx_market_time():
    # 한국 시간대 설정
    korea_tz = pytz.timezone('Asia/Seoul')
    current_time = datetime.datetime.now(korea_tz)

    # 주중인지 확인 (0 = 월요일, 6 = 일요일)
    if current_time.weekday() >= 5:  # 주말이면 실행하지 않음
        return False

    # 시간이 9:00 ~ 15:30 사이인지 확인
    market_start = current_time.replace(hour=9,
                                        minute=0,
                                        second=0,
                                        microsecond=0)
    market_end = current_time.replace(hour=15,
                                      minute=30,
                                      second=0,
                                      microsecond=0)

    return market_start <= current_time <= market_end


# -------------------------------------------------
def load_stocks():
    """
    주식 데이터를 로드하는 함수.
    먼저 JSON 파일에서 로드하고, 없으면 TinyDB에서 로드합니다.
    
    Returns:
        list: 주식 데이터 리스트
    """
    config_dir = os.getenv('CONFIG_DIR', 'config')
    json_path = os.path.join(config_dir, 'stocks.json')
    
    # JSON 파일에서 로드 시도
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON 파일 로드 실패: {e}")
    
    # TinyDB에서 로드 시도
    try:
        # 테스트 환경에서는 직접 TinyDB 인스턴스를 생성
        if config_dir == 'test_config':
            test_db = TinyDB(os.path.join(config_dir, 'db.json'))
            stocks_table = test_db.table('stocks')
            result = stocks_table.all()
            test_db.close()
            return result
        else:
            stocks_table = db.table('stocks')
            return stocks_table.all()
    except Exception as e:
        logger.error(f"TinyDB 로드 실패: {e}")
    
    return []

# -------------------------------------------------
def save_stocks(stocks):
    """
    주식 데이터를 저장하는 함수.
    JSON 파일과 TinyDB 모두에 저장합니다.
    
    Args:
        stocks (list): 저장할 주식 데이터 리스트
    """
    config_dir = os.getenv('CONFIG_DIR', 'config')
    json_path = os.path.join(config_dir, 'stocks.json')
    
    # JSON 파일에 저장
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"JSON 파일 저장 실패: {e}")
    
    # TinyDB에 저장
    try:
        # 테스트 환경에서는 직접 TinyDB 인스턴스를 생성
        if config_dir == 'test_config':
            test_db = TinyDB(os.path.join(config_dir, 'db.json'))
            stocks_table = test_db.table('stocks')
            stocks_table.truncate()  # 기존 데이터 삭제
            stocks_table.insert_multiple(stocks)
            test_db.close()
        else:
            stocks_table = db.table('stocks')
            stocks_table.truncate()  # 기존 데이터 삭제
            stocks_table.insert_multiple(stocks)
    except Exception as e:
        logger.error(f"TinyDB 저장 실패: {e}")

# -------------------------------------------------
def get_stock_by_code(code):
    """
    종목코드로 주식 정보를 검색하는 함수.
    
    Args:
        code (str): 종목코드
        
    Returns:
        dict: 주식 정보 딕셔너리 또는 None
    """
    stocks = load_stocks()
    for stock in stocks:
        if stock.get('code') == code:
            return stock
    return None


# -------------------------------------------------
if __name__ == '__main__':
    get_stock_by_code_res = get_stock_by_code("012450")
    print(f"get_stock_by_code: {get_stock_by_code}")