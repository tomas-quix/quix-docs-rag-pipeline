import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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

def fetch_messages_from_channel(client, channel_id):
    """Fetches all messages from a given channel."""
    messages = []
    try:
        # Initial call to fetch the first batch of messages
        response = client.conversations_history(channel=channel_id)
        messages.extend(response['messages'])

        # Fetch all further messages using pagination
        while response['has_more']:
            response = client.conversations_history(channel=channel_id, cursor=response['response_metadata']['next_cursor'])
            messages.extend(response['messages'])
        
    except SlackApiError as e:
        print(f"Error fetching messages from channel {channel_id}: {e}")

    return messages

if __name__ == "__main__":
    client = WebClient(token=os.environ["slack_token"])
    channels = fetch_channels(client)
    all_messages = []

    for channel in channels:
        channel_id = channel['id']
        channel_name = channel['name']
        print(f"Fetching messages from channel: {channel_name}")
        messages = fetch_messages_from_channel(client, channel_id)
        all_messages.append({
            'channel': channel_name,
            'messages': messages
        })
        print(f"Total messages fetched from {channel_name}: {len(messages)}")

    # Summarize total messages fetched across all channels
    total_messages = sum(len(channel['messages']) for channel in all_messages)
    print(f"Total messages fetched across all channels: {total_messages}")
