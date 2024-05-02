from flask import Flask, request, jsonify
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import os
import datetime
import json

from flask import Flask, request, Response
from waitress import serve

from setup_logging import get_logger

from quixstreams.platforms.quix import QuixKafkaConfigsBuilder
from quixstreams.kafka import Producer
from quixstreams import Application

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

app = Application()

topic = app.topic(os.environ["output"])
producer = app.get_producer()

logger = get_logger()

app = Flask(__name__)

@app.route('/slack/events', methods=['POST'])
def slack_events():
    json_data = request.json
    print(json_data)
    # Check for Slack's challenge response
    if "challenge" in json_data:
        return jsonify({'challenge': json_data['challenge']})

    channel_id = json_data['event']['channel']

    producer.produce(topic.name, json.dumps(json_data), channel_id)

    return jsonify({'status': 'ok'}), 200

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=80)
