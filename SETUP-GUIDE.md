# AWS Amplify + Cognito + API Gateway + Lambda Setup Guide

This guide documents the complete setup process for a secure, scalable web application with authentication and API backend.

## 🏗️ Architecture Overview

```
Frontend (Next.js) → AWS Amplify → Cognito (Auth) → API Gateway (IAM) → Lambda (FastAPI) → RDS Database
                                      ↓
                                 Identity Pool → Temporary AWS Credentials → Signed API Requests
```

## 📋 Prerequisites

- AWS Account with admin access
- Domain name (optional)
- Git repository
- AWS CLI installed and configured

## 🚀 Step-by-Step Setup

### 1. **Create Cognito User Pool**

#### In AWS Console:
1. **AWS Console** → **Cognito** → **User Pools** → **Create user pool**
2. **Configure sign-in experience:**
   - Sign-in options: ✅ **Email**
   - User name requirements: **Email address**
3. **Configure security requirements:**
   - Password policy: **Cognito defaults** (or customize)
   - Multi-factor authentication: **No MFA** (or enable if needed)
4. **Configure sign-up experience:**
   - Self-registration: ✅ **Enable**
   - Attribute verification: ✅ **Send email verification**
5. **Configure message delivery:**
   - Email provider: **Send email with Cognito** (or configure SES)
6. **Integrate your app:**
   - User pool name: `{app-name}-user-pool`
   - App client name: `{app-name}-client`
   - Client secret: **Don't generate** (for web apps)
7. **Review and create**

#### Save These Values:
- **User Pool ID**: `eu-west-1_XXXXXXXXX`
- **User Pool Client ID**: `xxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2. **Create Cognito Identity Pool**

#### In AWS Console:
1. **AWS Console** → **Cognito** → **Identity Pools** → **Create identity pool**
2. **Configure identity pool:**
   - Identity pool name: `{app-name}-identity-pool`
   - Enable access to unauthenticated identities: **No**
3. **Configure authentication providers:**
   - Authentication providers: **Cognito**
   - User pool ID: `{your-user-pool-id}`
   - App client ID: `{your-user-pool-client-id}`
4. **Configure permissions:**
   - Create new IAM roles: **Yes**
   - Authenticated role name: `{app-name}-authenticated-role`
   - Unauthenticated role name: `{app-name}-unauthenticated-role`
5. **Create identity pool**

#### Save These Values:
- **Identity Pool ID**: `eu-west-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- **Authenticated Role ARN**: `arn:aws:iam::ACCOUNT:role/{app-name}-authenticated-role`

### 3. **Create RDS Database**

#### In AWS Console:
1. **AWS Console** → **RDS** → **Create database**
2. **Choose database creation method:** **Standard create**
3. **Engine options:** **PostgreSQL**
4. **Templates:** **Production** (or Dev/Test for development)
5. **Settings:**
   - DB instance identifier: `{app-name}-prod-db`
   - Master username: `postgres`
   - Master password: **Auto generate** (managed by Secrets Manager)
6. **Instance configuration:** Choose appropriate size
7. **Storage:** Configure as needed
8. **Connectivity:**
   - VPC: **Default VPC** (or create custom)
   - Public access: **No**
   - VPC security group: **Create new** → `{app-name}-db-sg`
9. **Additional configuration:**
   - Initial database name: `{app_name}_prod`
10. **Create database**

#### Save These Values:
- **Database endpoint**: `{app-name}-prod-db.xxxxxxxxx.{region}.rds.amazonaws.com`
- **Database name**: `{app_name}_prod`
- **Secrets Manager ARN**: `arn:aws:secretsmanager:{region}:ACCOUNT:secret:rds-db-credentials/...`

### 4. **Store Configuration in SSM Parameter Store**

#### In AWS Console:
1. **AWS Console** → **Systems Manager** → **Parameter Store**
2. **Create parameters** (all as **SecureString**):

