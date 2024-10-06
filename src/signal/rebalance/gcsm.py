from pydantic import BaseModel, conint, Field
from typing import Literal, List, Any
import pandas as pd
import numpy as np
from .state_maximization import KlineStateTemplate, StateMaximization












class GcKlineStateConfigSpace(BaseModel):
    state_target: List[Literal['close', 'ret']]
    ema_fast_length: List[conint(gt=1)] = Field(default=[12])
    ema_slow_length: List[conint(gt=2)] = Field(default=[26])


class GcKlineStateConfig(BaseModel):
    state_target: Literal['close', 'ret']
    ema_fast_length: conint(gt=1) = Field(default=12)
    ema_slow_length: conint(gt=2) = Field(default=26)





class GcKlineState(KlineStateTemplate):
    def __init__(self, buffer_safety_factor=5) -> None:
        self.buffer_safety_factor = buffer_safety_factor

    def get(self, data: pd.DataFrame, **config) -> pd.DataFrame:
        config = GcKlineStateConfig(**config)
        data['ema_fast'] = data[config.state_target].ewm(span=config.ema_fast_length).mean()
        data['ema_slow'] = data[config.state_target].ewm(span=config.ema_slow_length).mean()
        data['state'] = (data['ema_fast'] > data['ema_slow']) * 1
        return data
    

    def get_length(self,
                   config_space: GcKlineStateConfigSpace | dict[str, List[Any]]) -> int:
        config_space = GcKlineStateConfigSpace(**config_space)
        return max(*config_space.ema_fast_length,
                   *config_space.ema_slow_length)










class GoldenCrossStateMaximization(StateMaximization):
    def __init__(self, config: dict, kline_state_config: dict) -> None:
        super().__init__(config, kline_state_config, GcKlineState())



