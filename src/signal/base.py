from datetime import timedelta
from src.core.db import StateInjectable
from datetime import datetime
import pandas as pd


class BaseSignal(StateInjectable):
    def get_length(self) -> timedelta | int:
        raise NotImplementedError()
    
    def get_config(self) -> dict:
        pass

    def tick(self, now: datetime, data: pd.DataFrame) -> float:
        raise NotImplementedError()
    
    def post_tick(self, now: datetime) -> float:
        pass