```bash
# Database Configuration
/amplify/{app-name}/database/host = {database-endpoint}
/amplify/{app-name}/database/port = 5432
/amplify/{app-name}/database/name = {app_name}_prod
/amplify/{app-name}/database/username = postgres
/amplify/{app-name}/database/password = {current-password-from-secrets-manager}

# Cognito Configuration
/amplify/{app-name}/cognito/user-pool-id = {user-pool-id}
/amplify/{app-name}/cognito/user-pool-client-id = {user-pool-client-id}
/amplify/{app-name}/cognito/identity-pool-id = {identity-pool-id}
```

### 5. **Disable Secrets Manager Auto-Rotation**

#### In AWS Console:
1. **AWS Console** → **Secrets Manager**
2. **Find your database secret** → **Click on it**
3. **Rotation configuration** tab
4. **Edit rotation** → **Uncheck "Enable automatic rotation"**
5. **Save**

### 6. **Create Lambda Function with Amplify**

#### Setup Amplify Backend:
```bash
# Initialize Amplify (if not already done)
npx create-amplify@latest

# Add API function
npx amplify add function
# Choose: REST API
# Function name: api-main
# Runtime: Python
```

#### Configure Lambda Resource (`amplify/functions/api-main/resource.ts`):
```typescript
import { defineFunction } from '@aws-amplify/backend';

export const apiMain = defineFunction({
  name: 'api-main',
  entry: './handler.py',
  runtime: 'python3.12',
  timeout: 30,
  memoryMB: 1024,
  environment: {
    // Add any environment variables if needed
  },
  // Add IAM permissions for SSM and Secrets Manager
});
```

#### Add IAM Permissions for Lambda:
The Lambda needs permissions to:
- Read SSM parameters: `/amplify/{app-name}/*`
- Access Secrets Manager (if using)
- VPC access (if database is in VPC)

### 7. **Create API Gateway**

#### In AWS Console:
1. **AWS Console** → **API Gateway** → **Create API**
2. **Choose REST API** → **Build**
3. **Settings:**
   - API name: `{app-name}-api`
   - Description: `{App Name} REST API`
4. **Create Resource:**
   - Resource path: `/{proxy+}`
   - Enable CORS: **Yes**
5. **Create Method:**
   - Method: **ANY**
   - Integration type: **Lambda Function**
   - Lambda function: `{your-lambda-function}`
   - Use Lambda Proxy integration: **Yes**
6. **Authorization:**
   - Authorization: **AWS_IAM**
7. **Deploy API:**
   - Stage name: `api`
   - Deploy

#### Save These Values:
- **API Gateway ID**: `xxxxxxxxxx`
- **API Endpoint**: `https://xxxxxxxxxx.execute-api.{region}.amazonaws.com/api`

### 8. **Configure Identity Pool IAM Permissions**

#### In AWS Console:
1. **AWS Console** → **IAM** → **Roles**
2. **Find the authenticated role**: `{app-name}-authenticated-role`
3. **Add permissions** → **Create inline policy**
4. **JSON policy:**

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "execute-api:Invoke"
            ],
            "Resource": [
                "arn:aws:execute-api:{region}:ACCOUNT:{api-gateway-id}/*"
            ]
        }
    ]
}
```

5. **Policy name**: `ApiGatewayInvokePolicy`
6. **Create policy**

### 9. **Setup Frontend Application**

#### Create Next.js App:
```bash
npx create-next-app@latest {app-name}
cd {app-name}
npm install aws-amplify @aws-amplify/ui-react
```

#### Configure Amplify Provider (`app/amplify-provider.tsx`):
```typescript
'use client';

import { useEffect, useState } from 'react';
import { Amplify } from 'aws-amplify';

export default function AmplifyProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isConfigured, setIsConfigured] = useState(false);

  useEffect(() => {
    // Configure Amplify directly in code
    Amplify.configure({
      Auth: {
        Cognito: {
          userPoolId: '{USER_POOL_ID}',
          userPoolClientId: '{USER_POOL_CLIENT_ID}',
          identityPoolId: '{IDENTITY_POOL_ID}',
          signUpVerificationMethod: 'code',
          loginWith: {
            email: true,
          },
        },
      },
      API: {
        REST: {
          '{app-name}-api': {
            endpoint: 'https://{API_GATEWAY_ID}.execute-api.{region}.amazonaws.com/api',
            region: '{region}',
          },
        },
      },
    });
    setIsConfigured(true);
  }, []);

  if (!isConfigured) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
