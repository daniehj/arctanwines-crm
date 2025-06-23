'use client';

import { useState, useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { getCurrentUser, signOut, fetchAuthSession } from 'aws-amplify/auth';
import { post, get } from 'aws-amplify/api';
import '@aws-amplify/ui-react/styles.css';
import Link from 'next/link';

interface TestResult {
  endpoint: string;
  status: 'loading' | 'success' | 'error';
  response?: any;
  error?: string;
  duration?: number;
  method?: string;
}

export default function DeveloperDashboard() {
  const [user, setUser] = useState<any>(null);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunningTests, setIsRunningTests] = useState(false);

  const generalEndpoints = [
    { name: 'Health Check', path: '/health', method: 'GET' },
    { name: 'Status', path: '/status', method: 'GET' },
    { name: 'Root Endpoint', path: '/', method: 'GET' },
    { name: 'API Test', path: '/api/v1/test', method: 'GET' },
  ];

  const systemEndpoints = [
    { name: 'Config Debug', path: '/config-debug', method: 'GET' },
    { name: 'Environment Debug', path: '/env-debug', method: 'GET' },
    { name: 'VPC Info', path: '/vpc-info', method: 'GET' },
    { name: 'DNS Test', path: '/dns-test', method: 'GET' },
    { name: 'Network Test (AWS Only)', path: '/network-test', method: 'GET' },
    { name: 'Simple Network Test', path: '/network-simple-test', method: 'GET' },
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

    console.log(`Testing endpoint: ${endpoint.name} (${endpoint.method} ${endpoint.path})`);
    console.log('Using Amplify API with IAM authentication...');

    try {
      let response;
      if (endpoint.method === 'GET') {
        response = await get({
          apiName: 'arctanwines-crm-api',
          path: endpoint.path,
          options: {
            headers: {
              'Content-Type': 'application/json',
            },
          },
        }).response;
      } else {
        response = await post({
          apiName: 'arctanwines-crm-api',
          path: endpoint.path,
          options: {
            headers: {
              'Content-Type': 'application/json',
            },
          },
        }).response;
      }

      const duration = Date.now() - startTime;
      const body = await response.body.json();
      console.log('Amplify API successful:', body);

      setTestResults(prev => [
        ...prev.filter(r => r.endpoint !== endpoint.name),
        {
          endpoint: endpoint.name,
          status: 'success',
          response: body,
          duration,
          method: 'Amplify API (IAM signed)'
        }
      ]);
    } catch (error: any) {
      const duration = Date.now() - startTime;
      console.error('API Error:', error);
      
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
    
    const allEndpoints = [...generalEndpoints, ...systemEndpoints];
    for (const endpoint of allEndpoints) {
      await runTest(endpoint);
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setIsRunningTests(false);
  };

  const clearResults = () => {
    setTestResults([]);
  };

  // Simple fetch test function (will fail with IAM auth)
  const testFetch = async () => {
    console.log('Testing with regular fetch (this should fail with IAM auth)...');
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`);
      console.log('Fetch response:', response);
    } catch (error) {
      console.error('Fetch error (expected):', error);
    }
  };

  const debugAuth = async () => {
    try {
      const user = await getCurrentUser();
      console.log('Current user:', user);
      
      const session = await fetchAuthSession();
      console.log('Session:', session);
      console.log('Identity ID:', session.identityId);
      console.log('Tokens exist:', !!session.tokens);
    } catch (error) {
      console.error('Auth debug error:', error);
    }
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
                      Arctan Wines CRM Dashboard
                    </h1>
                    <p className="text-sm text-gray-600 mt-1">
                      Norwegian wine import business management system
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <nav className="flex space-x-4">
                      <Link href="/database" className="text-blue-600 hover:text-blue-800">
                        Database Dashboard
                      </Link>
                      <Link href="/data-management" className="text-blue-600 hover:text-blue-800">
                        Data Management
                      </Link>
                    </nav>
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

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <Link href="/data-management" className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <span className="text-green-600 font-semibold">+</span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-gray-900">Manage Data</h3>
                    <p className="text-sm text-gray-500">Add suppliers, wines, and batches</p>
                  </div>
                </div>
              </Link>

              <Link href="/database" className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-blue-600 font-semibold">DB</span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-gray-900">Database</h3>
                    <p className="text-sm text-gray-500">Schema, migrations, and testing</p>
                  </div>
                </div>
              </Link>

              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <span className="text-purple-600 font-semibold">API</span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-gray-900">API Testing</h3>
                    <p className="text-sm text-gray-500">Test endpoints and debug</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Test Controls */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">API Testing & Debugging</h2>
              </div>
              <div className="px-6 py-4">
                <div className="flex flex-wrap gap-3">
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
                  <button
                    onClick={testFetch}
                    className="px-6 py-2 rounded-md bg-purple-600 text-white hover:bg-purple-700"
                  >
                    Test Fetch
                  </button>
                  <button
                    onClick={debugAuth}
                    className="px-6 py-2 rounded-md bg-orange-600 text-white hover:bg-orange-700"
                  >
                    Debug Auth
                  </button>
                </div>
              </div>
            </div>

            {/* Individual Test Buttons */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">API Endpoint Tests</h2>
              </div>
              <div className="px-6 py-4">
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">General API</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {generalEndpoints.map((endpoint) => (
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
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 mb-2">System & Debug</h3>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {systemEndpoints.map((endpoint) => (
                      <button
                        key={endpoint.name}
                        onClick={() => runTest(endpoint)}
                        className="px-4 py-2 text-sm bg-yellow-50 hover:bg-yellow-100 rounded-md border text-left"
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
                          <pre className="text-xs text-green-700 whitespace-pre-wrap overflow-x-auto max-h-40 overflow-y-auto">
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