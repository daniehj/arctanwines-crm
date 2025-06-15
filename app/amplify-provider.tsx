'use client';

import { useEffect, useState } from 'react';
import { Amplify } from 'aws-amplify';
import outputs from '../amplify_outputs.json';

export default function AmplifyProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isConfigured, setIsConfigured] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const configureAmplify = async () => {
      try {
        // Fetch configuration from API
        const response = await fetch('/api/config');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const config = await response.json();

        if (!config.userPoolId || !config.userPoolClientId || !config.identityPoolId) {
          throw new Error('Missing required configuration values');
        }

        // Configure Amplify with the outputs and configuration
        Amplify.configure({
          ...outputs,
          API: {
            REST: {
              'arctanwines-crm-api': {
                endpoint: 'https://ddezqhodb8.execute-api.eu-west-1.amazonaws.com/api',
                region: 'eu-west-1',
              },
            },
          },
          Auth: {
            Cognito: {
              userPoolId: config.userPoolId,
              userPoolClientId: config.userPoolClientId,
              signUpVerificationMethod: 'code',
              loginWith: {
                email: true,
              },
              identityPoolId: config.identityPoolId,
            },
          },
        });

        setIsConfigured(true);
        setError(null);
      } catch (error) {
        console.error('Error configuring Amplify:', error);
        setError(error instanceof Error ? error.message : 'Failed to configure Amplify');
      }
    };

    configureAmplify();
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full p-6 bg-white rounded-lg shadow-lg">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Configuration Error</h2>
          <p className="text-gray-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!isConfigured) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading configuration...</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
} 