import os
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import ccxt
import pymongo
from pymongo.server_api import ServerApi



load_dotenv()


LIVE_TRADE = os.environ.get('LIVE_TRADE') in [True, 'true', 'True', '1', 1]


DB_CONN = os.environ.get('DB_CONN')
DB_NAME = os.environ.get('DB_NAME')

API_KEY = os.environ.get('API_KEY')
API_SECRET = os.environ.get('API_SECRET')
API_PASS = os.environ.get('API_PASS')


SYMBOL = 'BTC/USDT'


TIMEFRAME = '1d'
TICK_SCHEDULE = { 'hour': 0, 'minute': 0, 'second': 0 }




INDICATOR_CONFIG = {
    'config': {
        'trade_freq': pd.to_timedelta(TIMEFRAME),
        'lookback': list(np.arange(115, 126, 1)),
        'forward_length': [1],
        'fee_adj': [1],
        'opt_range': 365+152,
        'opt_freq': 91,
        'optimize_ref_date': pd.to_datetime('2023-01-01')
    },
    'kline_state_config': {
        'state_target': ['close'],
        'ema_fast_length': [12],
        'ema_slow_length': [26],
    }
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
