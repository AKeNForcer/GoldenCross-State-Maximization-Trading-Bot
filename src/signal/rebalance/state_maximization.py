from datetime import datetime, timedelta
from pydantic import BaseModel, conint, confloat, Field
from typing import List, Any, Callable
import pandas as pd
import numpy as np
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed

from .base import RebalanceSignal
from src.core.db import State
from src.strategy.rebalance import RebalanceSingleStrategy
from src.core.logger import logger
from src.utils.backtest.runner import weight_trade_with_idx
from src.utils.backtest.em_weight import maximize_return_points_vt
from src.utils.backtest.backtest import handle_nan
from src.core.time import current_datetime











class KlineStateTemplate:
    def get(self, data: pd.DataFrame, **config) -> pd.DataFrame:
        raise NotImplementedError()
    
    def get_length(self, config_space: dict[str, List[Any]]) -> int:
        raise NotImplementedError()








class SmConfig(BaseModel):
    trade_freq: timedelta
    lookback: List[conint(gt=1)]
    fee_adj: List[confloat(ge=0)] = Field(default=[1])
    forward_length: List[conint(ge=1)] = Field(default=[1])
    offset: List[conint(ge=0)] = Field(default=[0])
    buffer: confloat(gt=1)
    opt_range: conint(gt=1)
    opt_freq: conint(gt=1)
    optimize: bool = Field(default=True)
    score_metric: Callable = Field(default=lambda x: handle_nan(x['Avg. Annual Return [%]']))
    save_opt_results: bool









class GetWeightFn:
    def __init__(self, fee, kline_state: KlineStateTemplate,
                 rng=np.arange(0, 1.01, 0.1)) -> None:
        self.fee = fee
        self.kline_state = kline_state
        self.rng = rng
    
    def _get_weight(self,
                    data: pd.DataFrame,
                    lookback: int,
                    forward_length: int,
                    fee_adj: int,
                    offset: int,
                    *args,
                    initial_w: float | None=None,
                    lastest_only=False,
                    **kwargs):
        
        data = data.copy()
        data['ret'] = data['close'].pct_change().fillna(0)

        data = self.kline_state.get(data, *args, **kwargs)

        weight = pd.DataFrame(index=data.index)
        weight['weight'] = 0.0

        prev_w = initial_w or 0

        for i in range(len(data) - 1 if lastest_only else lookback, len(data)):
            idx = data.index[i]
            sel = data.index[i + 1 - offset - lookback:
                             i + 1 - offset]

            window = data.loc[sel]
            st = window['state']
            last_st = st.iloc[-1]
            
            st_sel = st == last_st # why not compare with state at {idx}

            st_sel_start = window.index[st_sel]
            st_sel_end = window.index.shift(forward_length)[st_sel]

            w_sel = np.logical_or.reduce([(window.index >= start) & (window.index < end) \
                                        for start, end in zip(st_sel_start, st_sel_end)])
            

            window = window.loc[w_sel]
            ret = window['ret']

            w = maximize_return_points_vt(ret, fee=self.fee*fee_adj, prev=prev_w,
                                        rng=np.arange(0, 1.00001, 0.1))
            weight.loc[idx, 'weight'] = w
            weight.loc[idx, 'ret_avg'] = ret.mean()
            weight.loc[idx, 'ret_count'] = len(ret)
            weight.loc[idx, 'last_st'] = last_st
            weight.loc[idx, 'w_kline_start'] = sel[0]
            weight.loc[idx, 'w_kline_last'] = sel[-1]
            weight.loc[idx, 'w_kline_count'] = len(sel)
            prev_w = w

        data = data.join(weight)
        
        return data









class StateMaximization(RebalanceSignal):
    
    # ===== Init part =====
    
    def __init__(self, config: dict, kline_state_config: dict,
                 kline_state: KlineStateTemplate) -> None:
        super().__init__()

        self.kline_state = kline_state
        self.kline_state_config = kline_state_config

        config['buffer'] = \
            config.get('buffer') or \
                max(config['lookback']) + \
                max(config['forward_length']) + \
                    self.kline_state.get_length(self.kline_state_config)
        
        config['save_opt_results'] = config.get('save_opt_results') or False

        self.config = SmConfig(**config)

    
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
        
        if not self.config.optimize:
            now = current_datetime()
            self.state['params'] = {
                'date': now,
                '_expected_expire': now + self.config.opt_freq * self.config.trade_freq,
                '_kline_start': None,
                '_kline_last': None,
                '_kline_count': 0,
                'lookback': self.config.lookback[0],
                'forward_length': self.config.forward_length[0],
                'fee_adj': self.config.fee_adj[0],
                'offset': self.config.offset[0],
                **{ k: v[0] for k, v in self.kline_state_config.items() }
            }
        else:
            self.optimize(
                self.strategy.get_klines(self.config.opt_range),
                self.strategy.trading_fee,
                save=True
            )


    def get_length(self) -> int:
        return int(self.config.buffer)



    # ===== Hyperparams Optimize part =====

    def _mp_opt(self, data: pd.DataFrame, fee: float):
        with ProcessPoolExecutor() as executor:
            futures = []
            
            for (
                lookback,
                forward_length,
                fee_adj,
                offset,
                *kline_cfg
            ) in product(
                self.config.lookback,
                self.config.forward_length,
                self.config.fee_adj,
                self.config.offset,
                *[ v for v in self.kline_state_config.values() ]
            ):
                params = dict(
                    lookback=lookback,
                    forward_length=forward_length,
                    fee_adj=fee_adj,
                    offset=offset,
                    **dict(zip(self.kline_state_config.keys(), kline_cfg))
                )

                f = executor.submit(weight_trade_with_idx,
                                    params,
                                    data=data,
                                    get_weight=GetWeightFn(fee=fee,
                                                           kline_state=self.kline_state
                                                           )._get_weight,
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

        now = now or current_datetime()
        date = self.state['params'].get('date')
        
        if not force and date and \
            (now < date + self.config.opt_freq * self.config.trade_freq):
            return
        
        logger.info(f'Params expired or not exists, starting optimization')
        logger.info(f'Optimize klines from {data.index[0]} to {data.index[-1]}')

        results = self._mp_opt(data, fee)
        params, _ = max(results, key=lambda x : self.config.score_metric(x[1]))

        self.state['params'] = {
            'date': now,
            '_expected_expire': now + self.config.opt_freq * self.config.trade_freq,
            '_kline_start': data.index[0],
            '_kline_last': data.index[-1],
            '_kline_count': len(data),
            **params
        }
        if self.config.save_opt_results:
            self.state['opt_results'] = {
                'date': now,
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

        data = GetWeightFn(fee=self.strategy.trading_fee,
                           kline_state=self.kline_state)._get_weight(
            data=data,
            **{ k: v for k, v in params.items() if k not in [
                'date', '_expected_expire', '_kline_start',
                '_kline_last', '_kline_count'
            ] },
            initial_w=initial_frac,
            lastest_only=True
        )

        last = data.iloc[-1]
        last_idx = data.index[-1]
        fraction = last['weight']

        self.state['state'] = dict(time=now,
                                   initial_frac=initial_frac,
                                   kline_start=data.index[0],
                                   kline_last=data.index[-1],
                                   kline_count=len(data),
                                   fraction=fraction,
                                   last={'opentime': last_idx,
                                         **last.to_dict()})

        return fraction
    

    def post_tick(self, now: datetime):
        if not self.config.optimize:
            return
        self.optimize(
            self.strategy.get_klines(self.config.opt_range),
            self.strategy.trading_fee,
            now
        )


