import os
from quixstreams import Application, State
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import uuid
import json
import redis


# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

client = WebClient(token=os.environ["slack_token"])


# Connection details - replace these with your actual RedisCloud credentials
host = os.environ['redis_host'] 
port = int(os.environ['redis_port'])
password = os.environ['redis_password']

# Create the Redis connection
redis_client = redis.Redis(host=host, port=port, password=password, decode_responses=True)


app = Application.Quix("slack-enrich-v2.6", auto_offset_reset="earliest", use_changelog_topics=True)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])


def download_file(id: str):
    response = client.files_info(file=id)
    print(response['content'])
    return str(response['content'])

def download_files(row: dict):
    if "files" in row:
        for file in row['files']:
            row['text'] =+ ("\n" + download_file(file))
            

def lookup_users(row:dict, state: State):
    
    user_id = row["user"]
    
    if user_id is None:
        return None
    
    user = redis_client.get('user_' + user_id)
    
    if user is None:
        print("Getting info about user: " + user_id)
        user_dto = client.users_info(user=user_id)
        if 'real_name' in user_dto["user"]:
            user = user_dto["user"]["real_name"]
        else:
            user = user_dto["user"]['profile']["real_name"]
        print(user)
        redis_client.set('user_' + user_id, user)
    
    row['user'] = user
    
    download_files(row)
        
    if 'replies' in row:
        for reply in row['replies']:
            lookup_users(reply, state)
        
        
def lookup_channel(row:dict, state: State):
    channel_id = row["channel"]
    
    channel_name = redis_client.get('channel_' + channel_id)
    
    if channel_name is None:
        print("Getting info about channel: " + channel_id)
        
        channel_dto = client.conversations_info(channel=channel_id)
        
        channel_name = channel_dto["channel"]["name"]
        state.set(channel_id, channel_name)
        redis_client.set('channel_' + channel_id, channel_name)
        print(channel_name)
        
        
    return channel_name



sdf = app.dataframe(input_topic)

sdf = sdf[sdf.contains('channel')]
    
sdf["channel"] = sdf.apply(lookup_channel, stateful=True)
sdf = sdf.update(lookup_users, stateful=True)

sdf = sdf.update(lambda row: print(row))

#sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)