from unittest.mock import patch
from backtest.config import *
from backtest.controller import MockController
from src.core.logger import logger, MongoDBHandler
from src.signal.rebalance.gcsm import GoldenCrossStateMaximization
from src.strategy.rebalance import RebalanceSingleStrategy
from src.core.db import State
from traceback import format_exc




if __name__ == '__main__':
    with patch('src.core.time.mockable_current_datetime') as mock_current_datetime:
        mock_current_datetime.return_value = (start_date - pd.to_timedelta(TIMEFRAME)).to_pydatetime()
        logger.info(f'##### current datetime: {mock_current_datetime.return_value}')

        if mongo_client:
            mongo_client.admin.command('ping')
            mongo_handler = MongoDBHandler(db['log'])
            logger.addHandler(mongo_handler)
            logger.info("Database connection OK")
        
        try:
            signal = GoldenCrossStateMaximization(**INDICATOR_CONFIG)
            strategy = RebalanceSingleStrategy(ex=ex,
                                               symbol=SYMBOL,
                                               timeframe=TIMEFRAME,
                                               fraction=signal,
                                               live=LIVE_TRADE)
            state = State(db).sub_state(test_name)
            controller = MockController({ 'strategy': strategy }, state)
        except Exception as e:
            logger.error(format_exc())
            raise e

        for date in pd.date_range(start_date, end_date,
                                  freq=pd.to_timedelta(TIMEFRAME)):
            mock_current_datetime.return_value = date.to_pydatetime()
            logger.info(f'##### current datetime: {date}')
            strategy.dt.get_klines(max(len(strategy.dt.cache), 1))
            lastest_klines = strategy.dt.cache.iloc[-1]
            ex.__tick__(lastest_klines['close'],
                        lastest_klines['high'],
                        lastest_klines['low'])
            controller.tick()




