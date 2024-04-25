import os
from quixstreams import Application, State
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import uuid
import json


# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

client = WebClient(token=os.environ["slack_token"])


app = Application.Quix("slack-enrich-v1", auto_offset_reset="earliest", use_changelog_topics=True)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

def lookup_user(user_id:str, state: State):
    
    if user_id is None:
        return None
    
    user = state.get(user_id, None)
    
    if user is None:
        print("Getting info about user: " + user_id)
        user_dto = client.users_info(user=user_id)
        print(user_dto)
        user = user_dto["user"]["real_name"]
        state.set(user_id, user)
        
    return user
        
def lookup_channel(row:dict, state: State):
    channel_id = row["channel"]
    channel_name = state.get(channel_id, None)
    
    if channel_name is None:
        print("Getting info about channel: " + channel_id)
        
        channel_dto = client.conversations_info(channel=channel_id)
        print(channel_dto)
        
        channel_name = channel_dto["channel"]["name"]
        state.set(channel_id, channel_name)
        
    return channel_name



sdf = app.dataframe(input_topic)
    
    
sdf = sdf.apply(lambda row: row["event"])
sdf = sdf[sdf.contains("text") & sdf["text"].notnull()]

sdf = sdf[(sdf['type'] == 'message') & (sdf.contains("user"))]

    

sdf["channel"] = sdf.apply(lookup_channel, stateful=True)
sdf["parent_user"] = sdf.apply(lambda row,state: lookup_user(row.get("parent_user_id", None), state), stateful=True)
sdf["user"] = sdf.apply(lambda row,state: lookup_user(row["user"], state), stateful=True)


sdf["parent_user_id"] = sdf.apply(lambda row: row.get("parent_user_id", None))
sdf["thread_ts"] = sdf.apply(lambda row: row.get("thread_ts", None))


sdf = sdf[["text", "channel", "user","text", "thread_ts", "parent_user"]]

sdf = sdf.update(lambda row: print(row))

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)