import { NextResponse } from 'next/server';
import { SSMClient, GetParameterCommand } from '@aws-sdk/client-ssm';

const ssm = new SSMClient({ region: 'eu-west-1' });

export async function GET() {
  try {
    // Fetch parameters from SSM
    const [userPoolId, userPoolClientId, identityPoolId] = await Promise.all([
      ssm.send(new GetParameterCommand({
        Name: '/amplify/arctanwines/cognito/user-pool-id',
        WithDecryption: true,
      })),
      ssm.send(new GetParameterCommand({
        Name: '/amplify/arctanwines/cognito/user-pool-client-id',
        WithDecryption: true,
      })),
      ssm.send(new GetParameterCommand({
        Name: '/amplify/arctanwines/cognito/identity-pool-id',
        WithDecryption: true,
      })),
    ]);

    return NextResponse.json({
      userPoolId: userPoolId.Parameter?.Value,
      userPoolClientId: userPoolClientId.Parameter?.Value,
      identityPoolId: identityPoolId.Parameter?.Value,
    });
  } catch (error) {
    console.error('Error fetching SSM parameters:', error);
    return NextResponse.json(
      { error: 'Failed to fetch configuration' },
      { status: 500 }
    );
  }
} 