from datetime import datetime
from ccxt import Exchange
from src.core.controller import Syncronizable
from src.core.db import DatabaseWrapper





class BaseStrategy(Syncronizable):
    def __init__(self, ex: Exchange,
                 name: str = 'base'):
        super().__init__()
        self.name = name
        self.ex = ex
    
    def tick(self, now: datetime):
        pass

    def post_tick(self, now: datetime, payload):
        pass