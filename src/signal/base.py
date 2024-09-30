from datetime import timedelta
from src.core.db import StateInjectable


class BaseSignal(StateInjectable):
    def get_length(self) -> timedelta | int:
        raise NotImplementedError()