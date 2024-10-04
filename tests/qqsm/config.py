from dotenv import load_dotenv, dotenv_values
import pandas as pd
import ccxt
import pymongo
from pymongo.server_api import ServerApi
from src.core.timeframe import tf_to_resample
from .ccxt import getMockCcxt

load_dotenv()
test_variables = dotenv_values('.env.test')





test_name = 'test-3'
DB_NAME = f"{test_variables.get('DB_NAME')}-3"

start_date = pd.to_datetime('2019-01-01')
end_date = pd.to_datetime('2023-01-01')

fee = 0.1/100
start_equity = 10_000





LIVE_TRADE = True

DB_CONN = test_variables.get('DB_CONN')

API_KEY = test_variables.get('API_KEY')
API_SECRET = test_variables.get('API_SECRET')
API_PASS = test_variables.get('API_PASS')


SYMBOL = 'BTC/USDT'

TIMEFRAME = '1d'



INDICATOR_CONFIG = {
    'trade_freq': pd.to_timedelta(TIMEFRAME),
    'state_target': ['close'],
    'lookback': [90],
    'qt_length': [90],
    'qt_steps': [3],
    'chain_length': [7],
    'forward_length': [3],
    'fee_adj': [2],
    'opt_range': 120,
    'opt_freq': 61
}
# INDICATOR_CONFIG = {
#     'trade_freq': pd.to_timedelta(TIMEFRAME),
#     'state_target': ['close'],
#     'lookback': [90],
#     'qt_length': [90],
#     'qt_steps': [3, 5],
#     'chain_length': [7],
#     'forward_length': [3],
#     'fee_adj': [1.5, 2, 2.5],
#     'opt_range': 365,
#     'opt_freq': 61,
# }

if DB_CONN:
    mongo_client = pymongo.MongoClient(DB_CONN, server_api=ServerApi('1'))
else:
    mongo_client = None

if DB_NAME and mongo_client:
    # mongo_client.drop_database(DB_NAME)
    db = mongo_client[DB_NAME]
else:
    db = None


ex = getMockCcxt(ccxt.okx, { 'USDT': 100_000, 'BTC': 0 }, db, {
    'apiKey': API_KEY,         # Replace with your actual API key
    'secret': API_SECRET,      # Replace with your actual Secret key
    'password': API_PASS,
    'enableRateLimit': True,          # Enable rate limit handling by CCXT
})

