'use client';

import { useState, useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { getCurrentUser, signOut } from 'aws-amplify/auth';
import { post, get } from 'aws-amplify/api';
import '@aws-amplify/ui-react/styles.css';

interface TestResult {
  endpoint: string;
  status: 'loading' | 'success' | 'error';
  response?: any;
  error?: string;
  duration?: number;
}

export default function DeveloperDashboard() {
  const [user, setUser] = useState<any>(null);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunningTests, setIsRunningTests] = useState(false);

  const endpoints = [
    { name: 'Health Check', path: '/health', method: 'GET' },
    { name: 'Database Test', path: '/db-test', method: 'GET' },
    { name: 'Config Debug', path: '/config-debug', method: 'GET' },
    { name: 'VPC Info', path: '/vpc-info', method: 'GET' },
    { name: 'Network Test', path: '/network-simple-test', method: 'GET' },
    { name: 'SSM vs Secrets Debug', path: '/ssm-vs-secrets-debug', method: 'GET' },
    { name: 'Environment Debug', path: '/env-debug', method: 'GET' },
  ];

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  const runTest = async (endpoint: { name: string; path: string; method: string }) => {
    const startTime = Date.now();
    
    setTestResults(prev => [
      ...prev.filter(r => r.endpoint !== endpoint.name),
      { endpoint: endpoint.name, status: 'loading' }
    ]);

    try {
      let response;
      if (endpoint.method === 'GET') {
        response = await get({
          apiName: 'arctanwines-crm-api',
          path: endpoint.path,
        }).response;
      } else {
        response = await post({
          apiName: 'arctanwines-crm-api',
          path: endpoint.path,
        }).response;
      }

      const duration = Date.now() - startTime;
      const body = await response.body.json();

      setTestResults(prev => [
        ...prev.filter(r => r.endpoint !== endpoint.name),
        {
          endpoint: endpoint.name,
          status: 'success',
          response: body,
          duration
        }
      ]);
    } catch (error: any) {
      const duration = Date.now() - startTime;
      
      setTestResults(prev => [
        ...prev.filter(r => r.endpoint !== endpoint.name),
        {
          endpoint: endpoint.name,
          status: 'error',
          error: error.message || 'Unknown error',
          duration
        }
      ]);
    }
  };

  const runAllTests = async () => {
    setIsRunningTests(true);
    setTestResults([]);
    
    for (const endpoint of endpoints) {
      await runTest(endpoint);
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setIsRunningTests(false);
  };

  const clearResults = () => {
    setTestResults([]);
  };

  return (
    <Authenticator>
      {({ signOut, user }) => (
        <div className="min-h-screen bg-gray-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            {/* Header */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">
                      Wine CRM Developer Dashboard
                    </h1>
                    <p className="text-sm text-gray-600 mt-1">
                      API Health & Testing Console
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-600">
                      Welcome, {user?.signInDetails?.loginId || 'Developer'}
                    </span>
                    <button
                      onClick={signOut}
                      className="bg-red-600 text-white px-4 py-2 rounded-md text-sm hover:bg-red-700"
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Test Controls */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-4">
                <div className="flex space-x-4">
                  <button
                    onClick={runAllTests}
                    disabled={isRunningTests}
                    className={`px-6 py-2 rounded-md text-white font-medium ${
                      isRunningTests
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {isRunningTests ? 'Running Tests...' : 'Run All Tests'}
                  </button>
                  <button
                    onClick={clearResults}
                    className="px-6 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
                  >
                    Clear Results
                  </button>
                </div>
              </div>
            </div>

            {/* Individual Test Buttons */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Individual Tests</h2>
              </div>
              <div className="px-6 py-4">
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {endpoints.map((endpoint) => (
                    <button
                      key={endpoint.name}
                      onClick={() => runTest(endpoint)}
                      className="px-4 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-md border text-left"
                    >
                      <div className="font-medium">{endpoint.name}</div>
                      <div className="text-xs text-gray-500">
                        {endpoint.method} {endpoint.path}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Test Results */}
            <div className="bg-white shadow rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Test Results</h2>
              </div>
              <div className="divide-y divide-gray-200">
                {testResults.length === 0 ? (
                  <div className="px-6 py-8 text-center text-gray-500">
                    No tests run yet. Click "Run All Tests" or individual test buttons above.
                  </div>
                ) : (
                  testResults.map((result, index) => (
                    <div key={index} className="px-6 py-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-medium text-gray-900">
                          {result.endpoint}
                        </h3>
                        <div className="flex items-center space-x-2">
                          {result.duration && (
                            <span className="text-xs text-gray-500">
                              {result.duration}ms
                            </span>
                          )}
                          <span
                            className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                              result.status === 'success'
                                ? 'bg-green-100 text-green-800'
                                : result.status === 'error'
                                ? 'bg-red-100 text-red-800'
                                : 'bg-yellow-100 text-yellow-800'
                            }`}
                          >
                            {result.status === 'loading' ? 'Testing...' : result.status}
                          </span>
                        </div>
                      </div>
                      
                      {result.status === 'error' && (
                        <div className="bg-red-50 border border-red-200 rounded-md p-3">
                          <p className="text-sm text-red-700">{result.error}</p>
                        </div>
                      )}
                      
                      {result.status === 'success' && result.response && (
                        <div className="bg-green-50 border border-green-200 rounded-md p-3">
                          <pre className="text-xs text-green-700 whitespace-pre-wrap overflow-x-auto">
                            {JSON.stringify(result.response, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </Authenticator>
  );
} 