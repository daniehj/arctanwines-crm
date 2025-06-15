import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Fetch configuration from the Lambda function
    const response = await fetch('https://ddezqhodb8.execute-api.eu-west-1.amazonaws.com/api/config-debug', {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    
    // Extract Cognito configuration from the response
    return NextResponse.json({
      userPoolId: data.cognito?.userPoolId,
      userPoolClientId: data.cognito?.userPoolClientId,
      identityPoolId: data.cognito?.identityPoolId,
    });
  } catch (error) {
    console.error('Error fetching configuration:', error);
    return NextResponse.json(
      { error: 'Failed to fetch configuration' },
      { status: 500 }
    );
  }
} 