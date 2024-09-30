import logging
from pymongo.collection import Collection
from datetime import datetime


class MongoDBHandler(logging.Handler):
    def __init__(self, collection: Collection):
        logging.Handler.__init__(self)
        self.collection = collection

    def emit(self, record):
        # Format the log record as a dictionary
        log_entry = self.format(record)
        self.collection.insert_one(log_entry)

    def format(self, record):
        # Convert the log record to a dictionary
        return {
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
            "time": str(record.asctime),
            "filename": record.pathname,
            "line": record.lineno,
            "funcName": record.funcName
        }

    def close(self):
        logging.Handler.close(self)





# Create a logger
logger = logging.getLogger('main_logger')
logger.setLevel(logging.DEBUG)

# Create console handler and set level to debug
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create formatter and add it to the handler
formatter = logging.Formatter('[ %(asctime)s | %(levelname)s ] %(message)s')
console_handler.setFormatter(formatter)

# Add the console handler to the logger
logger.addHandler(console_handler)
