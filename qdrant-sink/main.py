from quixstreams import Application, message_key, message_context
from qdrant_client import models, QdrantClient

import os
import uuid

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()


qdrant = QdrantClient(
    url="https://20670375-f669-4a3f-a67e-dd533679b26d.us-east4-0.gcp.cloud.qdrant.io:6333",
    api_key=os.environ['qdrant_apikey'],
    grpc_port=6334,
    prefer_grpc=True,
    timeout=100
)

collection = os.environ['collectionname']
createcollection = os.environ['createcollection'] == "true"

print(createcollection)

if not qdrant.collection_exists(collection):
  # Create collection to store items
  qdrant.create_collection(
      collection_name=collection,
      vectors_config=models.VectorParams(
          size=int(os.environ["vector_size"]), # Vector size is defined by used model
          distance=models.Distance.COSINE
      )
  )

# Get collection to store items
qdrant.get_collection(
    collection_name=collection,
)


# Define the ingestion function
def ingest_vectors(row):

    row['metadata']['partition'] = message_context().partition
    row['metadata']['offset'] = message_context().offset

    single_record = models.PointStruct(
        id=row['metadata']['uuid'],
        vector=row['embeddings'],
        payload=row
    )

    qdrant.upload_points(
        collection_name=collection,
        points=[single_record]
    )

    print(f"Ingested vector from thread: {bytes.decode(message_key())}")
  
  
offsetlimit = 125

# def on_message_processed(topic, partition, offset):
#     if offset > offsetlimit:
#         app.stop()

app = Application.Quix(
    consumer_group="qdrant-ingestion-v6.4",
    auto_offset_reset="earliest",
)

# Define an input topic with JSON deserializer
input_topic = app.topic(os.environ['input']) # Merlin.. i updated this for you

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(topic=input_topic)

sdf = sdf[sdf['metadata'].contains('uuid')]

# INGESTION HAPPENS HERE
### Trigger the embedding function for any new messages(rows) detected in the filtered SDF
sdf = sdf.update(lambda row: ingest_vectors(row))
app.run(sdf)