import pytest
import os,sys
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from tinydb import TinyDB, Query

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import load_stocks, save_stocks, get_stock_by_code

# 테스트용 환경 변수 설정
@pytest.fixture(autouse=True)
def setup_env():
    os.environ['CONFIG_DIR'] = 'test_config'
    # 테스트용 디렉토리 생성
    os.makedirs('test_config', exist_ok=True)
    yield
    # 테스트 후 정리
    if os.path.exists('test_config/stocks.json'):
        os.remove('test_config/stocks.json')
    if os.path.exists('test_config/db.json'):
        os.remove('test_config/db.json')
    if os.path.exists('test_config'):
        os.rmdir('test_config')

# 테스트용 주식 데이터
@pytest.fixture
def sample_stocks():
    return [
        {"name": "삼성전자", "code": "005930"},
        {"name": "SK하이닉스", "code": "000660"},
        {"name": "NAVER", "code": "035420"}
    ]

# 주식 데이터 로드 테스트
def test_load_stocks_from_json(sample_stocks):
    """JSON 파일에서 주식 데이터 로드 테스트"""
    # 테스트용 JSON 파일 생성
    with open('test_config/stocks.json', 'w', encoding='utf-8') as f:
        json.dump(sample_stocks, f, ensure_ascii=False, indent=4)
    
    # 데이터 로드
    result = load_stocks()
    
    assert result == sample_stocks

def test_load_stocks_from_tinydb(sample_stocks):
    """TinyDB에서 주식 데이터 로드 테스트"""
    # TinyDB에 데이터 저장
    db = TinyDB('test_config/db.json')
    stocks_table = db.table('stocks')
    stocks_table.insert_multiple(sample_stocks)
    db.close()
    
    # 데이터 로드
    result = load_stocks()
    
    assert result == sample_stocks

def test_load_stocks_empty():
    """주식 데이터가 없는 경우 테스트"""
    result = load_stocks()
    assert result == []

# 주식 데이터 저장 테스트
def test_save_stocks(sample_stocks):
    """주식 데이터 저장 테스트"""
    # 데이터 저장
    save_stocks(sample_stocks)
    
    # 저장된 데이터 확인
    result = load_stocks()
    assert result == sample_stocks

# 종목코드로 주식 검색 테스트
def test_get_stock_by_code(sample_stocks):
    """종목코드로 주식 검색 테스트"""
    # 데이터 저장
    save_stocks(sample_stocks)
    
    # 종목코드로 검색
    result = get_stock_by_code("005930")
    assert result == {"name": "삼성전자", "code": "005930"}
    
    # 존재하지 않는 종목코드 검색
    result = get_stock_by_code("999999")
    assert result is None
