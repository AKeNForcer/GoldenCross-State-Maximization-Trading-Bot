from unittest import TestCase
from unittest.mock import patch
from .config import *
from .controller import MockController
from src.core.logger import logger, MongoDBHandler
from src.signal.rebalance.qqsm import QuantizedQuantileStateMaximization
from src.strategy.rebalance import RebalanceSingleStrategy
from src.core.db import State
from traceback import format_exc






class TestQqsmRebalanceStrategy(TestCase):

    @patch('src.core.time.mockable_current_datetime')
    def test_backtest(self, mock_current_datetime):
        # mdtc = self.mock_current_datetime()
        # mdtc.set_time((start_date - pd.to_timedelta(TIMEFRAME)).to_pydatetime())
        mock_current_datetime.return_value = (start_date - pd.to_timedelta(TIMEFRAME)).to_pydatetime()

        if mongo_client:
            mongo_client.admin.command('ping')
            mongo_handler = MongoDBHandler(db['log'])
            logger.addHandler(mongo_handler)
            logger.info("Database connection OK")
        
        try:
            signal = QuantizedQuantileStateMaximization(INDICATOR_CONFIG)
            strategy = RebalanceSingleStrategy(ex=ex,
                                               symbol=SYMBOL,
                                               timeframe=TIMEFRAME,
                                               fraction=signal,
                                               live=LIVE_TRADE)
            state = State(db).sub_state(test_name)
            controller = MockController({ 'strategy': strategy },
                                        state)
        except Exception as e:
            logger.error(format_exc())
            raise e

        for date in pd.date_range(start_date, end_date,
                                  freq=pd.to_timedelta(TIMEFRAME)):
            # mdtc.set_time(date.to_pydatetime())
            mock_current_datetime.return_value = date.to_pydatetime()
            strategy.get_klines(1 if strategy.dt.cache is None else len(strategy.dt.cache))
            lastest_klines = strategy.dt.cache.iloc[-1]
            logger.info(f'current datetime: {date}')
            ex.__tick__(lastest_klines['close'],
                        lastest_klines['high'],
                        lastest_klines['low'])
            controller.tick()

