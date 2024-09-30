import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ccxt import Exchange
from pymongo.database import Database
from src.core.controller import Syncronizable
from src.core.db import State
from src.strategy.base import BaseStrategy
from src.core.data import DataBroker
from src.signal.rebalance.base import RebalanceSignal
from src.core.logger import logger
from src.utils.calc import calc_precision
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
        self.market_info = self.ex.load_markets()['BTC/USDT']
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
    

    def _rebalance(self, now: datetime, frac: float, last_price: float):
        balance = self.ex.fetch_balance()['total']
        quote_bal = balance.get(self.quote) or 0
        base_bal = balance.get(self.base) or 0
        equity = quote_bal + base_bal * last_price
        quote_invest = equity * frac
        base_invest = quote_invest / last_price

        diff_base = calc_precision(base_invest - base_bal,
                                    self.base_precision,
                                    np.floor)
        if np.abs(diff_base) < self.min_trade_base:
            diff_base = 0
        
        
        if diff_base == 0:
            return dict(
                time=now,
                fraction=frac,
                quote_bal=quote_bal,
                base_bal=base_bal,
                equity=equity,
                quote_invest=quote_invest,
                base_invest=base_invest,
                diff_base=diff_base,
                side=None,
                final_quote_bal=quote_bal,
                final_base_bal=base_bal,
                final_equity=equity,
                traded=False,
                order=None
            )

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
        
        final_balance = self.ex.fetch_balance()['total']
        final_quote_bal = final_balance.get(self.quote) or 0
        final_base_bal = final_balance.get(self.base) or 0

        return dict(
            time=now,
            fraction=frac,
            base_bal=base_bal,
            quote_bal=quote_bal,
            equity=equity,
            base_invest=base_invest,
            quote_invest=quote_invest,
            diff_base=diff_base,
            side=side,
            final_quote_bal=final_quote_bal,
            final_base_bal=final_base_bal,
            final_equity=final_quote_bal + \
                final_base_bal * res['price'] \
                    if res else equity,
            traded=res is not None,
            order=res
        )



    def tick(self, now: datetime):
        if type(self.fraction) == float:
            data = self.dt.get(1)
            self._rebalance(now, self.fraction, data.iloc[-1]['close'])
            return

        limit = self.fraction.get_length()
        if type(limit) != int:
            limit = int(limit / self.tfdelta)
        data = self.dt.get(last=datetime.now() - self.tfdelta, limit=limit)

        frac = self.fraction.get(now, data)
        res = self._rebalance(now, frac, data.iloc[-1]['close'])

        return frac, res
    

    
    def post_tick(self, now: datetime, payload):
        frac, res = payload

        if self.state:
            self.state['tick'] = res
        
        logger.info('rebalance done')
        logger.info(f'fraction: {frac}')
        logger.info(f'diff_base: {res["diff_base"]}')
        logger.info(f'final_base_bal: {res["final_base_bal"]}')
        logger.info(f'final_quote_bal: {res["final_quote_bal"]}')
        logger.info(f'final_equity: {res["final_equity"]}')
        logger.info(f'traded: {res["traded"]}')