```

#### Wrap App with Provider (`app/layout.tsx`):
```typescript
import AmplifyProvider from './amplify-provider';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AmplifyProvider>
          {children}
        </AmplifyProvider>
      </body>
    </html>
  );
}
```

### 10. **Deploy with AWS Amplify Hosting**

#### In AWS Console:
1. **AWS Console** → **Amplify** → **Create app**
2. **Deploy from Git repository**
3. **Connect repository** → Choose your Git provider
4. **Configure build settings:**
   - Build command: `npm run build`
   - Output directory: `.next`
5. **Environment variables** (if using env vars instead of hardcoded config):
   - `NEXT_PUBLIC_USER_POOL_ID`
   - `NEXT_PUBLIC_USER_POOL_CLIENT_ID`
   - `NEXT_PUBLIC_IDENTITY_POOL_ID`
   - `NEXT_PUBLIC_API_ENDPOINT`
6. **Deploy**

### 11. **Force Track amplify_outputs.json (if using)**

If using `amplify_outputs.json` instead of hardcoded config:

```bash
# Force git to track the file even if in .gitignore
git add -f amplify_outputs.json
git commit -m "Add amplify outputs configuration"
git push
```

## 🧪 Testing the Setup

### Create Test Dashboard:
```typescript
// app/dashboard/page.tsx
'use client';

import { Authenticator } from '@aws-amplify/ui-react';
import { get } from 'aws-amplify/api';

export default function Dashboard() {
  const testAPI = async () => {
    try {
      const response = await get({
        apiName: '{app-name}-api',
        path: '/health',
      }).response;
      const data = await response.body.json();
      console.log('API Response:', data);
    } catch (error) {
      console.error('API Error:', error);
    }
  };

  return (
    <Authenticator>
      {({ signOut, user }) => (
        <div>
          <h1>Welcome {user?.signInDetails?.loginId}</h1>
          <button onClick={testAPI}>Test API</button>
          <button onClick={signOut}>Sign Out</button>
        </div>
      )}
    </Authenticator>
  );
}
```

## 🔧 Common Issues & Solutions

### 1. **"API name is invalid" Error**
- **Cause**: `amplify_outputs.json` not deployed or incorrect API name
- **Solution**: Use hardcoded configuration or force-track the outputs file

### 2. **403 Forbidden on API Calls**
- **Cause**: Identity Pool role lacks API Gateway permissions
- **Solution**: Add `execute-api:Invoke` permission to authenticated role

### 3. **Database Connection Fails**
- **Cause**: Password rotation or incorrect SSM parameters
- **Solution**: Update SSM parameter with current password from Secrets Manager

### 4. **CORS Errors**
- **Cause**: API Gateway CORS not configured
- **Solution**: Enable CORS on API Gateway resources

## 📝 Configuration Checklist

Before going live, verify:

- [ ] User Pool created with email sign-in
- [ ] Identity Pool created and linked to User Pool
- [ ] Database created with Secrets Manager password
- [ ] SSM parameters created for all config values
- [ ] Secrets Manager auto-rotation disabled
- [ ] Lambda function deployed with proper permissions
- [ ] API Gateway created with IAM authentication
- [ ] Identity Pool role has API Gateway invoke permissions
- [ ] Frontend configured with correct IDs and endpoints
- [ ] Amplify hosting configured and deployed

## 🔄 For Next App Setup

1. **Replace all `{app-name}` placeholders** with your new app name
2. **Update region** if different from `eu-west-1`
3. **Follow steps 1-11** in order
4. **Test authentication and API calls**
5. **Deploy and verify everything works**

## 🎯 Key Benefits of This Setup

- ✅ **Secure Authentication**: Cognito handles user management
- ✅ **Signed API Requests**: IAM authentication prevents unauthorized access
- ✅ **Scalable**: Serverless architecture scales automatically
- ✅ **Maintainable**: Configuration centralized in SSM
- ✅ **Cost-effective**: Pay only for what you use
- ✅ **Production-ready**: Follows AWS best practices

---

*This setup provides a robust, secure, and scalable foundation for any web application requiring authentication and API backend.* 