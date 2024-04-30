import os
from quixstreams import Application, State, message_key

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application.Quix("slack-aggregate-threads-v2.5", auto_offset_reset="earliest", use_changelog_topics=False)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

sdf = app.dataframe(input_topic)


def aggregate_threads(row: dict, state: State):
    
    state_key = bytes.decode(message_key())
    
    default_state = {**row, 'replies': []}
    
    thread = state.get(state_key, default_state)
    
    if row['event_ts'] != row['thread_ts']:
        thread['replies'].append(row)
    
    state.set(state_key, thread)
    
    return thread

sdf = sdf.apply(aggregate_threads, stateful=True)

def print_threads(row: dict):
    
    print(f"[{row['user']}]): {row['text']}")
    
    for reply in row['replies']:
        print(f"--- [{reply['user']}]: {reply['text']}")
        

sdf = sdf.update(print_threads)


sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)