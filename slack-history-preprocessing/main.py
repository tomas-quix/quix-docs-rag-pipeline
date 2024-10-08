import os
from quixstreams import Application, State
import uuid
import json

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()


app = Application.Quix(
    "slack-history-preprocessing-v1.4", 
    auto_offset_reset="earliest",
    on_processing_error=lambda ex, row, *_: print(row.value))

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])


sdf = app.dataframe(input_topic)

#sdf = sdf[sdf['type'] == 'message']
sdf = sdf[sdf.contains('channel_id')]
sdf = sdf[sdf.contains("user")]

sdf["thread_ts"] = sdf.apply(lambda row: float(row["thread_ts"] if "thread_ts" in row else row['ts']))

def project_replies(row: dict):
    return {
      "text": row['text'],
      "user":  row['user'],
      "event_ts": float(row['ts']),
      "file_ids": list(map(lambda row: row['id'], filter(lambda f: 'mimetype' in f and f['mimetype'] == 'text/plain', row['files']))) if 'files' in row else []
      
    }

def project_messages(row: dict):
    
    result = {
            "text": row['text'],
            "channel": row['channel_id'],
            "user": row['user'],
            "thread_ts": row['thread_ts'],
            "event_ts": float(row['ts']),
            "file_ids": list(map(lambda row: row['id'], filter(lambda f: 'mimetype' in f and f['mimetype'] == 'text/plain', row['files']))) if 'files' in row else []
            
    }
    
    if 'replies' in row:
        result["replies"] = list(map(lambda reply: project_replies(reply), filter(lambda row: 'user' in row, row['replies'])))
    else:
        result["replies"] = []
        
    return result

sdf = sdf.apply(project_messages)    

sdf = sdf.update(lambda row: print(json.dumps(row, indent=4)))

sdf = sdf.to_topic(output_topic, key=lambda row: f"{row['user']}-{row['thread_ts']}")

if __name__ == "__main__":
    app.run(sdf)