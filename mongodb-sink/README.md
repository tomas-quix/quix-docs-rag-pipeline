# MongoDB Sink

This project provides a sink for streaming data into MongoDB.

## Setup

1. Install dependencies:
	```sh
	pip install -r requirements.txt
	```

2. Set up environment variables. Create a `.env` file in the root directory and add the following:
	```env
	URI=your_mongodb_uri
	DATABASE_NAME=your_database_name
	COLLECTION_NAME=your_collection_name
	CONSUMER_GROUP=your_consumer_group
	input=your_input_topic
	```

## Usage

1. Run the application:
	```sh
	python main.py
	```

## Configuration

- `URI`: The MongoDB connection URI.
- `DATABASE_NAME`: The name of the MongoDB database.
- `COLLECTION_NAME`: The name of the MongoDB collection.
- `CONSUMER_GROUP`: The consumer group for the application.
- `input`: The input topic for the application.

## Example

Here is an example of how to use the MongoDB sink in your application:

```python
import os
from setup_logger import logger
from quixstreams import Application
from dotenv import load_dotenv
from mongo_db_sink import MongoDBSink

load_dotenv()

mongodb_sink = MongoDBSink(
    uri=os.environ["URI"],
    database_name=os.environ["DATABASE_NAME"],
    collection_name=os.environ["COLLECTION_NAME"],
    logger=logger)

mongodb_sink.connect()

app = Application(
    consumer_group=os.environ["CONSUMER_GROUP"], 
    auto_offset_reset="earliest",
    commit_interval=1,
    commit_every=100)

input_topic = app.topic(os.environ["input"])

sdf = app.dataframe(input_topic)
sdf.sink(mongodb_sink)
```