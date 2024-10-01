import os
from dotenv import load_dotenv
import pandas as pd
import ccxt
import pymongo
from pymongo.server_api import ServerApi
from src.core.timeframe import tf_to_resample


LIVE_TRADE = False


load_dotenv()

DB_CONN = os.environ.get('DB_CONN')
DB_NAME = os.environ.get('DB_NAME')

API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
API_PASS = os.environ.get('API_PASS')


SYMBOL = 'BTC/USDT'

TIMEFRAME = '1m'
TICK_SCHEDULE = { 'second': 0 }

# TIMEFRAME = '1d'
# TICK_SCHEDULE = { 'hour': 0, 'minute': 0, 'second': 0 }




INDICATOR_CONFIG = {
    'trade_freq': pd.to_timedelta(tf_to_resample(TIMEFRAME)),
    'state_target': ['close'],
    'lookback': [90],
    'qt_length': [90],
    'qt_steps': [3, 5],
    'chain_length': [7],
    'forward_length': [3],
    'fee_adj': [1.5, 2, 2.5],
    'opt_range': 365,
    'opt_freq': 61,
}

if DB_CONN:
    mongo_client = pymongo.MongoClient(DB_CONN, server_api=ServerApi('1'))
else:
    mongo_client = None

if DB_NAME and mongo_client:
    db = mongo_client[DB_NAME]
else:
    db = None


ex = ccxt.okx({
    'apiKey': API_KEY,         # Replace with your actual API key
    'secret': API_SECRET,      # Replace with your actual Secret key
    'password': API_PASS,
    'enableRateLimit': True,          # Enable rate limit handling by CCXT
})
