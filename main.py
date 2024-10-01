from config import *
from src.core.controller import Controller
from src.core.logger import logger, MongoDBHandler
from src.core.db import State
from src.strategy.rebalance import RebalanceSingleStrategy
from src.signal.rebalance.golden_cross import GoldenCross
from src.signal.rebalance.qqsm import QuantizedQuantileStateMaximization
from traceback import format_exc



if mongo_client:
    mongo_client.admin.command('ping')
    mongo_handler = MongoDBHandler(db['log'])
    logger.addHandler(mongo_handler)
    logger.info("Database connection OK")




def main():
    try:
        signal = QuantizedQuantileStateMaximization(INDICATOR_CONFIG)
        # signal = GoldenCross(INDICATOR_CONFIG)
        strategy = RebalanceSingleStrategy(ex=ex,
                                        symbol=SYMBOL,
                                        timeframe=TIMEFRAME,
                                        fraction=signal,
                                        live=LIVE_TRADE)
        state = State(db)
        controller = Controller(TICK_SCHEDULE,
                                { 'strategy': strategy },
                                state)
    except Exception as e:
        logger.error(format_exc())
        raise e
    controller.start()


if __name__ == '__main__':
    main()
