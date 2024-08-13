from datetime import datetime
import logging
from logging import Logger
import time

from pymongo import MongoClient, ASCENDING, errors
from quixstreams.sinks import SinkBatch
from quixstreams.sinks import BatchingSink

from utils import format_nanoseconds

class MongoDBSink(BatchingSink):
    def __init__(
        self,
        uri: str,
        database_name: str,
        collection_name: str,
        logger: Logger = None
    ):
        self.uri = uri
        self.database_name = database_name
        self.collection_name = collection_name
        
        self.columns = []
        
        self.logger = logger if logger is not None else logging.getLogger("MongoDB Sink")

        # Define the format for the logs, including the timestamp
        log_format = '%(asctime)s-%(levelname)s-%(message)s'

        # Configure the basicConfig with the new format and, optionally, the date format
        logging.basicConfig(format=log_format, datefmt='%Y-%m-%d %H:%M:%S')

        super().__init__()
        
    def connect(self):
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            
            self.logger.info("CONNECTED to MongoDB!")
        except Exception as e:
            self.logger.error(f"ERROR!: {e}")
            raise

        self._create_indexes()
        
    def write(self, batch: SinkBatch):
        all_cols = list(set().union(*map(lambda b: b.value, batch)))
        all_cols = list(set().union([*all_cols, "timestamp", "__key"]))
        
        all_rows = []
        
        last_timestamp = None
        
        for row in batch:
            timestamp = format_nanoseconds(row.timestamp * 1E6)

            last_timestamp = row.timestamp
                
            result_row = {
                **row.value,
                "timestamp": timestamp,
                "__key": str(row.key)
            }
            
            all_rows.append(result_row)
    
        self._insert_row(all_rows)
        
        start_time = time.time()
        self.logger.debug(f"Data ({batch.size}) from {str(datetime.fromtimestamp(last_timestamp / 1000))} sent in {time.time() - start_time}.")
        
    def _create_indexes(self):
        # Create indexes for timestamp and key fields for faster querying
        self.collection.create_index([("timestamp", ASCENDING)])
        self.collection.create_index([("__key", ASCENDING)])

    def _insert_row(self, rows: list):
        try:
            result = self.collection.insert_many(rows)
            self.logger.debug(f"Inserted {len(result.inserted_ids)} rows into MongoDB.")
        except errors.BulkWriteError as e:
            self.logger.error(f"Encountered errors while inserting rows: {e.details}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error occurred: {e}")
            raise


class Null:
    def __init__(self):
        self.name = 'NULL'

    def __str__(self):
        return self.name