import os
import json
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import logging
import sys

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

load_dotenv(os.path.join(os.getenv('CONFIG_DIR', 'config'), '.env'))

APP_KEY = os.getenv('APP_KEY')
APP_SECRET = os.getenv('APP_SECRET')
ACCESS_TOKEN = None
URL_BASE = "https://openapi.koreainvestment.com:9443"


# -------------------------------------------------
def load_token():
    """ API Token 을 가져온다. """
    try:
        token_path = os.path.join(os.getenv('CONFIG_DIR', 'config'),
                                  'token.json')
        with open(token_path, 'r') as f:
            token_data = json.load(f)

        if token_data['issued_time'] == "" or token_data['access_token'] == "":
            return None

        issued_time = datetime.fromisoformat(token_data['issued_time'])
        current_time = datetime.now()

        if current_time - issued_time < timedelta(hours=23):
            return token_data['access_token']
        return None
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


# -------------------------------------------------
def save_token(access_token):
    """ API Token 을 저장한다. """
    token_data = {
        'access_token': access_token,
        'issued_time': datetime.now().isoformat()
    }
    token_path = os.path.join(os.getenv('CONFIG_DIR', 'config'), 'token.json')
    with open(token_path, 'w') as f:
        json.dump(token_data, f)
    logger.info("새로운 토큰이 저장되었습니다.")


# -------------------------------------------------
def auth():
    """
        access_token을 발급받는다.
        한국투자증권 API access token은 24시간 유효한 토큰임.  
    """

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
    """ 주식 가격정보를 가져온다. """

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

    params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": stock_no}

    res = requests.get(URL, headers=headers, params=params)

    if res.status_code == 200 and res.json()["rt_cd"] == "0":
        data = res.json()["output"]
        result = {
            "stock_code": data["stck_shrn_iscd"],  # 종목코드
            "stock_name": stock_name,  # 종목명
            "current_price": int(data["stck_prpr"]),  # 현재가
            "price_diff": int(data["prdy_vrss"]),  # 전일대비
            "change_rate": float(data["prdy_ctrt"]),  # 등락률
            "volume": int(data["acml_vol"]),  # 거래량
            "trading_value": int(data["acml_tr_pbmn"]),  # 거래대금
            "opening_price": int(data["stck_oprc"]),  # 시가
            "high_price": int(data["stck_hgpr"]),  # 고가
            "low_price": int(data["stck_lwpr"]),  # 저가
        }
        return result

    # res.status_code == 500 경우도 있어 아래와 같이 수정함.
    # 기존 코드 : res.status_code == 200 and res.json()["msg_cd"] == "EGW00123":
    elif res.json()["msg_cd"] == "EGW00123":
        auth()
        return get_current_price(stock_no)
    else:
        logger.error("Error Code : " + str(res.status_code) + " | " + res.text)
        return None


# -------------------------------------------------
if __name__ == "__main__":
    result = get_current_price("012450", "한화에어로스페이스")

    if result:
        for key, value in result.items():
            if key == 'change_rate':
                print(f"{key:<15}: {value:>10.2f}")
            elif isinstance(value, int):
                print(f"{key:<15}: {value:>10,d}")
            else:
                print(f"{key:<15}: {value:>10}")
