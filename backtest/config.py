from dotenv import load_dotenv, dotenv_values
import pandas as pd
import ccxt
import pymongo
from pymongo.server_api import ServerApi
from src.core.timeframe import tf_to_resample
from .ccxt import getMockCcxt

load_dotenv()
test_variables = dotenv_values('.env.test')



test_i = 1

test_name = f'test-qqsm-{test_i}'
DB_NAME = f"{test_variables.get('DB_NAME')}-qqsm-{test_i}"
start_date = pd.to_datetime('2019-01-01')
end_date = pd.to_datetime('2023-01-01')


# test_name = f'test-qqsm-{test_i}-test'
# DB_NAME = f"{test_variables.get('DB_NAME')}-qqsm-{test_i}-test"
# start_date = pd.to_datetime('2023-01-01')
# end_date = pd.to_datetime('2024-10-01')



start_equity = 1_000





LIVE_TRADE = True

DB_CONN = test_variables.get('DB_CONN')

API_KEY = test_variables.get('API_KEY')
API_SECRET = test_variables.get('API_SECRET')
API_PASS = test_variables.get('API_PASS')


SYMBOL = 'BTC/USDT'

TIMEFRAME = '1d'



INDICATOR_CONFIG = {
    'config': {
        'trade_freq': pd.to_timedelta(TIMEFRAME),
        'lookback': [90],
        'forward_length': [3],
        'fee_adj': [1],
        'offset': [1],
        'opt_range': 190 + 182,
        'opt_freq': 91,
        'optimize': False
    },
    # 'config': {
    #     'trade_freq': pd.to_timedelta(TIMEFRAME),
    #     'lookback': [60, 75, 90],
    #     'forward_length': [3],
    #     'fee_adj': [1, 1.25, 1.5],
    #     'offset': [1],
    #     'opt_range': 190 + 182,
    #     'opt_freq': 91,
    # },
    'kline_state_config': {
        'state_target': ['close'],
        'qt_length': [90],
        'qt_steps': [3],
        'chain_length': [7],
    }
}


if DB_CONN:
    mongo_client = pymongo.MongoClient(DB_CONN, server_api=ServerApi('1'))
else:
    mongo_client = None

if DB_NAME and mongo_client:
    # mongo_client.drop_database(DB_NAME)
    db = mongo_client[DB_NAME]
else:
    db = None


ex = getMockCcxt(ccxt.okx, { 'USDT': start_equity, 'BTC': 0 }, db, {
    'apiKey': API_KEY,         # Replace with your actual API key
    'secret': API_SECRET,      # Replace with your actual Secret key
    'password': API_PASS,
    'enableRateLimit': True,          # Enable rate limit handling by CCXT
})

