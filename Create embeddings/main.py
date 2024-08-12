from quixstreams import Application 
import os
import time
import openai

# Set your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

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
    
    text_chunks = split_string_with_overlap(row['page_content'], 4000, 200)
    
    result_chunks = []
        
    for i, text_chunk in enumerate(text_chunks):
        
        text = text_chunk
        
        response = openai.embeddings.create(input=text, model="text-embedding-3-large")
        embeddings = response.data[0].embedding
        result_chunks.append({**row, "embeddings": embeddings})
        print(f'Created vector: "{embeddings}"')

    return result_chunks

# Define your application and settings
app = Application.Quix(
    consumer_group=os.environ['consumergroup'],
    auto_offset_reset="earliest",
    producer_extra_config={"allow.auto.create.topics": "true"},
)

# Define an input topic with JSON deserializer
input_topic = app.topic(os.environ['input'], value_deserializer="json")

# Define an output topic with JSON serializer
output_topic = app.topic(os.environ['output'], value_serializer="json")

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(topic=input_topic)
sdf = sdf.update(lambda val: print(f"Received update: {val}"))

# Trigger the embedding function for any new messages(rows) detected in the filtered SDF
sdf = sdf.apply(create_embeddings, expand=True)

# Update the timestamp column to the current time in nanoseconds
sdf["Timestamp"] = sdf["Timestamp"].apply(lambda row: time.time_ns())

# Publish the processed SDF to a Kafka topic specified by the output_topic object.
sdf = sdf.to_topic(output_topic)

app.run(sdf)