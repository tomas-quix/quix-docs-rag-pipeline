from quixstreams import Application, message_key
import os
import time
import datetime
import uuid
import openai

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define a namespace (can be any valid UUID)
namespace = uuid.UUID('12345678-1234-5678-1234-567812345678')

def split_string_with_overlap(s, chunk_size, overlap):
    if chunk_size <= overlap:
        raise ValueError("Chunk size must be greater than overlap.")
    
    chunks = []
    start = 0
    while start < len(s):
        end = start + chunk_size
        chunks.append(s[start:end])
        start += (chunk_size - overlap)
    
    return chunks

# Define the embedding function
def create_embeddings(row):
    text = f"{row['text']}"

    for file in row['files']:
        text += "\n" + file
    
    for reply in row['replies']:
        text += f"{reply['text']}"

        for file in reply['files']:
            text += "\n" + file
            
    text_chunks = split_string_with_overlap(text, 4000, 200)
    
    result_chunks = []
        
    for i, text_chunk in enumerate(text_chunks):
        
        response = openai.embeddings.create(input=text_chunk, model="text-embedding-ada-002")
        embeddings = response.data[0].embedding
        
        id = f"{bytes.decode(message_key())}"

        result_chunks.append({
            'page_content': text_chunk,
            'embeddings': embeddings,
            'doc_id': id,
            'metadata': {
                'title': row['text'],
                'id': id,
                'uuid': str(uuid.uuid5(namespace, id)),
                'timestamp': str(datetime.datetime.fromtimestamp(row['event_ts'])),
                'channel': row['channel'],
                'author': row['user'],
                'chunk_index': str(i),
                'chunks_total': str(len(text_chunks))
            }
        })
        
    return result_chunks

# Define your application and settings
app = Application(consumer_group="slack-embeddings-v1.14",auto_offset_reset="earliest")

# Define an input topic with JSON deserializer
input_topic = app.topic(os.environ['input'], value_deserializer="json")

# Define an output topic with JSON serializer
output_topic = app.topic(os.environ['output'], value_serializer="json")

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(topic=input_topic)

sdf = sdf[sdf.contains("event_ts")]

sdf = sdf.filter(lambda row: "subtype" not in row)

sdf = sdf.update(print)

# Trigger the embedding function for any new messages(rows) detected in the filtered SDF
sdf = sdf.apply(create_embeddings, expand=True)

# Publish the processed SDF to a Kafka topic specified by the output_topic object.
sdf = sdf.to_topic(output_topic, key=lambda row: f"{row['doc_id']}-{row['metadata']['chunk_index']}")

app.run(sdf)