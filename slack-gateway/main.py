from flask import Flask, request, jsonify
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = Flask(__name__)
client = WebClient(token=os.environ['slack_token'])

@app.route('/slack/events', methods=['POST'])
def slack_events():
    json_data = request.json
    # Check for Slack's challenge response
    if "challenge" in json_data:
        return jsonify({'challenge': json_data['challenge']})

    # Extract the event data
    event_message = json_data['event']

    # Check for different types of message events
    try:
        if event_message['type'] == 'message' and 'subtype' not in event_message:
            handle_message(event_message)
        elif event_message['type'] == 'message' and event_message['subtype'] == 'message_replied':
            handle_thread_message(event_message)
    except KeyError as e:
        print(f"Key error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 200

    return jsonify({'status': 'ok'}), 200

def handle_message(message):
    channel_id = message['channel']
    message_text = message['text']
    print(f"Regular message received: {message_text}")
    # Add custom processing logic here

def handle_thread_message(message):
    channel_id = message['channel']
    thread_ts = message['thread_ts']
    parent_message_text = message.get('parent_user_id', {}).get('text', 'N/A')
    reply_count = message.get('reply_count', 0)
    replies = message.get('replies', [])
    print(f"Thread message received in {channel_id}, thread timestamp {thread_ts}, replies count {reply_count}")
    for reply in replies:
        print(f"Reply from {reply['user']} with text: {reply['text']}")
    # Add custom processing logic here

if __name__ == "__main__":
    app.run(port=80)
