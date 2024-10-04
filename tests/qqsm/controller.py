from traceback import format_exc
from apscheduler.schedulers.blocking import BlockingScheduler
from src.core.logger import logger
from src.core.controller import Syncronizable, Controller
from src.core.db import State
from src.core.time import current_datetime
from datetime import datetime
from time import sleep




class MockController(Controller):
    def __init__(self,
                 modules: dict[str, Syncronizable],
                 state: State | None = None):
        if type(modules) != dict:
            self.modules = { 'module': modules }
        else:
            self.modules = modules
        
        self.state = state
        
        if state:
            for name, module in self.modules.items():
                module.inject_state(state.sub_state(name))
    
    def _handle_error(self, e):
        raise e
        # tb = format_exc()
        # logger.error(tb)

    def tick(self):
        try:
            now = current_datetime()
            payloads = []
            logger.info('==================== tick start ====================')
            for name, module in self.modules.items():
                logger.info(f'====== module: {name} ==========')
                payloads.append(module.tick(now))
            logger.info('==================== tick done ====================')
            for (name, module), payload in zip(self.modules.items(), payloads):
                logger.info(f'====== module: {name} ==========')
                module.post_tick(now, payload)
            logger.info('==================== post tick done ====================')
        except Exception as e:
            self._handle_error(e)
        finally:
            if self.state:
                self.state.save(now)
            logger.info('==================== state saved ====================')

