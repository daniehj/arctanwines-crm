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
          userPoolId: 'eu-west-1_zGyN4f7YA',
          userPoolClientId: '34jotc4tl1i9lmeqb9lmnq96dl',
          identityPoolId: 'eu-west-1:3022ae09-6fe2-4273-b2cf-95a4903198f5',
          signUpVerificationMethod: 'code',
          loginWith: {
            email: true,
          },
        },
      },
      API: {
        REST: {
          'arctanwines-crm-api': {
            endpoint: 'https://ddezqhodb8.execute-api.eu-west-1.amazonaws.com',
            region: 'eu-west-1',
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