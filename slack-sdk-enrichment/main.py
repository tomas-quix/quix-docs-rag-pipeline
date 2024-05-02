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
host = os.environ['redis-host'] # 'redis-16017.c251.east-us-mz.azure.redns.redis-cloud.com'
port = os.environ['redis-port'] '16017'
password = 'lYZaRHEr7Ee6ysLAdRoH3s9lmg2koxsk'

# Create the Redis connection
redis_client = redis.Redis(host=host, port=port, password=password, decode_responses=True)


app = Application.Quix("slack-enrich-v2.4", auto_offset_reset="latest", use_changelog_topics=True)

input_topic = app.topic(os.environ["input"])
output_topic = app.topic(os.environ["output"])

def lookup_users(row:dict, state: State):
    
    user_id = row["user"]
    
    if user_id is None:
        return None
    
    user = redis_client.get(user_id)
    
    if user is None:
        print("Getting info about user: " + user_id)
        user_dto = client.users_info(user=user_id)
        if 'real_name' in user_dto["user"]:
            user = user_dto["user"]["real_name"]
        else:
            user = user_dto["user"]['profile']["real_name"]
        print(user)
        redis_client.set(user_id, user)
    
    row['user'] = user
    
        
    if 'replies' in row:
        for reply in row['replies']:
            lookup_users(reply, state)
        
        
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

sdf = sdf[sdf.contains('channel')]
    
sdf["channel"] = sdf.apply(lookup_channel, stateful=True)
sdf = sdf.update(lookup_users, stateful=True)

sdf = sdf.update(lambda row: print(row))

sdf = sdf.to_topic(output_topic)

if __name__ == "__main__":
    app.run(sdf)