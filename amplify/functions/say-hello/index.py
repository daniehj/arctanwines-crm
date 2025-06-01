# index.py
from fastapi import FastAPI, HTTPException
from mangum import Mangum
import json

# Create FastAPI app
app = FastAPI(title="Amplify FastAPI Lambda")

# Define your API routes
@app.get("/")
async def root():
    return {"message": "Hello World from FastAPI"}

@app.get("/items")
async def get_items():
    # Example endpoint that returns a list of items
    items = [
        {"id": 1, "name": "Item 1", "description": "Description for Item 1"},
        {"id": 2, "name": "Item 2", "description": "Description for Item 2"},
        {"id": 3, "name": "Item 3", "description": "Description for Item 3"},
    ]
    return {"message": "Items retrieved successfully", "items": items}

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    # This would typically fetch from a database
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    # Mock user data
    return {
        "id": user_id,
        "username": f"user_{user_id}",
        "email": f"user_{user_id}@example.com",
        "createdAt": "2023-01-01T00:00:00Z"
    }

# Create handler for AWS Lambda
handler = Mangum(app)