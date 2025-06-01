
import importlib.util
import sys

# Load the FastAPI app from your Lambda
spec = importlib.util.spec_from_file_location(
    "lambda_module", 
    "C:/Users/dahjoh/PROG/dinner/ahccustomerportal/amplify/functions/say-hello/index.py"
)
lambda_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lambda_module)

# Find the FastAPI app
app = None
for attr_name in dir(lambda_module):
    attr = getattr(lambda_module, attr_name)
    if str(type(attr)).endswith("fastapi.applications.FastAPI'>"):
        app = attr
        break

if not app:
    print("FastAPI app not found!")
    sys.exit(1)

# Run the app directly
import uvicorn
if __name__ == "__main__":
    print("Running FastAPI directly with Uvicorn")
    print("To see the Swagger UI docs, visit: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
