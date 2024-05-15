import os
from quixstreams import Application, State, message_key

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application.Quix(
    "slack-aggregate-threads-v2.5", 
    auto_offset_reset="earliest", 
    use_changelog_topics=False,
    on_processing_error=lambda error, row, *_: print(row))

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

def get_thread_key(row: dict):
    print(row)
    state_key = f'{row["parent_user_id"] if ("parent_user_id" in row) else row["user"]}'
    state_key += f'-{row["thread_ts"] if ("thread_ts" in row) else row["event_ts"]}'
    
    return state_key



sdf = app.dataframe(input_topic)
sdf = sdf.apply(lambda row: row["event"])
sdf = sdf[sdf.contains("user")]
sdf = sdf.group_by(get_thread_key, name="thread-id")

sdf = sdf.apply(lambda row: {
  "text": row["text"],
  "channel": row["channel"],
  "user": row["user"],
  "thread_ts": float(row["thread_ts"] if "thread_ts" in row else row["event_ts"]),
  "event_ts": float(row["event_ts"]),
  "file_ids": list(map(lambda row: row["id"], filter(lambda f: "mimetype" in f and f["mimetype"] == "text/plain", row["files"]))) if "files" in row else []
})

def aggregate_threads(row: dict, state: State):
    
    state_key = get_thread_key(row)
    
    default_state = {**row, "replies": []}
    
    thread = state.get(state_key, default_state)
    
    if row["event_ts"] != row["thread_ts"]:
        thread["replies"].append(row)
    
    state.set(state_key, thread)
    
    return thread

sdf = sdf.apply(aggregate_threads, stateful=True)

def print_threads(row: dict):
    
    print(f'[{row["user"]}]): {row["text"]}')
    
    for reply in row["replies"]:
        print(f'--- [{reply["user"]}]: {reply["text"]}')
        
sdf = sdf.update(print_threads)

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)