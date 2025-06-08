# Wine CRM Developer Dashboard Setup Guide

## 🎯 Overview

This guide sets up a developer dashboard with:
- **Cognito User Pool** authentication
- **IAM-protected API Gateway** 
- **Developer dashboard** for testing all endpoints
- **Automatic credential handling** via Cognito Identity Pool

## 🚀 Step 1: Deploy the Backend

```bash
# Deploy the updated backend with Cognito auth
npx ampx sandbox deploy
```

## 🔐 Step 2: Configure IAM Permissions for Cognito Users

After deployment, you need to manually add IAM permissions for Cognito users to access the API Gateway.

### Get the Identity Pool Role ARN

1. Go to **AWS Console > Cognito > Identity Pools**
2. Find your Amplify-created Identity Pool (named something like `amplify_backend_...`)
3. Click on it and go to **Edit identity pool**
4. Note down the **Authenticated role ARN** (looks like: `arn:aws:iam::ACCOUNT:role/amplify-...`)

### Add API Gateway Permissions

1. Go to **AWS Console > IAM > Roles**
2. Search for the role name from the ARN above
3. Click on the role
4. Click **Add permissions > Attach policies > Create policy**
5. Use the **JSON** tab and paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "execute-api:Invoke",
            "Resource": [
                "arn:aws:execute-api:eu-west-1:*:*/api/*",
                "arn:aws:execute-api:eu-west-1:*:*/api/*/*"
            ]
        }
    ]
}
```

6. **Review policy**:
   - Name: `WineCrmApiGatewayAccess`
   - Description: `Allows Cognito users to access Wine CRM API Gateway`
7. **Create policy**
8. **Attach** this policy to the Cognito authenticated role

## 👥 Step 3: Create Test Users

1. Go to **AWS Console > Cognito > User Pools**
2. Find your Amplify User Pool
3. Go to **Users** tab
4. Click **Create user**
5. Create test users:

```
Username: developer1
Email: developer1@yourcompany.com
Temporary password: TempPass123!
Send welcome email: ✓ (uncheck if email is not real)

Username: admin
Email: admin@yourcompany.com  
Temporary password: AdminPass123!
```

## 🖥️ Step 4: Test the Dashboard

1. **Start the development server**:
```bash
npm run dev
```

2. **Open the dashboard**: http://localhost:3000/dashboard

3. **Sign in** with one of your test users

4. **Update password** on first login (Cognito will prompt)

5. **Test API endpoints** using the dashboard buttons

## 🧪 Step 5: Available Test Endpoints

The dashboard provides testing for these endpoints:

| Endpoint | Description | Expected Result |
|----------|-------------|-----------------|
| `/health` | Basic health check | ✅ Status OK |
| `/db-test` | Database connectivity | ✅ Connection success |
| `/config-debug` | Configuration status | ✅ SSM parameters |
| `/vpc-info` | VPC networking info | ✅ Network details |
| `/network-simple-test` | Network connectivity | ✅ Connection times |
| `/ssm-vs-secrets-debug` | Config comparison | ✅ Parameter status |
| `/env-debug` | Environment variables | ✅ Environment info |

## 🔍 Step 6: Troubleshooting

### "Missing Authentication Token" Error
- ✅ **Good!** This means IAM protection is working
- Make sure you're signed in to the dashboard
- Check that the IAM policy was attached correctly

### "AccessDeniedException" in API calls
- Check the IAM policy resource ARNs match your API Gateway
- Verify the Cognito Identity Pool is correctly configured
- Make sure you're using an authenticated user

### Dashboard doesn't load / Auth errors
- Check that `amplify_outputs.json` is present and up-to-date
- Verify Cognito User Pool is deployed correctly
- Check browser console for specific errors

### API calls fail with network errors
- Verify your API Gateway is deployed and accessible
- Check that the API name in the dashboard matches your deployment
- Ensure VPC endpoints are configured for Lambda

## 🎯 Expected Results

**✅ Successful Setup:**
- Dashboard loads with Cognito login
- Users can sign in and update passwords
- All test endpoints return success status
- Database connection test shows ✅ connection
- Config debug shows all SSM parameters found

**📊 Performance Metrics:**
- Health check: ~500ms 
- Database test: ~2-3 seconds
- Config debug: ~1-2 seconds
- Network tests: ~1 second

## 🔧 Advanced Configuration

### Adding New Test Users

Create additional users via:
1. **AWS Console** (manual)
2. **AWS CLI**:
```bash
aws cognito-idp admin-create-user \
  --user-pool-id YOUR_USER_POOL_ID \
  --username newuser \
  --user-attributes Name=email,Value=newuser@company.com \
  --temporary-password TempPass123!
```

### API Name Configuration

If your API name doesn't match `wine-crm-api`, update it in:
```typescript
// app/dashboard/page.tsx
const response = await get({
  apiName: 'your-actual-api-name', // ← Update this
  path: endpoint.path,
}).response;
```

### Custom Endpoints

Add new endpoints to test by updating the `endpoints` array in `app/dashboard/page.tsx`:

```typescript
const endpoints = [
  // ... existing endpoints
  { name: 'Custom Test', path: '/your-custom-endpoint', method: 'GET' },
];
```

## 🎉 Success!

You now have:
- ✅ **Secure Cognito authentication**
- ✅ **IAM-protected API Gateway**  
- ✅ **Developer dashboard** for testing
- ✅ **Automatic credential handling**
- ✅ **Real-time endpoint testing**

Your developers can now sign in with Cognito credentials and test all API endpoints through the dashboard interface! 🚀 