from ..base import BaseSignal
from datetime import datetime
import pandas as pd


class RebalanceSignal(BaseSignal):
    def __init__(self) -> None:
        super().__init__()
    
    def get(self, now: datetime, data: pd.DataFrame) -> float:
        raise NotImplementedError()