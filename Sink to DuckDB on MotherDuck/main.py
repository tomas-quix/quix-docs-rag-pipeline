from quixstreams import Application
from quixstreams import State, message_key

import duckdb
import pandas as pd
import os
import time

mdtoken = os.environ['motherduck_token']
# initiate the MotherDuck connection through a service token through
con = duckdb.connect(f'md:Docstore?motherduck_token={mdtoken}') 

def sink_duckdb(conn, row, table_name):
    # Ensure row is a list of dictionaries
    # if not isinstance(row, list) or not all(isinstance(item, dict) for item in row):
    #    raise ValueError("Row must be a list of dictionaries.")
    
    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame([row])
    df['Timestamp'] = df['Timestamp'].astype(str)
    
    # Check if the table exists and create it if not
    table_exists = conn.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table_name}')").fetchone()[0]
    if not table_exists:
        # Assuming 'row' contains the data with correct types, infer schema from the DataFrame
        schema = pd.io.sql.get_schema(df, table_name)
        conn.execute(schema.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS'))
    
    # Insert the DataFrame into the existing table using the execute method
    conn.execute(f"INSERT INTO '{table_name}' SELECT * FROM df")
    
    # Print a confirmation message
    print(f"Inserted {len(df)} row into '{table_name}'.")
    
    # Print a confirmation message
    print(f"Inserted {len(df)} row into '{table_name}'.")

# Define your application and settings
app = Application.Quix(
    consumer_group="duckdb-sink-v3",
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
sdf = sdf.update(lambda val: sink_duckdb(con, val, os.environ['tablename']), stateful=False)

app.run(sdf)