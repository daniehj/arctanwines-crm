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
    // Simple configuration with amplify_outputs.json
    Amplify.configure(outputs);
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