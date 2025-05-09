import pytest
import os,sys
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from tinydb import TinyDB

# 상위 디렉토리를 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kis_api import (
    load_token, 
    save_token, 
    auth, 
    get_current_price
)

# 테스트용 환경 변수 설정
@pytest.fixture(autouse=True)
def setup_env():
    # 테스트 환경 변수 설정
    os.environ['APP_KEY'] = 'test_app_key'
    os.environ['APP_SECRET'] = 'test_app_secret'
    os.environ['CANO'] = '12345678'
    os.environ['ACNT_PRDT_CD'] = '01'
    os.environ['CONFIG_DIR'] = 'test_config'
    
    # 테스트 디렉토리 생성
    os.makedirs('test_config', exist_ok=True)
    
    # 테스트 전에 db.json 파일이 있다면 삭제
    if os.path.exists('test_config/db.json'):
        os.remove('test_config/db.json')
    
    yield
    
    # 테스트 후 정리
    if os.path.exists('test_config/db.json'):
        os.remove('test_config/db.json')
    if os.path.exists('test_config'):
        os.rmdir('test_config')

# 토큰 관련 테스트
def test_load_token_no_token():
    """토큰이 없는 경우 테스트"""
    result = load_token()
    assert result is None

def test_save_token():
    """토큰 저장 테스트"""
    with patch('kis_api.datetime') as mock_datetime:
        # 현재 시간 설정
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.fromisoformat.return_value = mock_now
        
        save_token('test_token')
        
        # TinyDB에서 직접 토큰 확인
        db = TinyDB('test_config/db.json')
        token_table = db.table('token')
        token_data = token_table.all()[-1] if token_table.all() else None
        db.close()
        
        assert token_data is not None
        assert token_data['access_token'] == 'test_token'
        assert token_data['issued_time'] == mock_now.isoformat()

# 인증 관련 테스트
@patch('kis_api.requests.post')
def test_auth_success(mock_post):
    """인증 성공 테스트"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'access_token': 'test_token'}
    mock_post.return_value = mock_response
    
    auth()
    
    # TinyDB에서 직접 토큰 확인
    db = TinyDB('test_config/db.json')
    token_table = db.table('token')
    token_data = token_table.all()[-1] if token_table.all() else None
    db.close()
    
    assert token_data is not None
    assert token_data['access_token'] == 'test_token'

@patch('kis_api.requests.post')
def test_auth_failure(mock_post):
    """인증 실패 테스트"""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_post.return_value = mock_response
    
    with pytest.raises(Exception) as exc_info:
        auth()
    assert str(exc_info.value) == '인증 실패'

# 주식 시세 조회 테스트
@patch('kis_api.requests.get')
def test_get_current_price_success(mock_get):
    """주식 시세 조회 성공 테스트"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'rt_cd': '0',
        'output': {
            'stck_shrn_iscd': '005930',
            'stck_prpr': '70000',
            'prdy_vrss': '1000',
            'prdy_ctrt': '1.45',
            'acml_vol': '1000000',
            'acml_tr_pbmn': '70000000000',
            'stck_oprc': '69000',
            'stck_hgpr': '71000',
            'stck_lwpr': '68000'
        }
    }
    mock_get.return_value = mock_response
    
    with patch('kis_api.load_token', return_value='test_token'):
        result = get_current_price('005930', '삼성전자')
        
        assert result is not None
        assert result['stock_code'] == '005930'
        assert result['current_price'] == 70000
        assert result['price_diff'] == 1000
        assert result['change_rate'] == 1.45


