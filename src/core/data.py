from ccxt import Exchange
from src.core.logger import logger
from src.core.controller import Syncronizable
from src.core.timeframe import tf_to_resample
from src.core.time import current_datetime
from datetime import datetime
import pandas as pd
import numpy as np


class DataBroker(Syncronizable):
    def __init__(self, ex: Exchange,
                 symbol: str, timeframe: str,
                 fill=True, include_open=False,
                 max_length=1000) -> None:
        super().__init__()
        self.symbol = symbol
        self.timeframe = timeframe
        self.tfdelta = pd.to_timedelta(timeframe)
        self.ex = ex
        self.fill = fill
        self.cache = self._to_df()
        self.include_open = include_open
        self.set_max_length(max_length)
    
    def set_max_length(self, max_length: int):
        self.max_length = int(max_length)
    
    def _get_params(self, 
                    limit: int | None,
                    start: datetime | None,
                    last: datetime | None,
                    end: datetime | None):
        if last is not None and end is not None:
            raise ValueError('last and end must not specify'
                             'both at the same time.')

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
            limit = int((end - start) / self.tfdelta)

        if limit is None:
            limit = 1
        
        if start is None:
            start = (current_datetime() if end is None else end) - limit * self.tfdelta

        return start, limit

    def tick(self, now: datetime):
        pass

    def _to_df(self, data=None):
        df = pd.DataFrame(data or [],
                          columns=['time', 'open', 'high', 'low',
                                   'close', 'volume'], dtype=float)
        df['time'] = pd.to_datetime(df['time']*1000000)
        df.set_index('time', inplace=True)
        return df.resample(self.tfdelta).last()

    def get(self, limit: int | None = None,
            start: datetime | None = None,
            last: datetime | None = None,
            end: datetime | None = None):
        logger.debug(f'data | cache range: '
                     f'{self.cache.index[0] if len(self.cache) > 0 else None} '
                     f'{self.cache.index[-1] if len(self.cache) > 0 else None} '
                     f'freq: {self.cache.index.freq}')
        logger.debug(f'data | query '
                     f'{limit=} '
                     f'{start=} '
                     f'{last=} '
                     f'{end=} ')
        
        start_, limit_ = self._get_params(limit, start, last, end)
        logger.debug(f'data | query '
                     f'{limit_=} '
                     f'{start_=} ')

        if limit_ < 1:
            raise ValueError(f"{limit_=} must >= 1")

        if limit_ > self.max_length:
            raise ValueError(f"{limit_=} must <= {self.max_length=}")

        if (not self.include_open and \
            start_ + self.tfdelta > current_datetime()):
            raise ValueError(f'{start_ = } cannot be future')

        start__, limit__ = start_, limit_

        if (len(self.cache) > 0 and \
            self.cache.index[0] <= start__):
            limit__ = limit__ - len(self.cache.loc[start__:].iloc[:limit])
            start__ = np.max([self.cache.index[-1] + self.cache.index.freq, start__])
            # self.cache.index[0] <= start__ and \:
            # self.cache.index[-1] >= start__ + (limit - 1) * self.tfdelta):
            # _cache = self.cache.loc[start__:].iloc[:limit]
            # self.cache = self.cache.loc[self.cache.index <= _cache.index[-1]]
        else:
            self.cache = self._to_df()
            logger.debug(f'data | reset cache')

        logger.debug(f'data | query '
                     f'{limit__=} '
                     f'{start__=} ')

        df = self._to_df()

        while limit__ > 0:
            _df = self.ex.fetch_ohlcv(self.symbol, self.timeframe,
                                     since=int(start__.timestamp() * 1000),
                                     limit=limit__)
            _df = self._to_df(_df)
            # print((f'start__={start__} limit__={limit__}', flush=True)
            # print((f'i0={_df.index[0]} i1={_df.index[1]}', flush=True)
            if len(_df) > 0:
                logger.debug(f'data | klines updated from: {_df.index[0]} to: {_df.index[-1]} ({limit__})')
            else:
                logger.warning(f'data | no klines updated ({limit__})')
                break

            df = pd.concat([_df, df])
            limit__ -= len(_df)

        self.cache = pd.concat([self.cache, df])

        self.cache = self.cache.iloc[-self.max_length:].resample(self.tfdelta).last()

        return self.cache.loc[start_:].iloc[:limit_]







