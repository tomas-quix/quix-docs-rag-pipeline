from quixstreams import Application 
from quixstreams import State, message_key
import os
import time
import uuid

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()


# Define your application and settings
app = Application(consumer_group="slack-embeddings-v1.9",auto_offset_reset="earliest")

# Define an input topic with JSON deserializer
input_topic = app.topic(os.environ['input'], value_deserializer="json")

# Define an output topic with JSON serializer
output_topic = app.topic(os.environ['output'], value_serializer="json")

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(topic=input_topic)

sdf = sdf[sdf["root"]["channel"] == "SDK"]

# Publish the processed SDF to a Kafka topic specified by the output_topic object.
sdf = sdf.to_topic(output_topic)

app.run(sdf)