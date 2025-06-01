const express = require('express');
const cors = require('cors');
const { exec, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const app = express();
const port = 3001;

// Define virtual environment path
const venvPath = path.join(__dirname, 'api-venv');
const venvActivate = process.platform === 'win32' 
  ? path.join(venvPath, 'Scripts', 'activate.bat')
  : path.join(venvPath, 'bin', 'activate');

// Get Python executable path based on environment
function getPythonPath() {
  if (process.platform === 'win32') {
    return path.join(venvPath, 'Scripts', 'python.exe');
  } else {
    return path.join(venvPath, 'bin', 'python');
  }
}

app.use(cors());
app.use(express.json());

// Function to fetch resources directly from the FastAPI app using Python
function fetchFromFastAPI(endpoint) {
    return new Promise((resolve, reject) => {
      try {
        // Create Python script to fetch content from FastAPI
        const fetcherPath = path.join(__dirname, 'fastapi-fetcher.py');
        const fastapiPath = path.join(__dirname, 'amplify/functions/say-hello/index.py');
        
        // Ensure the directory exists
        const fetcherDir = path.dirname(fetcherPath);
        if (!fs.existsSync(fetcherDir)) {
          fs.mkdirSync(fetcherDir, { recursive: true });
        }

        // Write the Python script
        fs.writeFileSync(fetcherPath, `import importlib.util
import json
import sys
import os
import uvicorn
import asyncio
import threading
import time
import requests
import socket

try:
    # Load the Lambda module
    spec = importlib.util.spec_from_file_location("lambda_module", "${fastapiPath.replace(/\\/g, '/')}") 
    lambda_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lambda_module)
    
    # Find FastAPI app in the module
    app = None
    for attr_name in dir(lambda_module):
        attr = getattr(lambda_module, attr_name)
        if str(type(attr)).endswith("fastapi.applications.FastAPI'>"):
            app = attr
            break
    
    if not app:
        print(json.dumps({
            "error": "FastAPI app not found in the Lambda module",
            "content": None,
            "content_type": None
        }))
        sys.exit(1)
    
    # Find a free port
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', 0))
            return s.getsockname()[1]
    
    port = find_free_port()
    
    # Start the server in a thread
    def run_server():
        config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical")
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
    
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
    
    # Wait for server to start up
    time.sleep(1)
    
    # Make the request with SSL verification disabled for local development
    endpoint = "${endpoint}"
    url = f"http://127.0.0.1:{port}{endpoint}"
    response = requests.get(url, verify=False)
    
    # Get the result
    print(json.dumps({
        "success": True,
        "content": response.text,
        "content_type": response.headers.get("content-type", "text/plain"),
        "status_code": response.status_code
    }))
    
    # Stop the server
    thread.join(timeout=1)
    
except Exception as e:
    print(json.dumps({
        "error": str(e),
        "content": None,
        "content_type": None,
        "status_code": 500
    }))
    sys.exit(1)
`);

        // Run the Python script
        const pythonPath = getPythonPath();
        console.log(`Running Python script with: ${pythonPath}`);
        console.log(`Script path: ${fetcherPath}`);
        
        exec(`"${pythonPath}" "${fetcherPath}"`, (error, stdout, stderr) => {
          // Clean up the temporary file
          try {
            if (fs.existsSync(fetcherPath)) {
              fs.unlinkSync(fetcherPath);
            }
          } catch (e) {
            console.error('Failed to clean up fetcher script:', e);
          }
          
          if (error) {
            console.error(`Error executing Python script: ${error}`);
            return reject(error);
          }
          
          if (stderr) {
            console.error(`stderr: ${stderr}`);
            return reject(new Error(stderr));
          }
          
          try {
            // Parse the JSON output from Python
            const result = JSON.parse(stdout.trim());
            
            if (result.error) {
              console.error(`Error fetching from FastAPI: ${result.error}`);
              return reject(new Error(result.error));
            }
            
            resolve({
              content: result.content,
              contentType: result.content_type,
              statusCode: result.status_code
            });
          } catch (e) {
            console.error(`Failed to parse fetcher output: ${stdout}`);
            reject(e);
          }
        });
      } catch (error) {
        console.error('Error in fetchFromFastAPI:', error);
        reject(error);
      }
    });
}

// Helper function to set up virtual environment and install packages
function setupVirtualEnv() {
  return new Promise((resolve, reject) => {
    try {
      console.log('Setting up virtual environment...');
      
      // Check if virtual environment already exists
      if (!fs.existsSync(venvPath)) {
        console.log('Creating new virtual environment...');
        execSync(`python -m venv "${venvPath}"`, { stdio: 'inherit' });
        console.log('Virtual environment created at:', venvPath);
      } else {
        console.log('Using existing virtual environment at:', venvPath);
      }
      
      // Install required packages in the virtual environment
      const requirementsPath = path.join(__dirname, 'amplify/functions/say-hello/requirements.txt');
      
      if (!fs.existsSync(requirementsPath)) {
        console.log('requirements.txt not found, creating it...');
        fs.writeFileSync(requirementsPath, 'fastapi==0.109.2\nmangum==0.17.0\npydantic==2.6.1\nrequests==2.31.0\ncertifi==2024.2.2');
      }
      
      console.log('Installing Python packages in virtual environment...');
      const pipInstallCmd = process.platform === 'win32'
        ? `"${getPythonPath()}" -m pip install -r "${requirementsPath}"`
        : `"${getPythonPath()}" -m pip install -r "${requirementsPath}"`;
      
      execSync(pipInstallCmd, { stdio: 'inherit' });
      console.log('Python packages installed successfully in virtual environment');

      // Install certificates for requests library
      console.log('Installing certificates for requests library...');
      const certInstallCmd = process.platform === 'win32'
        ? `"${getPythonPath()}" -m pip install --upgrade certifi`
        : `"${getPythonPath()}" -m pip install --upgrade certifi`;
      
      execSync(certInstallCmd, { stdio: 'inherit' });
      console.log('Certificates installed successfully');
      
      resolve();
    } catch (error) {
      console.error('Error setting up virtual environment:', error);
      reject(error);
    }
  });
}

// Helper function to discover FastAPI routes
function discoverFastAPIRoutes() {
  return new Promise((resolve, reject) => {
    const routeDiscovererPath = path.join(__dirname, 'route-discoverer.py');
    fs.writeFileSync(routeDiscovererPath, `
import importlib.util
import json
import sys

try:
    # Load the Lambda module
    spec = importlib.util.spec_from_file_location("lambda_module", "${path.join(__dirname, 'amplify/functions/say-hello/index.py').replace(/\\/g, '/')}") 
    lambda_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lambda_module)
    
    # Find FastAPI app in the module
    app = None
    for attr_name in dir(lambda_module):
        attr = getattr(lambda_module, attr_name)
        if str(type(attr)).endswith("fastapi.applications.FastAPI'>"):
            app = attr
            break
    
    if not app:
        print(json.dumps({
            "error": "FastAPI app not found in the Lambda module",
            "routes": []
        }))
        sys.exit(1)
    
    # Extract routes
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            for method in route.methods:
                routes.append({
                    "path": route.path,
                    "method": method,
                    "name": route.name if hasattr(route, "name") else None
                })
    
    print(json.dumps({
        "success": True,
        "routes": routes
    }))
except Exception as e:
    import traceback
    traceback.print_exc()
    print(json.dumps({
        "error": str(e),
        "routes": []
    }))
`);

    // Execute the route discoverer
    const pythonExec = getPythonPath();
    console.log(`Discovering FastAPI routes using Python: ${pythonExec}`);
    
    exec(`"${pythonExec}" "${routeDiscovererPath}"`, (error, stdout, stderr) => {
      // Clean up the temporary file
      try {
        if (fs.existsSync(routeDiscovererPath)) {
          fs.unlinkSync(routeDiscovererPath);
        }
      } catch (e) {
        console.error('Failed to clean up route discoverer:', e);
      }
      
      if (error) {
        console.error(`Route discovery error: ${error}`);
        console.error(`stderr: ${stderr}`);
        return reject(error);
      }
      
      try {
        // Parse the JSON output from Python
        const result = JSON.parse(stdout.trim());
        
        if (result.error) {
          console.error(`Error discovering routes: ${result.error}`);
          return resolve([]);
        }
        
        console.log(`Discovered ${result.routes.length} FastAPI routes:`);
        result.routes.forEach(route => {
          console.log(`  ${route.method} ${route.path} ${route.name ? `(${route.name})` : ''}`);
        });
        
        resolve(result.routes);
      } catch (e) {
        console.error(`Failed to parse route discovery output: ${stdout}`);
        reject(e);
      }
    });
  });
}

// Helper function to create an API Gateway event
function createApiGatewayEvent(method, path, pathParameters = {}, queryStringParameters = {}, body = null, headers = {}) {
  // Make sure path starts with / but doesn't end with / (unless it's just /)
  const normalizedPath = path === '/' ? '/' : path.replace(/\/$/, '');
  
  return {
    version: '2.0',
    routeKey: `${method} ${normalizedPath}`,
    rawPath: normalizedPath,
    rawQueryString: '',
    headers: {
      'accept': 'application/json',
      'content-type': 'application/json',
      'host': `localhost:${port}`,
      ...headers
    },
    requestContext: {
      accountId: 'local',
      apiId: 'local',
      domainName: `localhost:${port}`,
      domainPrefix: 'localhost',
      http: {
        method: method,
        path: normalizedPath,
        protocol: 'HTTP/1.1',
        sourceIp: '127.0.0.1',
        userAgent: 'Express/Local'
      },
      requestId: `local-${Date.now()}`,
      routeKey: `${method} ${normalizedPath}`,
      stage: '$default',
      time: new Date().toISOString(),
      timeEpoch: Date.now()
    },
    pathParameters: pathParameters,
    queryStringParameters: queryStringParameters,
    body: body ? JSON.stringify(body) : null,
    isBase64Encoded: false
  };
}

// Helper function to invoke Lambda using the virtual environment
function invokeLambda(apiGatewayEvent) {
  return new Promise((resolve, reject) => {
    // Write event to a temporary file
    const eventPath = path.join(__dirname, 'temp-event.json');
    fs.writeFileSync(eventPath, JSON.stringify(apiGatewayEvent));
    
    // Create Python script to invoke the Lambda
    const invokerPath = path.join(__dirname, 'lambda-invoker.py');
    fs.writeFileSync(invokerPath, `
import sys
import json
import importlib.util
import traceback

try:
    # Load the Lambda handler
    spec = importlib.util.spec_from_file_location("lambda_module", "${path.join(__dirname, 'amplify/functions/say-hello/index.py').replace(/\\/g, '/')}") 
    lambda_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lambda_module)

    # Load the event
    with open("${eventPath.replace(/\\/g, '/')}") as f:
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
`);
    
    // Execute the Python script using the virtual environment
    const pythonExec = getPythonPath();
    console.log(`Executing with Python: ${pythonExec}`);
    
    exec(`"${pythonExec}" "${invokerPath}"`, (error, stdout, stderr) => {
      console.log("Python output:", stdout);
      if (stderr) console.error("Python stderr:", stderr);
      
      if (error) {
        console.error(`Execution error: ${error}`);
        return reject(error);
      }
      
      try {
        // Extract the result from the output
        const resultMatch = /RESULT: (.+)$/m.exec(stdout);
        if (resultMatch && resultMatch[1]) {
          const result = JSON.parse(resultMatch[1]);
          
          // Handle Lambda proxy integration response
          if (result.statusCode && result.body) {
            let responseBody;
            try {
              responseBody = JSON.parse(result.body);
            } catch (e) {
              responseBody = result.body;
            }
            
            resolve({
              statusCode: result.statusCode,
              headers: result.headers || {},
              body: responseBody
            });
          } else {
            resolve(result);
          }
        } else {
          console.error(`No result found in output: ${stdout}`);
          reject(new Error('No result found in Lambda output'));
        }
      } catch (e) {
        console.error(`Failed to parse Lambda output: ${stdout}`);
        reject(e);
      }
    });
  });
}

// Function to extract path parameters from route template
function extractPathParams(routeTemplate, actualPath) {
  const routeParts = routeTemplate.split('/');
  const pathParts = actualPath.split('/');
  const params = {};
  
  if (routeParts.length !== pathParts.length) {
    return null; // Path structure doesn't match
  }
  
  for (let i = 0; i < routeParts.length; i++) {
    // Check if this part is a parameter (starts with {)
    if (routeParts[i].startsWith('{') && routeParts[i].endsWith('}')) {
      // Extract parameter name without the braces
      const paramName = routeParts[i].slice(1, -1);
      params[paramName] = pathParts[i];
    } else if (routeParts[i] !== pathParts[i]) {
      return null; // Static part doesn't match
    }
  }
  
  return params;
}

// Function to handle requests based on FastAPI routes
function createDynamicRequestHandler(fastApiRoutes) {
  return (req, res, next) => {
    const method = req.method;
    let path = req.path;
    
    // Normalize path (remove trailing slash unless it's just /)
    path = path === '/' ? '/' : path.replace(/\/$/, '');
    
    // Find matching route
    let matchingRoute = null;
    let pathParams = {};
    
    // First try direct match
    matchingRoute = fastApiRoutes.find(r => 
      r.method === method && r.path === path
    );
    
    // If no direct match, try routes with parameters
    if (!matchingRoute) {
      for (const route of fastApiRoutes) {
        if (route.method !== method) continue;
        
        // Only check routes with parameters
        if (route.path.includes('{')) {
          const params = extractPathParams(route.path, path);
          if (params) {
            matchingRoute = route;
            pathParams = params;
            break;
          }
        }
      }
    }
    
    // If we found a matching route, handle it
    if (matchingRoute) {
      console.log(`Handling ${method} request to ${path} with route ${matchingRoute.path}`);
      
      const event = createApiGatewayEvent(
        method, 
        path, 
        pathParams,
        req.query, 
        method !== 'GET' ? req.body : null, 
        req.headers
      );
      
      invokeLambda(event)
        .then(result => {
          console.log(`Result from ${path}:`, result);
          
          if (result.statusCode) {
            Object.entries(result.headers || {}).forEach(([key, value]) => {
              res.set(key, value);
            });
            res.status(result.statusCode).json(result.body);
          } else {
            res.json(result);
          }
        })
        .catch(error => {
          console.error(`Error invoking Lambda for ${path}:`, error);
          res.status(500).json({ error: 'Failed to invoke Lambda function' });
        });
    } else {
      // No matching route found, continue to the next middleware
      next();
    }
  };
}

// Set up virtual environment, discover routes, and start server
setupVirtualEnv()
  .then(() => {
    // Make sure the test client is installed
    const pythonExec = getPythonPath();
    console.log('Installing FastAPI test client dependencies...');
    return new Promise((resolve, reject) => {
      exec(`"${pythonExec}" -m pip install httpx`, (error, stdout, stderr) => {
        if (error) {
          console.error(`Error installing httpx: ${error}`);
          console.error(`stderr: ${stderr}`);
          return reject(error);
        }
        resolve();
      });
    });
  })
  .then(() => discoverFastAPIRoutes())
  .then(fastApiRoutes => {
    // Add special handlers for Swagger UI
    app.get('/docs', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/docs');
        res.set('Content-Type', result.contentType);
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving Swagger UI:', error);
        res.status(500).json({ error: 'Failed to serve Swagger UI' });
      }
    });

    // Handle Swagger UI resources
    app.get('/openapi.json', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/openapi.json');
        res.set('Content-Type', result.contentType);
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving OpenAPI JSON:', error);
        res.status(500).json({ error: 'Failed to serve OpenAPI JSON' });
      }
    });

    // Handle static resources for Swagger UI
    app.get('/docs/oauth2-redirect', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/docs/oauth2-redirect');
        res.set('Content-Type', result.contentType);
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving Swagger UI resource:', error);
        res.status(500).json({ error: 'Failed to serve Swagger UI resource' });
      }
    });

    // Handle Swagger UI static resources 
    app.get('/docs/swagger-ui.css', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/docs/swagger-ui.css');
        res.set('Content-Type', 'text/css');
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving Swagger UI CSS:', error);
        res.status(500).send('/* Failed to load CSS */');
      }
    });

    app.get('/docs/swagger-ui-bundle.js', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/docs/swagger-ui-bundle.js');
        res.set('Content-Type', 'application/javascript');
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving Swagger UI JS bundle:', error);
        res.status(500).send('console.error("Failed to load Swagger UI bundle");');
      }
    });

    app.get('/docs/swagger-ui-standalone-preset.js', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/docs/swagger-ui-standalone-preset.js');
        res.set('Content-Type', 'application/javascript');
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving Swagger UI JS preset:', error);
        res.status(500).send('console.error("Failed to load Swagger UI preset");');
      }
    });

    app.get('/docs/favicon.png', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/docs/favicon.png');
        res.set('Content-Type', 'image/png');
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving Swagger UI favicon:', error);
        res.status(404).send('Not found');
      }
    });
    
    // Handle ReDoc UI
    app.get('/redoc', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/redoc');
        res.set('Content-Type', result.contentType);
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving ReDoc UI:', error);
        res.status(500).json({ error: 'Failed to serve ReDoc UI' });
      }
    });
    
    // ReDoc resources
    app.get('/redoc/redoc.standalone.js', async (req, res) => {
      try {
        const result = await fetchFromFastAPI('/redoc/redoc.standalone.js');
        res.set('Content-Type', 'application/javascript');
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error('Error serving ReDoc JS:', error);
        res.status(500).send('console.error("Failed to load ReDoc JS");');
      }
    });

    // Wild card handler for any other static resources Swagger might need
    app.get('/docs/*', async (req, res, next) => {
      const resourcePath = req.path;
      try {
        const result = await fetchFromFastAPI(resourcePath);
        res.set('Content-Type', result.contentType);
        res.status(result.statusCode).send(result.content);
      } catch (error) {
        console.error(`Error serving Swagger resource ${resourcePath}:`, error);
        next(); // Continue to the next handler
      }
    });

    // Debug route to inspect event format
    app.get('/debug', (req, res) => {
      const event = createApiGatewayEvent('GET', '/debug', {}, req.query, null, req.headers);
      res.json(event);
    });

    // Add FastAPI route handler middleware
    app.use(createDynamicRequestHandler(fastApiRoutes));
    
    // Fallback for routes not found
    app.use((req, res) => {
      res.status(404).json({
        error: 'Not Found',
        message: `No FastAPI route found for ${req.method} ${req.path}`
      });
    });

    // Also create a helper script to run FastAPI directly
    const fastApiRunnerPath = path.join(__dirname, 'run_fastapi.py');
    fs.writeFileSync(fastApiRunnerPath, `
import importlib.util
import sys

# Load the FastAPI app from your Lambda
spec = importlib.util.spec_from_file_location(
    "lambda_module", 
    "${path.join(__dirname, 'amplify/functions/say-hello/index.py').replace(/\\/g, '/')}"
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
`);

    console.log("Created run_fastapi.py script for running FastAPI directly");
    console.log("Run it with: python api-venv/bin/python run_fastapi.py");

    app.listen(port, () => {
      console.log(`Local API server running at http://localhost:${port}`);
      console.log(`Using Python virtual environment at: ${venvPath}`);
      console.log(`Server is dynamically mapped to your FastAPI routes`);
      console.log(`Swagger UI is available at: http://localhost:${port}/docs`);
      console.log(`ReDoc UI is available at: http://localhost:${port}/redoc`);
      console.log(`API debugging is available at: http://localhost:${port}/debug`);
    });
  })
  .catch(error => {
    console.error('Server startup failed:', error);
    console.error('Please check that Python and all required packages are installed');
  });

// Clean up temporary files on exit
process.on('exit', () => {
  try {
    const eventPath = path.join(__dirname, 'temp-event.json');
    const invokerPath = path.join(__dirname, 'lambda-invoker.py');
    if (fs.existsSync(eventPath)) fs.unlinkSync(eventPath);
    if (fs.existsSync(invokerPath)) fs.unlinkSync(invokerPath);
  } catch (e) {
    console.error('Failed to clean up temp files:', e);
  }
});