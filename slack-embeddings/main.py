from quixstreams import Application 
from quixstreams import State, message_key
from sentence_transformers import SentenceTransformer
import os
import time
import datetime
import uuid

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

encoder = SentenceTransformer('all-MiniLM-L6-v2') # Model to create embeddings

# Define the embedding function
def create_embeddings(row):
    text = f"At {datetime.datetime.fromtimestamp(row['event_ts'])}"
    text += f" in Slack channel {row['channel']}"
    text += f" user {row['user']} posted: {row['text']}"
    
    for reply in row['replies']:
        text = f"At {datetime.datetime.fromtimestamp(reply['event_ts'])}"
        text += f" user {reply['user']} replied to that with text: {reply['text']}"
        
    embeddings = encoder.encode(text)
    embedding_list = embeddings.tolist() # Conversion step because SentenceTransformer outputs a numpy Array but Qdrant expects a plain list
    print(f'Created vector: "{embedding_list}"')

    id = f"{bytes.decode(message_key())}"

    return {
        'page_content': text,
        'embeddings': embedding_list,
        'doc_id': id,
        'metadata': {
            'title': row['text'],
            'id': id
        }
    }

# Define your application and settings
app = Application(consumer_group="slack-embeddings-v1.10",auto_offset_reset="earliest")

# Define an input topic with JSON deserializer
input_topic = app.topic(os.environ['input'], value_deserializer="json")

# Define an output topic with JSON serializer
output_topic = app.topic(os.environ['output'], value_serializer="json")

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(topic=input_topic)

sdf = sdf.update(lambda val: print(f"Received update: {val}"))

sdf = sdf[sdf.contains("event_ts")]

# Trigger the embedding function for any new messages(rows) detected in the filtered SDF
sdf = sdf.apply(create_embeddings)

# Update the timestamp column to the current time in nanosecondsc
sdf["Timestamp"] = sdf.apply(lambda row: time.time_ns())

# Publish the processed SDF to a Kafka topic specified by the output_topic object.
sdf = sdf.to_topic(output_topic)

app.run(sdf)