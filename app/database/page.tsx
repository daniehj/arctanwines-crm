'use client';

import { useState, useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { get, post } from 'aws-amplify/api';
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

interface MigrationStatus {
  table: string;
  exists: boolean;
  columns?: string[];
  status: 'missing' | 'complete' | 'partial';
}

export default function DatabaseDashboard() {
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [migrationStatus, setMigrationStatus] = useState<MigrationStatus[]>([]);
  const [isCheckingSchema, setIsCheckingSchema] = useState(false);
  const [isRunningMigration, setIsRunningMigration] = useState(false);

  const databaseEndpoints = [
    { name: 'Database Connection Test', path: '/db/test', method: 'GET' },
    { name: 'List Wine Batches', path: '/db/wine-batches', method: 'GET' },
    { name: 'List Suppliers', path: '/db/suppliers', method: 'GET' },
    { name: 'List Wines', path: '/db/wines', method: 'GET' },
    { name: 'List Customers (Phase 3)', path: '/db/customers', method: 'GET' },
    { name: 'List Orders (Phase 3)', path: '/db/orders', method: 'GET' },
    { name: 'List Inventory (Phase 3)', path: '/db/inventory', method: 'GET' },
    { name: 'Low Stock Alerts (Phase 3)', path: '/db/inventory/low-stock', method: 'GET' },
    { name: 'List Wine Batch Costs (Phase 3)', path: '/db/wine-batch-costs', method: 'GET' },
    { name: 'List Order Items (Phase 3)', path: '/db/order-items', method: 'GET' },
  ];



  const expectedSchema = [
    {
      table: 'wine_batches',
      columns: ['id', 'batch_number', 'wine_name', 'producer', 'import_date', 'supplier_id', 'total_bottles', 'eur_exchange_rate', 'wine_cost_eur_cents', 'transport_cost_ore', 'customs_fee_ore', 'freight_forwarding_ore', 'status', 'fiken_sync_status', 'total_cost_nok_ore', 'target_price_nok_ore', 'active', 'created_at', 'updated_at']
    },
    {
      table: 'suppliers',
      columns: ['id', 'name', 'country', 'contact_person', 'email', 'phone', 'payment_terms', 'currency', 'tax_id', 'active', 'created_at', 'updated_at']
    },
    {
      table: 'wines',
      columns: ['id', 'name', 'producer', 'region', 'country', 'vintage', 'alcohol_content', 'bottle_size_ml', 'product_category', 'tasting_notes', 'serving_temperature', 'food_pairing', 'organic', 'biodynamic', 'fiken_product_id', 'active', 'created_at', 'updated_at']
    },
    {
      table: 'wine_inventory',
      columns: ['id', 'wine_id', 'batch_id', 'quantity_available', 'quantity_reserved', 'quantity_sold', 'cost_per_bottle_ore', 'selling_price_ore', 'markup_percentage', 'margin_per_bottle_ore', 'minimum_stock_level', 'location', 'best_before_date', 'low_stock_alert', 'active', 'created_at', 'updated_at']
    },
    {
      table: 'wine_batch_costs',
      columns: ['id', 'batch_id', 'cost_type', 'amount_ore', 'currency', 'fiken_account_code', 'payment_date', 'allocation_method', 'invoice_reference', 'active', 'created_at', 'updated_at']
    },
    {
      table: 'customers',
      columns: ['id', 'name', 'customer_type', 'email', 'phone', 'address_line1', 'address_line2', 'postal_code', 'city', 'country', 'organization_number', 'vat_number', 'preferred_delivery_method', 'payment_terms', 'credit_limit_nok_ore', 'marketing_consent', 'newsletter_subscription', 'preferred_language', 'notes', 'fiken_customer_id', 'active', 'created_at', 'updated_at']
    },
    {
      table: 'orders',
      columns: ['id', 'order_number', 'customer_id', 'status', 'payment_status', 'order_date', 'requested_delivery_date', 'confirmed_delivery_date', 'delivered_date', 'delivery_method', 'delivery_address_line1', 'delivery_address_line2', 'delivery_postal_code', 'delivery_city', 'delivery_country', 'delivery_notes', 'subtotal_ore', 'delivery_fee_ore', 'discount_ore', 'vat_ore', 'total_ore', 'payment_terms', 'payment_due_date', 'customer_notes', 'internal_notes', 'fiken_order_id', 'fiken_invoice_number', 'active', 'created_at', 'updated_at']
    },
    {
      table: 'order_items',
      columns: ['id', 'order_id', 'wine_batch_id', 'wine_id', 'quantity', 'unit_price_ore', 'total_price_ore', 'wine_name', 'producer', 'vintage', 'bottle_size_ml', 'discount_percentage', 'discount_ore', 'notes', 'active', 'created_at', 'updated_at']
    }
  ];

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

  const checkSchemaStatus = async () => {
    setIsCheckingSchema(true);
    setMigrationStatus([]);

    for (const schema of expectedSchema) {
      try {
        // Try to query each table to see if it exists
        let endpoint = '';
        switch (schema.table) {
          case 'wine_batches':
            endpoint = '/db/wine-batches';
            break;
          case 'suppliers':
            endpoint = '/db/suppliers';
            break;
          case 'wines':
            endpoint = '/db/wines';
            break;
          case 'customers':
            endpoint = '/db/customers';
            break;
          case 'orders':
            endpoint = '/db/orders';
            break;
          case 'wine_inventory':
            endpoint = '/db/inventory';
            break;
          case 'wine_batch_costs':
            endpoint = '/db/wine-batch-costs';
            break;
          case 'order_items':
            endpoint = '/db/order-items';
            break;
          default:
            endpoint = `/db/${schema.table.replace('_', '-')}`;
        }

        const response = await get({
          apiName: 'arctanwines-crm-api',
          path: endpoint,
          options: {
            headers: {
              'Content-Type': 'application/json',
            },
          },
        }).response;

        await response.body.json();
        
        setMigrationStatus(prev => [...prev, {
          table: schema.table,
          exists: true,
          columns: schema.columns,
          status: 'complete'
        }]);
      } catch (error: any) {
        const errorMsg = error.message || '';
        if (errorMsg.includes('does not exist') || errorMsg.includes('42P01')) {
          setMigrationStatus(prev => [...prev, {
            table: schema.table,
            exists: false,
            columns: schema.columns,
            status: 'missing'
          }]);
        } else {
          setMigrationStatus(prev => [...prev, {
            table: schema.table,
            exists: true,
            columns: schema.columns,
            status: 'partial'
          }]);
        }
      }
    }
    
    setIsCheckingSchema(false);
  };

  const runMigration = async () => {
    setIsRunningMigration(true);
    
    try {
      const response = await post({
        apiName: 'arctanwines-crm-api',
        path: '/db/migrate',
        options: {
          headers: {
            'Content-Type': 'application/json',
          },
        },
      }).response;

      const body = await response.body.json();
      console.log('Migration result:', body);
      
      // Refresh schema status after migration
      setTimeout(() => {
        checkSchemaStatus();
      }, 1000);
      
      alert(`Migration completed: ${(body as any)?.message || 'Migration successful'}`);
    } catch (error: any) {
      console.error('Migration error:', error);
      alert(`Migration failed: ${error.message || error}`);
    }
    
    setIsRunningMigration(false);
  };

  const runAllTests = async () => {
    setTestResults([]);
    
    for (const endpoint of databaseEndpoints) {
      await runTest(endpoint);
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  };

  useEffect(() => {
    checkSchemaStatus();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'complete': return 'bg-green-100 text-green-800';
      case 'missing': return 'bg-red-100 text-red-800';
      case 'partial': return 'bg-yellow-100 text-yellow-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'complete': return '✅';
      case 'missing': return '❌';
      case 'partial': return '⚠️';
      default: return '❔';
    }
  };

  const pendingMigrations = migrationStatus.filter(s => s.status === 'missing' || s.status === 'partial').length;
  const completedMigrations = migrationStatus.filter(s => s.status === 'complete').length;

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
                      Database Dashboard
                    </h1>
                    <p className="text-sm text-gray-600 mt-1">
                      Database schema, migrations, and testing
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <nav className="flex space-x-4">
                      <Link href="/dashboard" className="text-blue-600 hover:text-blue-800">
                        Main Dashboard
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

            {/* Migration Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <span className="text-green-600 font-semibold">{completedMigrations}</span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Completed Tables</p>
                    <p className="text-lg font-semibold text-gray-900">{completedMigrations} / {migrationStatus.length}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                      <span className="text-red-600 font-semibold">{pendingMigrations}</span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Pending Migrations</p>
                    <p className="text-lg font-semibold text-gray-900">{pendingMigrations} tables need migration</p>
                  </div>
                </div>
              </div>

              <div className="bg-white shadow rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Migration Status</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {pendingMigrations > 0 ? 'Action Required' : 'Up to Date'}
                    </p>
                  </div>
                  <button
                    onClick={runMigration}
                    disabled={isRunningMigration || pendingMigrations === 0}
                    className={`px-4 py-2 rounded-md text-white font-medium ${
                      isRunningMigration || pendingMigrations === 0
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-green-600 hover:bg-green-700'
                    }`}
                  >
                    {isRunningMigration ? 'Running...' : pendingMigrations > 0 ? 'Run Migration' : 'No Migration Needed'}
                  </button>
                </div>
              </div>
            </div>

            {/* Migration Status */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h2 className="text-lg font-medium text-gray-900">Database Schema Status</h2>
                  <button
                    onClick={checkSchemaStatus}
                    disabled={isCheckingSchema}
                    className={`px-4 py-2 rounded-md text-white font-medium ${
                      isCheckingSchema
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {isCheckingSchema ? 'Checking...' : 'Refresh Schema'}
                  </button>
                </div>
              </div>
              <div className="px-6 py-4">
                <div className="space-y-4">
                  {migrationStatus.map((table) => (
                    <div key={table.table} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-3">
                          <span className="text-lg">{getStatusIcon(table.status)}</span>
                          <h3 className="text-lg font-medium text-gray-900">{table.table}</h3>
                        </div>
                        <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(table.status)}`}>
                          {table.status}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">
                        <p className="mb-2">Expected columns ({table.columns?.length || 0}):</p>
                        <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
                          {table.columns?.map((column) => (
                            <span key={column} className="bg-gray-100 px-2 py-1 rounded text-xs">
                              {column}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Database Tests */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                  <h2 className="text-lg font-medium text-gray-900">Database Tests</h2>
                  <button
                    onClick={runAllTests}
                    className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700"
                  >
                    Run All DB Tests
                  </button>
                </div>
              </div>
              <div className="px-6 py-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
                  {databaseEndpoints.map((endpoint) => (
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

                {/* Test Results */}
                <div className="space-y-3">
                  {testResults.map((result, index) => (
                    <div key={index} className="border rounded-lg p-4">
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
                  ))}
                  {testResults.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      No tests run yet. Click "Run All DB Tests" or individual test buttons above.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </Authenticator>
  );
} 