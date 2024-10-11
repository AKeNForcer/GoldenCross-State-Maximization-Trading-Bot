import pandas as pd
import numpy as np
from datetime import datetime
from ccxt import Exchange
from src.core.db import State
from src.strategy.base import BaseStrategy
from src.core.data import DataBroker
from src.signal.rebalance.base import RebalanceSignal
from src.core.logger import logger
from src.utils.calc import calc_precision
from src.core.time import current_datetime
from time import sleep





class RebalanceSingleStrategy(BaseStrategy):
    def __init__(self, ex: Exchange,
                 symbol: str,
                 timeframe: str,
                 fraction: RebalanceSignal | float,
                 name: str = 'rebalance-single',
                 live: bool = False):
        super().__init__(ex, name)
        self.live = live
        self.dt = DataBroker(ex, symbol, timeframe)
        self.symbol = symbol
        self.market_info = self.ex.load_markets()[self.symbol]
        self.base = self.market_info['base']
        self.quote = self.market_info['quote']
        self.trading_fee = self.market_info['taker']
        self.base_precision = self.market_info['precision']['amount']
        self.price_precision = self.market_info['precision']['price']
        self.min_trade_base = self.market_info['limits']['amount']['min']
        self.timeframe = timeframe
        self.tfdelta = pd.to_timedelta(self.timeframe)

        self.fraction = fraction

        logger.info(f'live trade: {self.live}')
        logger.info(f'symbol: {self.symbol}')
        logger.info(f'base: {self.base}')
        logger.info(f'quote: {self.quote}')
        logger.info(f'timeframe: {self.timeframe}')
        logger.info(f'initial balance: {self.ex.fetch_balance()["total"]}')
    

    def inject_state(self, state: State):
        super().inject_state(state)
        self.state.load('tick')
        self.fraction.inject_state(state.sub_state('signal'))
        self.fraction.inject_strategy(self)
    

    def _fetch_account_balance(self):
        self.last_price = self.data.iloc[-1]['close']
        self.balance = self.ex.fetch_balance()['total']
        self.quote_bal = self.balance.get(self.quote) or 0
        self.base_bal = self.balance.get(self.base) or 0
        self.equity = self.quote_bal + self.base_bal * self.last_price


    def _rebalance(self, now: datetime, frac: float):
        quote_invest = self.equity * frac
        base_invest = quote_invest / self.last_price

        diff_base = base_invest - self.base_bal
        diff_base = calc_precision(diff_base,
                                   self.base_precision,
                                   np.floor if diff_base > 0 else np.ceil)
        
        if np.abs(diff_base) < self.min_trade_base:
            diff_base = 0
        
        
        response = dict(
            time=now,
            fraction=frac,
            quote_bal=self.quote_bal,
            base_bal=self.base_bal,
            equity=self.equity,
            quote_invest=quote_invest,
            base_invest=base_invest,
            diff_base=diff_base,
            side=None,
            final_quote_bal=self.quote_bal,
            final_base_bal=self.base_bal,
            final_equity=self.equity,
            traded=False,
            order=None
        )

        if diff_base == 0:
            return response

        side = 'buy' if diff_base > 0 else 'sell'
        diff_base = np.abs(diff_base)

        logger.info(f'rebalancing: {diff_base} {self.base}')
        if self.live:
            _res = self.ex.create_order(self.symbol, 'market', side, diff_base)
        else:
            logger.info(f'rebalancing rejected: not in live mode')
            _res = None

        if _res is not None:
            logger.info(f'awaiting order...')
            while True:
                o = self.ex.fetch_order(_res['id'], self.symbol)
                if o['status'] != 'closed':
                    sleep(1)
                    continue
                res = o
                break
            logger.info(f'order filled!')
        else:
            res = None
        
        old_equity = self.equity
        self._fetch_account_balance()
        
        response['final_quote_bal'] = self.quote_bal
        response['final_base_bal'] = self.base_bal
        # try:
        response['final_equity'] = \
            self.quote_bal + self.base_bal * res['price'] if res else old_equity
        # except Exception as e:
        #     print(res)
        #     print(self.quote_bal + self.base_bal, res['price'], old_equity)
        #     raise e
        response['traded'] = res is not None
        response['order'] = res
        
        return response


    def get_current_kline(self):
        return self.dt.get(1)
    

    def get_klines(self, limit=None, now=None):
        return self.dt.get(last=(now or current_datetime()) - self.tfdelta,
                           limit=limit)


    def tick(self, now: datetime):
        if type(self.fraction) in [float, int]:
            self.data = self.get_current_kline()
            self._fetch_account_balance()

            self._rebalance(now, self.fraction, self.last_price)
            return

        limit = self.fraction.get_length()
        if type(limit) != int:
            limit = int(limit / self.tfdelta)

        self.data = self.get_klines(limit=limit)
        self._fetch_account_balance()

        frac = self.fraction.tick(now, self.data)
        res = self._rebalance(now, frac)

        return frac, res
    

    
    def post_tick(self, now: datetime, payload):
        frac, res = payload

        if self.state:
            self.state['tick'] = res
        
        logger.info('rebalance done')
        logger.info(f'kline start: {self.data.index[0]}')
        logger.info(f'kline last: {self.data.index[-1]}')
        logger.info(f'fraction: {frac}')
        logger.info(f'diff_base: {res["diff_base"]}')
        logger.info(f'final_base_bal: {res["final_base_bal"]}')
        logger.info(f'final_quote_bal: {res["final_quote_bal"]}')
        logger.info(f'final_equity: {res["final_equity"]}')
        logger.info(f'traded: {res["traded"]}')

        self.fraction.post_tick(now)

