import os
from quixstreams import Application, State
import uuid

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application.Quix("group-by-v1.5", auto_offset_reset="earliest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])


def get_thread_key(row: dict):
    print(row)
    state_key = f"{row['parent_user_id'] if ('parent_user_id' in row) else row['user']}"
    state_key += f"- {row['thread_ts'] if ('thread_ts' in row) else row['event_ts']}"
    
    return state_key

sdf = app.dataframe(input_topic)

sdf = sdf[sdf.contains('event')]
sdf = sdf.apply(lambda row: row['event'])
sdf = sdf[sdf.contains("user")]

sdf = sdf.apply(lambda row: {
  "text": row['text'],
  "channel": row['channel'],
  "user": row['user'],
  "thread_ts": float(row["thread_ts"]) if "thread_ts" in row else None,
  "event_ts": float(row['event_ts'])
})

sdf = sdf.update(print)

sdf = sdf.to_topic(output_topic, key=get_thread_key)

if __name__ == "__main__":
    app.run(sdf)