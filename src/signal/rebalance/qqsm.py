from pydantic import BaseModel, conint
from typing import Literal, List, Any
import pandas as pd
import numpy as np
from .state_maximization import KlineStateTemplate, StateMaximization
from src.utils.backtest.data import make_time_window












class QqKlineStateConfigSpace(BaseModel):
    state_target: List[Literal['close', 'ret']]
    qt_length: List[conint(gt=1)]
    qt_steps: List[conint(gt=1)]
    chain_length: List[conint(gt=1)]


class QqKlineStateConfig(BaseModel):
    state_target: Literal['close', 'ret']
    qt_length: conint(gt=1)
    qt_steps: conint(gt=1)
    chain_length: conint(gt=1)





class QqKlineState(KlineStateTemplate):
    def get(self, data: pd.DataFrame, **config) -> pd.DataFrame:
        config = QqKlineStateConfig(**config)

        data['uni_state'] = (data[config.state_target] \
                             .rolling(config.qt_length).rank() * \
                                config.qt_steps / config.qt_length).round()
        state = make_time_window(data[['uni_state']], ['uni_state'],
                                 steps=config.chain_length, dropna=False)

        data['state'] = (state * \
                         np.power(config.qt_steps + 1, np.arange(config.chain_length)[::-1])) \
                            .sum(axis=1, skipna=False)
        
        return data
    

    def get_length(self,
                   config_space: QqKlineStateConfigSpace | dict[str, List[Any]]) -> int:
        config_space = QqKlineStateConfigSpace(**config_space)
        return sum([ max(x) for x in [config_space.qt_length,
                                      config_space.chain_length] ])










class QuantizedQuantileStateMaximization(StateMaximization):
    def __init__(self, config: dict, kline_state_config: dict) -> None:
        super().__init__(config, kline_state_config, QqKlineState())



