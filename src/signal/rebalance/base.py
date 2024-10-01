from ..base import BaseSignal
from datetime import datetime
import pandas as pd


class RebalanceSignal(BaseSignal):
    def __init__(self) -> None:
        super().__init__()
    
    def inject_strategy(self, strategy):
        self.strategy = strategy
