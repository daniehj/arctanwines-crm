## AWS Amplify Next.js (App Router) Starter Template

This repository provides a starter template for creating applications using Next.js (App Router) and AWS Amplify, emphasizing easy setup for authentication, API, and database capabilities.

## Overview

This template equips you with a foundational Next.js application integrated with AWS Amplify, streamlined for scalability and performance. It is ideal for developers looking to jumpstart their project with pre-configured AWS services like Cognito, AppSync, and DynamoDB.

## Installation

Before you begin, make sure you have the following prerequisites installed on your system:

1. Node.js (for the frontend)
2. Python 3.x (for the local API server)

Then, follow these steps:

1. Clone the repository:
```bash
git clone <repository-url>
cd ahccustomerportal
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Set up Python environment:
```bash
# First, ensure Python is installed and in your PATH
python --version  # Should show Python 3.x

# Create and activate virtual environment
python -m venv api-venv

# On Windows (Git Bash):
source api-venv/Scripts/activate

# On Windows (Command Prompt):
api-venv\Scripts\activate

# On macOS/Linux:
source api-venv/bin/activate

```

4. Install Python dependencies:
```bash
pip install fastapi==0.109.2 mangum==0.17.0 pydantic==2.6.1
```

5. Set up a user in the Cognito user pool (choose one method):

   **Method 1: Using AWS Console**
   1. Log in to the AWS Management Console
   2. Navigate to Amazon Cognito
   3. Select your user pool
   4. Click on "Users and groups" in the left sidebar
   5. Click "Create user"
   6. Enter the user's email address and temporary password
   7. Click "Create user"
   8. After creation, you can set a permanent password by selecting the user and clicking "Reset password"

   **Method 2: Using AWS CLI**
   ```bash
   # First, ensure you have the AWS CLI configured with the correct credentials
   aws configure

   # Create a new user in the Cognito user pool
   aws cognito-idp admin-create-user \
     --user-pool-id <your-user-pool-id> \
     --username <desired-username> \
     --temporary-password <temporary-password> \
     --user-attributes Name=email,Value=<user-email> Name=email_verified,Value=true

   # Set the user's permanent password
   aws cognito-idp admin-set-user-password \
     --user-pool-id <your-user-pool-id> \
     --username <username> \
     --password <permanent-password> \
     --permanent
   ```

   Replace the following placeholders:
   - `<your-user-pool-id>`: Your Cognito user pool ID (can be found in the AWS Console)
   - `<desired-username>`: The username for the new user
   - `<temporary-password>`: A temporary password for initial setup
   - `<user-email>`: The email address for the user
   - `<permanent-password>`: The permanent password you want to set

6. Start the local development server:
```bash
# In one terminal, start the local API server
node local-api-server.js

# In another terminal, start the frontend
npm run dev
```

This will set up both the frontend and backend components of the project.

## Features

- **Authentication**: Integration with Amazon Cognito for secure user authentication using the Amplify Authenticator component.
- **API**: FastAPI-based REST API with the following endpoints:
  - `/` - Hello World endpoint
  - `/items` - Returns a list of sample items
  - `/users/{user_id}` - Returns user information
  - `/docs` - Swagger UI documentation
  - `/redoc` - ReDoc documentation
  - `/openapi.json` - OpenAPI schema
- **Local Development**: 
  - Local API server with Swagger UI support
  - Automatic switching between local and production API endpoints
  - Development mode indicator in the UI
- **Frontend Features**:
  - Real-time Todo list with Amplify DataStore
  - API endpoint testing interface
  - User authentication UI
  - Responsive design with modern styling

## AWS Credentials Setup

Before starting development, you'll need to set up your AWS credentials:

1. Install the AWS CLI if you haven't already:
```bash
# For Windows
winget install -e --id Amazon.AWSCLI

# For macOS
brew install awscli

# For Linux
sudo apt install awscli
```

2. Configure your AWS credentials:
```bash
aws configure
```
You'll need to provide:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., us-east-1)
- Default output format (json)

3. Verify your configuration:
```bash
aws sts get-caller-identity
```

4. For local development with Amplify Gen 2, ensure your credentials have the necessary permissions:
- AWSAmplifyAdminFullAccess
- AmazonDynamoDBFullAccess
- AmazonCognitoPowerUser
- AWSAppSyncAdministrator

> **Note**: For production environments, follow the principle of least privilege and only grant the minimum required permissions.

## Development Workflow

### Local Development

Use the sandbox for quick testing:
```bash
npx ampx sandbox
```
This gives you a local environment with real AWS resource emulation.

Use your custom FastAPI local server for enhanced testing:
```bash
node local-api-server.js
```
This provides your FastAPI with Swagger UI support for better API development.

Run your frontend:
```bash
npm run dev
```

### Deployment
When you're ready to deploy:

1. Commit and push to main branch:
```bash
git add .
git commit -m "Your changes"
git push origin main
```

Amplify Hosting automatically deploys your changes through the CI/CD pipeline.

### Advantages of This Workflow

- Local sandbox for quick testing of Amplify resources (DynamoDB, Auth, etc.)
- Custom FastAPI server with Swagger UI for better API development
- Git-based deployments for reliable CI/CD
- No manual deployment commands needed in normal workflow

The beauty of this setup is that you can have multiple environments running in parallel - your production environment, your local sandbox, and your custom FastAPI server - giving you maximum flexibility during development.

## Deploying to AWS

For detailed instructions on deploying your application, refer to the [deployment section](https://docs.amplify.aws/nextjs/start/quickstart/nextjs-app-router-client-components/#deploy-a-fullstack-app-to-aws) of our documentation.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.