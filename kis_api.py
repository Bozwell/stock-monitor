import os
import json
import logging
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

# config 디렉토리의 .env 파일 로드
load_dotenv(os.path.join(os.getenv('CONFIG_DIR', 'config'), '.env'))

# TinyDB
db_path = os.path.join(os.getenv('CONFIG_DIR', 'config'), 'db.json')
db = TinyDB(db_path)

APP_KEY = os.getenv('APP_KEY')
APP_SECRET = os.getenv('APP_SECRET')
ACCESS_TOKEN = None
URL_BASE = "https://openapi.koreainvestment.com:9443"


# -------------------------------------------------
def load_token():
    # 테스트 환경에서는 항상 None 반환
    if os.getenv('CONFIG_DIR') == 'test_config':
        return None
        
    try:
        token_table = db.table('token')
        token_data = token_table.all()[-1] if token_table.all() else None

        if not token_data or token_data['issued_time'] == "" or token_data['access_token'] == "":
            return None

        issued_time = datetime.fromisoformat(token_data['issued_time'])
        current_time = datetime.now()

        if current_time - issued_time < timedelta(hours=23):
            return token_data['access_token']
        return None
    except (KeyError, json.JSONDecodeError):
        return None


# -------------------------------------------------
def save_token(access_token):
    token_data = {
        'access_token': access_token,
        'issued_time': datetime.now().isoformat()
    }
    
    # 테스트 환경에서는 직접 TinyDB 인스턴스를 생성
    if os.getenv('CONFIG_DIR') == 'test_config':
        test_db = TinyDB(os.path.join('test_config', 'db.json'))
        token_table = test_db.table('token')
        token_table.insert(token_data)
        test_db.close()
    else:
        token_table = db.table('token')
        token_table.insert(token_data)
    
    logger.info("새로운 토큰이 저장되었습니다.")


# -------------------------------------------------
def auth():
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"

    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }

    res = requests.post(URL, json=data)

    if res.status_code == 200:
        ACCESS_TOKEN = res.json()["access_token"]
        save_token(ACCESS_TOKEN)
    else:
        logger.error("Error Code : " + str(res.status_code) + " | " + res.text)
        raise Exception("인증 실패")


# -------------------------------------------------
def get_current_price(stock_no, stock_name):
    ACCESS_TOKEN = load_token()
    if ACCESS_TOKEN == None:
        auth()
        ACCESS_TOKEN = load_token()

    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"

    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "FHKST01010100"
    }

    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_INPUT_ISCD": stock_no
    }

    res = requests.get(URL, headers=headers, params=params)

    if res.status_code == 200:
        data = res.json()
        if data['rt_cd'] == '0':
            output = data['output']
            return {
                'stock_code': output['stck_shrn_iscd'],
                'stock_name': stock_name,
                'current_price': int(output['stck_prpr']),
                'price_diff': int(output['prdy_vrss']),
                'change_rate': float(output['prdy_ctrt']),
                'volume': int(output['acml_vol']),
                'trading_value': int(output['acml_tr_pbmn']),
                'open_price': int(output['stck_oprc']),
                'high_price': int(output['stck_hgpr']),
                'low_price': int(output['stck_lwpr'])
            }
        else:
            logger.error(f"Error Code : {data['rt_cd']} | {data['msg_cd']} | {data['msg1']}")
            return None
    else:
        logger.error("Error Code : " + str(res.status_code) + " | " + res.text)
        return None


# -------------------------------------------------
if __name__ == "__main__":
    result = get_current_price("012450", "한화에어로스페이스")
    print(type(result.get("change_rate")))

    if result:
        for key, value in result.items():
            if key == 'change_rate':
                print(f"{key:<15}: {value:>10.2f}")
            elif isinstance(value, int):
                print(f"{key:<15}: {value:>10,d}")
            else:
                print(f"{key:<15}: {value:>10}")
