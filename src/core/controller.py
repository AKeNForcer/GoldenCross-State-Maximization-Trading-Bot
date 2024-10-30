from traceback import format_exc
from apscheduler.schedulers.blocking import BlockingScheduler
from src.core.logger import logger
from src.core.db import State, StateInjectable
from src.core.time import current_datetime
from datetime import datetime
from time import sleep
import os
from threading import Thread


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
                 state: State | None = None,
                 no_watch=None):
        if type(modules) != dict:
            self.modules = { 'module': modules }
        else:
            self.modules = modules
        
        self.scheduler = BlockingScheduler()
        self.scheduler.add_job(self.tick, 'cron', **schedule)
        self.state = state
        self.no_watch = no_watch if no_watch is not None else \
            os.environ.get('NO_WATCH') in [True, 'true', 'True', '1', 1]

        if self.no_watch:
            logger.info('no_watch mode: Tasks will run once and exit.')

        if state:
            for name, module in self.modules.items():
                module.inject_state(state.sub_state(name))
    
    def _handle_error(self, e):
        tb = format_exc()
        logger.error(tb)

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
        
        if self.no_watch:
            logger.info('no_watch mode: Stopping tasks...')
            th = Thread(target=self.scheduler.shutdown)
            th.start()
    
    def start(self):
        try:
            if not self.no_watch:
                for i in range(10):
                    logger.info(f'Starting in {10 - i} seconds')
                    sleep(1)
            logger.info('==================== start running ====================')
            self.scheduler.start()
        except Exception as e:
            self._handle_error(e)
