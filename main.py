from config import *
from src.core.controller import Controller
from src.core.logger import logger, MongoDBHandler
from src.core.db import State
from src.strategy.rebalance import RebalanceSingleStrategy
from src.signal.rebalance.golden_cross import GoldenCross



if mongo_client:
    mongo_client.admin.command('ping')
    mongo_handler = MongoDBHandler(db['log'])
    logger.addHandler(mongo_handler)
    logger.info("Database connection OK")




def main():
    signal = GoldenCross(INDICATOR_CONFIG)
    strategy = RebalanceSingleStrategy(ex=ex,
                                       symbol=SYMBOL,
                                       timeframe=TIMEFRAME,
                                       fraction=signal,
                                       live=LIVE_TRADE)
    state = State(db)
    controller = Controller(TICK_SCHEDULE,
                            { 'strategy': strategy },
                            state)
    controller.start()


if __name__ == '__main__':
    main()
