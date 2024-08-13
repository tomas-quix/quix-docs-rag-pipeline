import os
from setup_logger import logger

from quixstreams import Application

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

from mongo_db_sink import MongoDBSink


mongodb_sink = MongoDBSink(
    uri=os.environ["URI"],
    database_name=os.environ["DATABASE_NAME"],
    collection_name=os.environ["COLLECTION_NAME"],
    logger=logger)

mongodb_sink.connect()

app = Application(
    consumer_group=os.environ["CONSUMER_GROUP"], 
    auto_offset_reset = "earliest",
    commit_interval=1,
    commit_every=100)

input_topic = app.topic(os.environ["input"])

sdf = app.dataframe(input_topic)
sdf.sink(mongodb_sink)

if __name__ == "__main__":
    app.run(sdf)