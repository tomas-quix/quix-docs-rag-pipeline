import os
from quixstreams import Application

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application(consumer_group="transformation-v1.2", auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)

sdf = sdf[sdf.contains("event") & sdf["event"].contains("text")]

sdf = sdf.apply(lambda row: row["event"])

sdf["words_count"] = sdf["text"].apply(lambda text: len(text.split(" ")))

sdf = sdf[["ts", "words_count"]]

sdf = sdf.apply(lambda row: row["words_count"]).tumbling_window(60000).sum().final()

sdf.print()
sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)