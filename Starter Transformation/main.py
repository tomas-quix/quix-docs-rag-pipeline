import os
from quixstreams import Application

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application(consumer_group="demo-v1.1", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)

sdf = sdf.apply(lambda row: row["event"])

sdf = sdf[sdf.contains("text")]

sdf["words-count"] = sdf["text"].apply(lambda text: len(text.split(" ")))

sdf = sdf[["ts", "words-count"]]

sdf.print()
sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)