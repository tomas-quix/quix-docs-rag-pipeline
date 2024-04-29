import os
from quixstreams import Application, State
import uuid
import datetime

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application.Quix(str(uuid.uuid4()), auto_offset_reset="earliest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"])
#output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)

sdf = sdf[sdf["user"] == "Jack Murphy"]

sdf = sdf[sdf.contains('event_ts')]

sdf = sdf.update(lambda row: print(f"{datetime.datetime.fromtimestamp(row['event_ts'])} {row['user']}: {row['text']}"))

#sdf = sdf.to_topic(output_topic, key=get_thread_key)

if __name__ == "__main__":
    app.run(sdf)