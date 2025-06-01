
import sys
import json
import importlib.util
import traceback

try:
    # Load the Lambda handler
    spec = importlib.util.spec_from_file_location("lambda_module", "C:/Users/dahjoh/PROG/dinner/ahccustomerportal/amplify/functions/say-hello/index.py") 
    lambda_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lambda_module)

    # Load the event
    with open("C:/Users/dahjoh/PROG/dinner/ahccustomerportal/temp-event.json") as f:
        event = json.load(f)

    # Print the event for debugging
    print("DEBUG_EVENT: " + json.dumps(event))

    # Call the handler
    result = lambda_module.handler(event, {})
    print("RESULT: " + json.dumps(result))
except ImportError as e:
    print("ERROR: Import error: " + str(e))
    traceback.print_exc()
    print("RESULT: " + json.dumps({
        "statusCode": 500,
        "body": json.dumps({
            "error": f"Import error: {str(e)}",
            "message": "Please check the virtual environment has all required packages installed"
        })
    }))
except Exception as e:
    print("ERROR: Execution error: " + str(e))
    traceback.print_exc()
    print("RESULT: " + json.dumps({
        "statusCode": 500,
        "body": json.dumps({
            "error": f"Execution error: {str(e)}"
        })
    }))
