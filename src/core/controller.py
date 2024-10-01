from traceback import format_exc
from apscheduler.schedulers.blocking import BlockingScheduler
from src.core.logger import logger
from src.core.db import State, StateInjectable
from datetime import datetime
from time import sleep


class Syncronizable(StateInjectable):
    def tick(self, now: datetime):
        raise NotImplementedError()
    
    def post_tick(self, now: datetime, payload):
        raise NotImplementedError()



class SyncFn(Syncronizable):
    def __init__(self, fn) -> None:
        self.fn = fn
        super().__init__()
    
    def tick(self, now: datetime):
        self.fn(now)



class Controller:
    def __init__(self, schedule: dict,
                 modules: dict[str, Syncronizable],
                 state: State | None = None):
        if type(modules) != dict:
            self.modules = { 'module': modules }
        else:
            self.modules = modules
        
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(self.tick, 'cron', **schedule)
        self.state = state

        if state:
            for name, module in self.modules.items():
                module.inject_state(state.sub_state(name))
    
    def _handle_error(self, e):
        tb = format_exc()
        logger.error(tb)

    def tick(self):
        try:
            now = datetime.now()
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
    
    def start(self):
        try:
            for i in range(10):
                logger.info(f'Starting in {10 - i} seconds')
                sleep(1)
            logger.info('==================== start running ====================')
            self.scheduler.start()
        except Exception as e:
            self._handle_error(e)
