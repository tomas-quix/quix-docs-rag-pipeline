import os
import datetime
import json
from flask import Flask, request, Response, render_template
from waitress import serve
from pymongo import MongoClient

from setup_logging import get_logger

from quixstreams import Application

# for local dev, load env vars from a .env file
from dotenv import load_dotenv
load_dotenv()

logger = get_logger()

app = Flask(__name__)

database_name=os.environ["DATABASE_NAME"]
collection_name=os.environ["COLLECTION_NAME"]

# Replace with your MongoDB URI
client = MongoClient(os.environ["URI"])
db = client.get_database(database_name)
collection = db.get_collection(collection_name)

@app.route('/', methods=['GET', 'POST'])
def index():
    query = {}
    sort_field = 'timestamp'
    sort_order = -1  # 1 for ascending, -1 for descending
    limit = int(request.form.get('limit', 50))

    if request.method == 'POST':
        # Get filter and sorting parameters from the form
        field_name = request.form.get('field_name')
        field_value = request.form.get('field_value')
        sort_field = request.form.get('sort_field', 'timestamp')
        sort_order = int(request.form.get('sort_order', -1))
        
        if field_name and field_value:
            query = {field_name: field_value}
            
    logger.info(query)

    # Query the collection with the provided filters and sorting
    results = collection.find(query).sort(sort_field, sort_order).limit(limit)

    return render_template('index.html', results=results)

if __name__ == '__main__':
    serve(app, host="0.0.0.0", port=80)