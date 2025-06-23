'use client';

import { useState, useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { getCurrentUser, signOut, fetchAuthSession } from 'aws-amplify/auth';
import { post, get } from 'aws-amplify/api';
import '@aws-amplify/ui-react/styles.css';

interface TestResult {
  endpoint: string;
  status: 'loading' | 'success' | 'error';
  response?: any;
  error?: string;
  duration?: number;
  method?: string;
}

interface WineBatchForm {
  batch_number: string;
  wine_name: string;
  producer: string;
  total_bottles: number;
  total_cost_nok_ore: number;
  target_price_nok_ore: number;
}

export default function DeveloperDashboard() {
  const [user, setUser] = useState<any>(null);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [showBatchForm, setShowBatchForm] = useState(false);
  const [batchForm, setBatchForm] = useState<WineBatchForm>({
    batch_number: '',
    wine_name: '',
    producer: '',
    total_bottles: 0,
    total_cost_nok_ore: 0,
    target_price_nok_ore: 0
  });

  const endpoints = [
    { name: 'Health Check', path: '/health', method: 'GET' },
    { name: 'Status', path: '/status', method: 'GET' },
    { name: 'Database Test', path: '/db/test', method: 'GET' },
    { name: 'Run Migrations', path: '/db/migrate', method: 'POST' },
    { name: 'List Wine Batches', path: '/db/wine-batches', method: 'GET' },
    { name: 'Root Endpoint', path: '/', method: 'GET' },
    { name: 'Config Debug', path: '/config-debug', method: 'GET' },
    { name: 'VPC Info', path: '/vpc-info', method: 'GET' },
    { name: 'DNS Test', path: '/dns-test', method: 'GET' },
    { name: 'Network Test (AWS Only)', path: '/network-test', method: 'GET' },
    { name: 'Simple Network Test', path: '/network-simple-test', method: 'GET' },
    { name: 'API Test', path: '/api/v1/test', method: 'GET' },
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

  // Simple fetch test function (will fail with IAM auth)
  const testFetch = async () => {
    console.log('Testing with regular fetch (this should fail with IAM auth)...');
    try {
      const response = await fetch('https://ddezqhodb8.execute-api.eu-west-1.amazonaws.com/api/health');
      console.log('Fetch response:', response.status, response.statusText);
      if (response.ok) {
        const data = await response.json();
        console.log('Fetch data:', data);
        alert(`Unexpected success: ${JSON.stringify(data)}`);
      } else {
        console.log('Fetch failed as expected with IAM auth');
        alert(`Fetch failed as expected with IAM auth: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      console.error('Fetch error (expected with IAM auth):', error);
      alert(`Fetch failed as expected with IAM auth: ${error}`);
    }
  };

  // Debug authentication and credentials
  const debugAuth = async () => {
    try {
      console.log('=== Authentication Debug ===');
      
      // Check current user
      const user = await getCurrentUser();
      console.log('Current user:', user);
      
      // Check auth session and credentials
      const session = await fetchAuthSession();
      console.log('Auth session:', session);
      console.log('Credentials available:', !!session.credentials);
      console.log('Identity ID:', session.identityId);
      
      if (session.credentials) {
        console.log('AWS Access Key ID:', session.credentials.accessKeyId?.substring(0, 10) + '...');
        console.log('AWS Secret Access Key:', session.credentials.secretAccessKey ? 'Present' : 'Missing');
        console.log('AWS Session Token:', session.credentials.sessionToken ? 'Present' : 'Missing');
      }
      
      alert(`Auth Debug Complete - Check console for details. Credentials: ${!!session.credentials}`);
    } catch (error) {
      console.error('Auth debug error:', error);
      alert(`Auth Debug Failed: ${error}`);
    }
  };

  // Create wine batch
  const createWineBatch = async () => {
    try {
      console.log('Creating wine batch:', batchForm);
      
      const response = await post({
        apiName: 'arctanwines-crm-api',
        path: '/db/wine-batches',
        options: {
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(batchForm)
        },
      }).response;

      const body = await response.body.json();
      console.log('Wine batch created:', body);
      
      // Reset form and hide it
      setBatchForm({
        batch_number: '',
        wine_name: '',
        producer: '',
        total_bottles: 0,
        total_cost_nok_ore: 0,
        target_price_nok_ore: 0
      });
      setShowBatchForm(false);
      
      // Refresh wine batches list
      await runTest({ name: 'List Wine Batches', path: '/db/wine-batches', method: 'GET' });
      
      alert('Wine batch created successfully!');
    } catch (error: any) {
      console.error('Create wine batch error:', error);
      alert(`Failed to create wine batch: ${error.message || error}`);
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
                  <button
                    onClick={() => setShowBatchForm(!showBatchForm)}
                    className="px-6 py-2 rounded-md bg-green-600 text-white hover:bg-green-700"
                  >
                    {showBatchForm ? 'Hide' : 'Add'} Wine Batch
                  </button>
                </div>
              </div>
            </div>

            {/* Wine Batch Form */}
            {showBatchForm && (
              <div className="bg-white shadow rounded-lg mb-6">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-medium text-gray-900">Create Wine Batch</h2>
                </div>
                <div className="px-6 py-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Batch Number *
                      </label>
                      <input
                        type="text"
                        value={batchForm.batch_number}
                        onChange={(e) => setBatchForm({...batchForm, batch_number: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., ACEDIANO-2024-001"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Wine Name *
                      </label>
                      <input
                        type="text"
                        value={batchForm.wine_name}
                        onChange={(e) => setBatchForm({...batchForm, wine_name: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., ACEDIANO Monastrell"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Producer *
                      </label>
                      <input
                        type="text"
                        value={batchForm.producer}
                        onChange={(e) => setBatchForm({...batchForm, producer: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., Bodega Acediano"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Total Bottles *
                      </label>
                      <input
                        type="number"
                        value={batchForm.total_bottles}
                        onChange={(e) => setBatchForm({...batchForm, total_bottles: parseInt(e.target.value) || 0})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 144"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Total Cost (NOK øre)
                      </label>
                      <input
                        type="number"
                        value={batchForm.total_cost_nok_ore}
                        onChange={(e) => setBatchForm({...batchForm, total_cost_nok_ore: parseInt(e.target.value) || 0})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 84000 (840.00 NOK)"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Target Price (NOK øre per bottle)
                      </label>
                      <input
                        type="number"
                        value={batchForm.target_price_nok_ore}
                        onChange={(e) => setBatchForm({...batchForm, target_price_nok_ore: parseInt(e.target.value) || 0})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 18000 (180.00 NOK)"
                      />
                    </div>
                  </div>
                  <div className="mt-4 flex space-x-3">
                    <button
                      onClick={createWineBatch}
                      disabled={!batchForm.batch_number || !batchForm.wine_name || !batchForm.producer || !batchForm.total_bottles}
                      className={`px-4 py-2 rounded-md text-white font-medium ${
                        !batchForm.batch_number || !batchForm.wine_name || !batchForm.producer || !batchForm.total_bottles
                          ? 'bg-gray-400 cursor-not-allowed'
                          : 'bg-green-600 hover:bg-green-700'
                      }`}
                    >
                      Create Wine Batch
                    </button>
                    <button
                      onClick={() => setShowBatchForm(false)}
                      className="px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

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