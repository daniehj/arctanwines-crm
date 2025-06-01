"use client";

import { useState, useEffect } from "react";
import { generateClient } from "aws-amplify/data";
import type { Schema } from "@/amplify/data/resource";
import { Authenticator } from "@aws-amplify/ui-react";
import "./app.css";
import { Amplify } from "aws-amplify";
import outputs from "@/amplify_outputs.json";
import "@aws-amplify/ui-react/styles.css";

// Configure Amplify once
Amplify.configure(outputs);

const client = generateClient<Schema>();

// Set this manually for development/sandbox mode
const LOCAL_API_URL = "http://localhost:3001"; 

export default function Home() {
  const [todos, setTodos] = useState<Array<Schema["Todo"]["type"]>>([]);
  const [apiUrl, setApiUrl] = useState<string>(LOCAL_API_URL);
  const [helloData, setHelloData] = useState<string>("Loading...");
  const [itemsData, setItemsData] = useState<string>("Loading items...");
  const [userData, setUserData] = useState<string>("No user data");
  const [userId, setUserId] = useState<string>("123");
  const [isLocalDev, setIsLocalDev] = useState<boolean>(true);

  // Set API URL based on environment
  useEffect(() => {
    // Check if we're in a local development environment
    const isLocal = window.location.hostname === "localhost" || 
                  window.location.hostname === "127.0.0.1";
    
    setIsLocalDev(isLocal);

    // Try to find API URL in outputs
    let foundApiUrl = '';

    // In Amplify Gen 2, the API URL could be in different locations depending on the setup
    if ('api' in outputs && typeof outputs.api === 'object' && outputs.api !== null) {
      // Check all properties of the api object for an endpoint
      Object.values(outputs.api as Record<string, unknown>).forEach((apiResource: any) => {
        if (apiResource && typeof apiResource === 'object' && 'apiEndpoint' in apiResource) {
          foundApiUrl = (apiResource as { apiEndpoint: string }).apiEndpoint;
        }
      });
    }

    // If we found an API URL in the outputs and we're not in development, use it
    if (foundApiUrl && !isLocal) {
      setApiUrl(foundApiUrl);
      console.log("Using API URL from outputs:", foundApiUrl);
    } else if (isLocal) {
      // Use the local dev URL in development
      console.log("Using local API URL:", LOCAL_API_URL);
    } else {
      console.log("No API URL found in outputs, using local fallback");
    }

    // Log the complete structure for debugging
    console.log("Available outputs:", JSON.stringify(outputs, null, 2));
  }, []);

  function listTodos() {
    client.models.Todo.observeQuery().subscribe({
      next: (data) => setTodos([...data.items]),
    });
  }

  async function fetchHelloWorld() {
    try {
      console.log("Fetching from:", `${apiUrl}/`);
      const response = await fetch(`${apiUrl}/`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setHelloData(JSON.stringify(data, null, 2));
    } catch (error) {
      setHelloData(`Error: ${(error as Error).message}`);
      console.error("API fetch error:", error);
    }
  }

  async function fetchItems() {
    try {
      console.log("Fetching from:", `${apiUrl}/items`);
      const response = await fetch(`${apiUrl}/items`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setItemsData(JSON.stringify(data, null, 2));
    } catch (error) {
      setItemsData(`Error: ${(error as Error).message}`);
      console.error("Items fetch error:", error);
    }
  }

  async function fetchUser() {
    try {
      console.log("Fetching from:", `${apiUrl}/users/${userId}`);
      const response = await fetch(`${apiUrl}/users/${userId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const data = await response.json();
      setUserData(JSON.stringify(data, null, 2));
    } catch (error) {
      setUserData(`Error: ${(error as Error).message}`);
      console.error("User fetch error:", error);
    }
  }

  useEffect(() => {
    listTodos();
  }, []);

  // Load API data once we have the URL
  useEffect(() => {
    if (apiUrl) {
      fetchHelloWorld();
      fetchItems();
    }
  }, [apiUrl]);

  function createTodo() {
    client.models.Todo.create({
      content: window.prompt("Todo content") || "New todo",
    });
  }

  return (
    <Authenticator>
      {({ signOut }) => (
        <main style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
          <h1>FastAPI HTTP Endpoints Demo</h1>

          {isLocalDev && (
            <div style={{ 
              padding: '10px', 
              backgroundColor: '#FFF3CD', 
              border: '1px solid #FFECB5',
              borderRadius: '4px',
              marginBottom: '20px'
            }}>
              <p><strong>Development Mode:</strong> Using local API URL. Production API Gateway URL will be used when deployed.</p>
            </div>
          )}

          {apiUrl ? (
            <p>API URL: <code>{apiUrl}</code></p>
          ) : (
            <p>Loading API URL...</p>
          )}
          
          <div style={{ marginBottom: '30px' }}>
            <h2>Basic Hello World</h2>
            <button 
              onClick={fetchHelloWorld}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: '#4CAF50', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                marginBottom: '10px',
                cursor: 'pointer'
              }}
            >
              Refresh Hello World
            </button>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '10px', 
              borderRadius: '5px',
              overflow: 'auto' 
            }}>
              {helloData}
            </pre>
          </div>
          
          <div style={{ marginBottom: '30px' }}>
            <h2>Get Items</h2>
            <button 
              onClick={fetchItems}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: '#4CAF50', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                marginBottom: '10px',
                cursor: 'pointer'
              }}
            >
              Refresh Items
            </button>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '10px', 
              borderRadius: '5px',
              overflow: 'auto' 
            }}>
              {itemsData}
            </pre>
          </div>
          
          <div style={{ marginBottom: '30px' }}>
            <h2>Get User</h2>
            <div style={{ marginBottom: '10px' }}>
              <input 
                type="text" 
                value={userId} 
                onChange={(e) => setUserId(e.target.value)}
                style={{ 
                  padding: '8px', 
                  borderRadius: '4px',
                  border: '1px solid #ddd',
                  marginRight: '10px'
                }}
                placeholder="Enter user ID"
              />
              <button 
                onClick={fetchUser}
                style={{ 
                  padding: '8px 16px', 
                  backgroundColor: '#2196F3', 
                  color: 'white', 
                  border: 'none', 
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Get User
              </button>
            </div>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '10px', 
              borderRadius: '5px',
              overflow: 'auto' 
            }}>
              {userData}
            </pre>
          </div>
          
          <div style={{ marginBottom: '30px' }}>
            <h2>Todo List</h2>
            <button 
              onClick={createTodo}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: '#9C27B0', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                marginBottom: '10px',
                cursor: 'pointer'
              }}
            >
              + New Todo
            </button>
            <ul style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '10px', 
              borderRadius: '5px',
              listStyle: 'none'
            }}>
              {todos.length === 0 ? (
                <li>No todos yet. Create one!</li>
              ) : (
                todos.map((todo) => (
                  <li key={todo.id} style={{ padding: '8px 0', borderBottom: '1px solid #ddd' }}>
                    {todo.content}
                  </li>
                ))
              )}
            </ul>
          </div>
          
          <button 
            onClick={signOut}
            style={{ 
              padding: '8px 16px', 
              backgroundColor: '#F44336', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Sign out
          </button>
        </main>
      )}
    </Authenticator>
  );
}