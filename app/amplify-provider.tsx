'use client';

import { useEffect } from 'react';
import { Amplify } from 'aws-amplify';
import outputs from '../amplify_outputs.json';

// Configure Amplify with the outputs and existing API Gateway
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
});

export default function AmplifyProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
} 