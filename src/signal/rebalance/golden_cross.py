from datetime import datetime, timedelta
from pandas import DataFrame

from src.core.db import State
from .base import RebalanceSignal



class GoldenCross(RebalanceSignal):
    def __init__(self, config: dict) -> None:
        super().__init__()
        
        config['period'] = sorted(config['period'])
        self.period = config['period']
        for i in range(len(self.period) - 1):
            if self.period[i] >= self.period[i+1]:
                raise ValueError(f'period values {self.period} should not be replicated')
        
        config['buffer'] = config.get('buffer') or max(self.period) * 4
        self.buffer = config['buffer']

        self.config = config
    
    
    def inject_state(self, state: State):
        super().inject_state(state)
        self.state.load('state')


    def get_length(self) -> timedelta | int:
        return self.buffer


    def tick(self, now: datetime, data: DataFrame) -> float:
        data = data.copy()
        for p in self.period:
            data[f'ema_{p}'] = data['close'].ewm(span=p).mean()
        
        fraction = True
        for i in range(len(self.period) - 1):
            fraction &= (data[f'ema_{self.period[i]}'] > data[f'ema_{self.period[i+1]}'])
        
        data['fraction'] = fraction * 1.0

        last = data.iloc[-1]
        last_idx = data.index[-1]

        cfg = { **self.config }
        del cfg['trade_freq']

        self.state['state'] = dict(time=now,
                                   fraction=last['fraction'],
                                   config=cfg,
                                   last={'opentime': last_idx,
                                         **last.to_dict()})

        return last['fraction']