from datetime import datetime, timedelta
from pydantic import BaseModel, conint, confloat, model_validator
from typing import Literal, List
import pandas as pd
import numpy as np
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed

from .base import RebalanceSignal
from src.core.db import State
from src.strategy.rebalance import RebalanceSingleStrategy
from src.core.logger import logger
from src.utils.backtest.runner import weight_trade_with_idx
from src.utils.backtest.data import make_time_window
from src.utils.backtest.em_weight import maximize_return_points








class QqsmConfig(BaseModel):
    trade_freq: timedelta
    state_target: List[Literal['close', 'ret']]
    lookback: List[conint(gt=1)]
    qt_length: List[conint(gt=1)]
    qt_steps: List[conint(gt=1)]
    chain_length: List[conint(gt=1)]
    forward_length: List[conint(gt=1)]
    fee_adj: List[confloat(gt=1)]
    buffer: confloat(gt=1)
    opt_range: conint(gt=1)
    opt_freq: conint(gt=1)
    save_opt_results: bool

    @model_validator(mode="after")
    def check_fields(self):
        for lookback, chain_length, forward_length in \
            product(self.lookback, self.chain_length, self.forward_length):
            if lookback < chain_length + forward_length:
                raise ValueError(
                    f'{lookback=} must be greater than or'
                    f'equal to {chain_length+forward_length=}'
                )
        
        for lookback in self.lookback:
            if self.opt_range <= lookback:
                raise ValueError(
                    f'{self.opt_range=} must be greater than or'
                    f'equal to {lookback=}'
                )

        return self









class GetWeightFn:
    def __init__(self, fee) -> None:
        self.fee = fee
    
    def _get_weight(self,
                    data: pd.DataFrame,
                    state_target: Literal['close', 'ret'],
                    lookback: int,
                    qt_length: int,
                    qt_steps: int,
                    chain_length: int,
                    forward_length: int,
                    fee_adj: int,
                    initial_w: float | None=None,
                    lastest_only=False):
        
        data = data.copy()
        data['ret'] = data['close'].pct_change().fillna(0)

        data['state'] = (data[state_target].rolling(qt_length).rank() * \
                        qt_steps / qt_length).round()
        state = make_time_window(data[['state']], ['state'], steps=chain_length, dropna=False)

        weight = pd.DataFrame(index=data.index)
        weight['weight'] = 0.0

        prev_w = initial_w or 0

        for i in range(len(data) - 1 if lastest_only else lookback, len(data)):
            idx = data.index[i]
            sel = data.index[i-lookback:i]

            st = state.loc[sel]
            window = data.loc[sel]
            
            st_sel_start = window.index[(st == st.iloc[-1]).all(axis=1)]
            st_sel_end = window.index.shift(forward_length)[(st == st.iloc[-1]).all(axis=1)]

            w_sel = pd.Series(np.full(len(window), False), index=window.index)

            for start, end in zip(st_sel_start, st_sel_end):
                w_sel[(w_sel.index >= start) & (w_sel.index < end)] = True

            window = window.loc[w_sel]
            ret = window['ret']

            w = maximize_return_points(ret,
                                       fee=self.fee * fee_adj,
                                       prev=prev_w)
            weight.loc[idx] = w
            prev_w = w

        data = data.join(weight)
        
        return data









