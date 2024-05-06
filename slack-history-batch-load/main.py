import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from quixstreams import Application
import json
# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()


app = Application()

topic = app.topic(os.environ["output"])
producer = app.get_producer()

def fetch_channels(client):
    """Fetches a list of all channels the bot is a member of."""
    channels = []
    try:
        # Initial call to fetch the first batch of channels
        result = client.conversations_list()
        channels.extend(result['channels'])
        
        # Continue fetching all channels using pagination
        while result['response_metadata']['next_cursor']:
            result = client.conversations_list(cursor=result['response_metadata']['next_cursor'])
            channels.extend(result['channels'])
    except SlackApiError as e:
        print(f"Error fetching channels: {e}")

    return channels

def fetch_thread_replies(client, channel_id, thread_ts):
    """Fetches all replies to a parent message in a thread."""
    replies = []
    try:
        response = client.conversations_replies(channel=channel_id, ts=thread_ts)
        replies.extend(response['messages'])

        while response['has_more']:
            response = client.conversations_replies(channel=channel_id, ts=thread_ts, cursor=response['response_metadata']['next_cursor'])
            replies.extend(response['messages'])

    except SlackApiError as e:
        print(f"Error fetching replies for thread {thread_ts} in channel {channel_id}: {e}")

    return replies

def fetch_messages_from_channel(client, channel_id):
    """Fetches all messages from a given channel."""
    
    messages = []
    try:
        # Initial call to fetch the first batch of messages
        response = client.conversations_history(channel=channel_id)
        messages.extend(response['messages'])

        while response['has_more']:
            response = client.conversations_history(channel=channel_id, cursor=response['response_metadata']['next_cursor'])
            messages.extend(response['messages'])
        
        for message in response['messages']:
            if message.get('thread_ts') and message['thread_ts'] == message['ts']:  # Check it's a thread parent
                replies = fetch_thread_replies(client, channel_id, message['thread_ts'])
                message['replies'] = replies
            
            message['channel_id'] = channel_id
            
            producer.produce(topic.name, json.dumps(message), channel_id, timestamp=int(float(message['ts'])* 1000))
            print(message)
        
       
        
    except SlackApiError as e:
        print(f"Error fetching messages from channel {channel_id}: {e}")


if __name__ == "__main__":
    client = WebClient(token=os.environ["slack_token"])
    channels = fetch_channels(client)
    all_messages = []

    for channel in channels:
        if channel['id'] != "C01H1LQHCAU":
            continue
        channel_id = channel['id']
        channel_name = channel['name']
        print(f"Fetching messages from channel: {channel_name}")
        messages = fetch_messages_from_channel(client, channel_id)
        all_messages.append({
            'channel': channel_name,
            'messages': messages
        })


    print("DONE...")