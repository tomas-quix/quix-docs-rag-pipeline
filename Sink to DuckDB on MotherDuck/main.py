from quixstreams import Application, State, message_key
import duckdb
import pandas as pd
import os
import time

os.environ['input'] = 'quix-raw-docs-html-no0_5_1kchars'
os.environ['table'] = 'quix-documents-1kchunks'

mdtoken = os.environ['motherduck_token']
# initiate the MotherDuck connection through a service token through
con = duckdb.connect(f'md:Docstore?motherduck_token={mdtoken}') 

# Define the embedding function
def sink_duckdb(conn, row, table_name):
    # Ensure row is a list of dictionaries
    #if isinstance(row, dict):
    #    row = [row]
    
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame([row])
    #df = row
    # Insert the DataFrame into the existing table using the execute method
    conn.execute(f"INSERT INTO '{table_name}' SELECT * FROM df")
    
    # Print a confirmation message
    print(f"Inserted {len(df)} row into '{table_name}'.")

# Define your application and settings
app = Application.Quix(
    consumer_group="duckdb-sink-v2",
    auto_offset_reset="earliest",
    consumer_extra_config={"allow.auto.create.topics": "true"},
    producer_extra_config={"allow.auto.create.topics": "true"},
)

# Define an input topic with JSON deserializer
input_topic = app.topic(os.environ['input'], value_deserializer="json")

# Initialize a streaming dataframe based on the stream of messages from the input topic:
sdf = app.dataframe(topic=input_topic)
sdf = sdf.update(lambda val: print(f"Received update: {val}"))

# Trigger the embedding function for any new messages(rows) detected in the filtered SDF
sdf = sdf.update(lambda val: sink_duckdb(con, val, os.environ['table']), stateful=False)

app.run(sdf)