class QuantizedQuantileStateMaximization(RebalanceSignal):
    
    # ===== Init part =====
    
    def __init__(self, config: dict) -> None:
        super().__init__()

        config['buffer'] = \
            config.get('buffer') or \
                int(max(*config['lookback'], *config['qt_length'],
                        *config['chain_length'], *config['forward_length']))
        config['save_opt_results'] = config.get('save_opt_results') or False

        self.config = QqsmConfig(**config)
    
    
    def get_config(self) -> dict:
        return self.config.model_dump()


    def inject_state(self, state: State):
        super().inject_state(state)
        self.state.load('state')
        self.state.load('params')
        if self.config.save_opt_results:
            self.state.load('opt_results')


    def inject_strategy(self, strategy: RebalanceSingleStrategy):
        super().inject_strategy(strategy)
        self.strategy: RebalanceSingleStrategy = strategy
        self.optimize(
            self.strategy.get_klines(self.config.opt_range),
            self.strategy.trading_fee,
            save=True
        )


    def get_length(self) -> int:
        return int(self.config.buffer + self.state['params']['qt_length'])



    # ===== Hyperparams Optimize part =====

    def _mp_opt(self, data: pd.DataFrame, fee: float):
        with ProcessPoolExecutor() as executor:
            futures = []
            
            for i, (
                state_target,
                lookback,
                qt_length,
                qt_steps,
                chain_length,
                forward_length,
                fee_adj,
            ) in enumerate(product(
                self.config.state_target,
                self.config.lookback,
                self.config.qt_length,
                self.config.qt_steps,
                self.config.chain_length,
                self.config.forward_length,
                self.config.fee_adj,
            )):
                params = dict(
                    state_target=state_target,
                    lookback=lookback,
                    qt_length=qt_length,
                    qt_steps=qt_steps,
                    chain_length=chain_length,
                    forward_length=forward_length,
                    fee_adj=fee_adj,
                )

                f = executor.submit(weight_trade_with_idx,
                                    params,
                                    data=data,
                                    get_weight=GetWeightFn(fee)._get_weight,
                                    get_weight_params=params,
                                    trade_freq=self.config.trade_freq,
                                    fee=fee,
                                    start_equity=10000)
                
                futures.append(f)

                results = []
                for f in as_completed(futures):
                    params, report = f.result()
                    results.append((params, report))
        
        return results


    def optimize(self, data: pd.DataFrame, fee: float,
                 now: datetime | None=None, force=False,
                 save=False):
        now = now or datetime.now()
        date = self.state['params'].get('date')
        
        if not force and date and \
            (now <= date + self.config.opt_freq * self.config.trade_freq):
            return
        
        logger.info(f'Params expired or not exists, starting optimization')
        logger.info(f'Optimize klines from {data.index[0]} to {data.index[-1]}')

        results = self._mp_opt(data, fee)
        params, _ = max(results, key=lambda x : -x[1]['Sharpe Ratio'])

        self.state['params'] = {
            'date': now,
            '_expected_expire': now + self.config.opt_freq * self.config.trade_freq,
            **params
        }
        if self.config.save_opt_results:
            self.state['opt_results'] = {
                'date': now,
                '_expected_expire': self.state['params']['_expected_expire'],
                'results': results
            }
        
        if save:
            self.state.save(now)

        logger.info(f"Optimize done!, best params is {self.state['params']}")



    # ===== Signal part =====

    def tick(self, now: datetime, data: pd.DataFrame) -> float:
        initial_frac = \
            self.strategy.base_bal * self.strategy.last_price \
            / self.strategy.equity
        
        params = self.state['params']

        data = GetWeightFn(self.strategy.trading_fee)._get_weight(
            data=data,
            state_target=params['state_target'],
            lookback=params['lookback'],
            qt_length=params['qt_length'],
            qt_steps=params['qt_steps'],
            chain_length=params['chain_length'],
            forward_length=params['forward_length'],
            fee_adj=params['fee_adj'],
            initial_w=initial_frac,
            lastest_only=True
        )

        last = data.iloc[-1]
        last_idx = data.index[-1]
        fraction = last['weight']

        self.state['state'] = dict(time=now,
                                   fraction=fraction,
                                   last={'opentime': last_idx,
                                         **last.to_dict()})

        return fraction
    

    def post_tick(self, now: datetime) -> float:
        self.optimize(
            self.strategy.get_klines(self.config.opt_range),
            self.strategy.trading_fee,
            now
        )


