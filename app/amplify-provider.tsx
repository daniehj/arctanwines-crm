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

  useEffect(() => {
    const configureAmplify = async () => {
      try {
        // Fetch configuration from SSM
        const response = await fetch('/api/config');
        const config = await response.json();

        // Configure Amplify with the outputs and SSM configuration
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
      } catch (error) {
        console.error('Error configuring Amplify:', error);
      }
    };

    configureAmplify();
  }, []);

  if (!isConfigured) {
    return <div>Loading...</div>;
  }

  return <>{children}</>;
} 