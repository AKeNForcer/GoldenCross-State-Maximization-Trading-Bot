from ccxt import Exchange
from src.core.logger import logger
from src.core.controller import Syncronizable
from src.core.timeframe import tf_to_resample
from datetime import datetime
import pandas as pd
import numpy as np


class DataBroker(Syncronizable):
    def __init__(self, ex: Exchange,
                 symbol: str, timeframe: str,
                 fill=True) -> None:
        super().__init__()
        self.symbol = symbol
        self.timeframe = timeframe
        self.tfdelta = pd.to_timedelta(timeframe)
        self.ex = ex
        self.fill = fill
    
    def _get_params(self, 
                    limit: int | None,
                    start: datetime | None,
                    last: datetime | None,
                    end: datetime | None):
        if last is not None and end is not None:
            raise ValueError('last and end must not specify both at the same time.')

        if end is not None:
            last = end - self.tfdelta
        elif last is not None:
            end = last + self.tfdelta
        else:
            if start is not None and limit is not None:
                end = start + limit * self.tfdelta
                last = end - self.tfdelta

        if start is None and end is not None and limit is not None:
            start = end - limit * self.tfdelta
        
        if limit is None and start is not None and end is not None:
            limit = np.floor((end - start) / self.tfdelta)


        return start, end, limit

    def get(self, limit: int | None = None,
            start: datetime | None = None,
            last: datetime | None = None,
            end: datetime | None = None):
        start, end, limit = self._get_params(limit, start, last, end)

        df = pd.DataFrame(self.ex.fetch_ohlcv(self.symbol, self.timeframe,
                                              since=int(start.timestamp() * 1000) \
                                                if start else None,
                                              limit=limit),
                          columns=['time', 'open', 'high', 'low',
                                   'close', 'volume'])
        df['time'] = pd.to_datetime(df['time']*1000000)
        df.set_index('time', inplace=True)
        df = df.resample(tf_to_resample(self.timeframe)).last()
        if self.fill:
            df.ffill(inplace=True)
        if start is not None:
            df = df.loc[df.index >= start]
            if limit:
                df = df.iloc[:limit]
        if end is not None:
            df = df.loc[df.index < end]
        if limit:
            df = df.iloc[-limit:]
        
        return df

    def tick(self, now: datetime):
        pass