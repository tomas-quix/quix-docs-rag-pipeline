import os
import traceback
from quixstreams import Application
from quixstreams.sources.kafka import QuixEnvironmentSource
from dotenv import load_dotenv

def main():
    
    # Load environment variables from .env file for local development
    load_dotenv()

    # Optional environment variables
    consumer_group = os.environ.get("consumer_group", "quix_environment_source")

    app = Application(consumer_group=consumer_group, loglevel="DEBUG")
    
    # Setup output topic
    output_topic = app.topic(os.environ["topic"])

    # Get necessary environment variables for Quix input topic
    source_workspace_id = os.environ["source_workspace_id"]
    source_sdk_token = os.environ["source_sdk_token"]
    

    auto_offset_reset = os.environ.get("auto_offset_reset",    "earliest")

    # Setup input topic
    input_topic = QuixEnvironmentSource(
        name=consumer_group,
        app_config=app.config,
        topic=os.environ["topic"],
        quix_workspace_id=source_workspace_id, 
        quix_sdk_token=source_sdk_token,
        auto_offset_reset=auto_offset_reset,
        shutdown_timeout=30,
        consumer_extra_config={'debug': 'all'}
        
    )

    app.add_source(input_topic, output_topic)
    print("CONNECTED!")

    # Start the application
    app._run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR: An error occurred in the application.")
        traceback.print_exc()
        if 'app' in locals():  # Ensure app exists before stopping it
            app.stop()