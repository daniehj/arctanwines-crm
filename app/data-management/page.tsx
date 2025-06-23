'use client';

import { useState, useEffect } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { post, get } from 'aws-amplify/api';
import '@aws-amplify/ui-react/styles.css';
import Link from 'next/link';

interface SupplierForm {
  name: string;
  country: string;
  contact_person: string;
  email: string;
  phone: string;
  payment_terms: number;
  currency: string;
  tax_id: string;
}

interface WineForm {
  name: string;
  producer: string;
  region: string;
  country: string;
  vintage: number;
  alcohol_content: number;
  bottle_size_ml: number;
  product_category: string;
  tasting_notes: string;
  organic: boolean;
  biodynamic: boolean;
}

interface WineBatchForm {
  batch_number: string;
  wine_name: string;
  producer: string;
  total_bottles: number;
  total_cost_nok_ore: number;
  target_price_nok_ore: number;
}

interface CustomerForm {
  name: string;
  customer_type: string;
  email: string;
  phone: string;
  address_line1: string;
  address_line2: string;
  postal_code: string;
  city: string;
  country: string;
  organization_number: string;
  vat_number: string;
  preferred_delivery_method: string;
  payment_terms: number;
  credit_limit_nok_ore: number;
  marketing_consent: boolean;
  newsletter_subscription: boolean;
  preferred_language: string;
  notes: string;
}

export default function DataManagement() {
  const [activeTab, setActiveTab] = useState<'suppliers' | 'wines' | 'batches' | 'customers'>('suppliers');
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [wines, setWines] = useState<any[]>([]);
  const [batches, setBatches] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [supplierForm, setSupplierForm] = useState<SupplierForm>({
    name: '',
    country: '',
    contact_person: '',
    email: '',
    phone: '',
    payment_terms: 30,
    currency: 'EUR',
    tax_id: ''
  });

  const [wineForm, setWineForm] = useState<WineForm>({
    name: '',
    producer: '',
    region: '',
    country: '',
    vintage: 0,
    alcohol_content: 0,
    bottle_size_ml: 750,
    product_category: '',
    tasting_notes: '',
    organic: false,
    biodynamic: false
  });

  const [batchForm, setBatchForm] = useState<WineBatchForm>({
    batch_number: '',
    wine_name: '',
    producer: '',
    total_bottles: 0,
    total_cost_nok_ore: 0,
    target_price_nok_ore: 0
  });

  const [customerForm, setCustomerForm] = useState<CustomerForm>({
    name: '',
    customer_type: 'individual',
    email: '',
    phone: '',
    address_line1: '',
    address_line2: '',
    postal_code: '',
    city: '',
    country: 'Norway',
    organization_number: '',
    vat_number: '',
    preferred_delivery_method: '',
    payment_terms: 0,
    credit_limit_nok_ore: 0,
    marketing_consent: false,
    newsletter_subscription: false,
    preferred_language: 'no',
    notes: ''
  });

  const loadData = async () => {
    try {
      // Load suppliers
      const suppliersResponse = await get({
        apiName: 'arctanwines-crm-api',
        path: '/db/suppliers'
      }).response;
      const suppliersData = await suppliersResponse.body.json();
      setSuppliers((suppliersData as any)?.suppliers || []);

      // Load wines
      const winesResponse = await get({
        apiName: 'arctanwines-crm-api',
        path: '/db/wines'
      }).response;
      const winesData = await winesResponse.body.json();
      setWines((winesData as any)?.wines || []);

      // Load batches
      const batchesResponse = await get({
        apiName: 'arctanwines-crm-api',
        path: '/db/wine-batches'
      }).response;
      const batchesData = await batchesResponse.body.json();
      setBatches((batchesData as any)?.wine_batches || []);

      // Load customers
      try {
        const customersResponse = await get({
          apiName: 'arctanwines-crm-api',
          path: '/db/customers'
        }).response;
        const customersData = await customersResponse.body.json();
        setCustomers((customersData as any)?.customers || []);
      } catch (customerError) {
        console.error('Error loading customers (Phase 3 feature):', customerError);
        setCustomers([]);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const createSupplier = async () => {
    setIsSubmitting(true);
    try {
      const response = await post({
        apiName: 'arctanwines-crm-api',
        path: '/db/suppliers',
        options: {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(supplierForm)
        },
      }).response;

      await response.body.json();
      
      // Reset form
      setSupplierForm({
        name: '', country: '', contact_person: '', email: '', phone: '',
        payment_terms: 30, currency: 'EUR', tax_id: ''
      });
      
      // Reload data
      await loadData();
      alert('Supplier created successfully!');
    } catch (error: any) {
      alert(`Failed to create supplier: ${error.message || error}`);
    }
    setIsSubmitting(false);
  };

  const createWine = async () => {
    setIsSubmitting(true);
    try {
      const response = await post({
        apiName: 'arctanwines-crm-api',
        path: '/db/wines',
        options: {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(wineForm)
        },
      }).response;

      await response.body.json();
      
      // Reset form
      setWineForm({
        name: '', producer: '', region: '', country: '', vintage: 0,
        alcohol_content: 0, bottle_size_ml: 750, product_category: '',
        tasting_notes: '', organic: false, biodynamic: false
      });
      
      // Reload data
      await loadData();
      alert('Wine created successfully!');
    } catch (error: any) {
      alert(`Failed to create wine: ${error.message || error}`);
    }
    setIsSubmitting(false);
  };

  const createBatch = async () => {
    setIsSubmitting(true);
    try {
      const response = await post({
        apiName: 'arctanwines-crm-api',
        path: '/db/wine-batches',
        options: {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(batchForm)
        },
      }).response;

      await response.body.json();
      
      // Reset form
      setBatchForm({
        batch_number: '', wine_name: '', producer: '',
        total_bottles: 0, total_cost_nok_ore: 0, target_price_nok_ore: 0
      });
      
      // Reload data
      await loadData();
      alert('Wine batch created successfully!');
    } catch (error: any) {
      alert(`Failed to create wine batch: ${error.message || error}`);
    }
    setIsSubmitting(false);
  };

  const createCustomer = async () => {
    setIsSubmitting(true);
    try {
      const response = await post({
        apiName: 'arctanwines-crm-api',
        path: '/db/customers',
        options: {
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(customerForm)
        },
      }).response;

      await response.body.json();
      
      // Reset form
      setCustomerForm({
        name: '', customer_type: 'individual', email: '', phone: '',
        address_line1: '', address_line2: '', postal_code: '', city: '',
        country: 'Norway', organization_number: '', vat_number: '',
        preferred_delivery_method: '', payment_terms: 0, credit_limit_nok_ore: 0,
        marketing_consent: false, newsletter_subscription: false,
        preferred_language: 'no', notes: ''
      });
      
      // Reload data
      await loadData();
      alert('Customer created successfully!');
    } catch (error: any) {
      alert(`Failed to create customer: ${error.message || error}`);
    }
    setIsSubmitting(false);
  };

  const formatCurrency = (amount: number) => {
    return `${(amount / 100).toFixed(2)} NOK`;
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
                      Data Management
                    </h1>
                    <p className="text-sm text-gray-600 mt-1">
                      Create and manage suppliers, wines, and wine batches
                    </p>
                  </div>
                  <div className="flex items-center space-x-4">
                    <nav className="flex space-x-4">
                      <Link href="/dashboard" className="text-blue-600 hover:text-blue-800">
                        Main Dashboard
                      </Link>
                      <Link href="/database" className="text-blue-600 hover:text-blue-800">
                        Database Dashboard
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

            {/* Tabs */}
            <div className="bg-white shadow rounded-lg mb-6">
              <div className="border-b border-gray-200">
                <nav className="-mb-px flex">
                  <button
                    onClick={() => setActiveTab('suppliers')}
                    className={`py-4 px-6 border-b-2 font-medium text-sm ${
                      activeTab === 'suppliers'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Suppliers ({suppliers.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('wines')}
                    className={`py-4 px-6 border-b-2 font-medium text-sm ${
                      activeTab === 'wines'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Wines ({wines.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('batches')}
                    className={`py-4 px-6 border-b-2 font-medium text-sm ${
                      activeTab === 'batches'
                        ? 'border-blue-500 text-blue-600'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    Wine Batches ({batches.length})
                  </button>
                </nav>
              </div>

              {/* Suppliers Tab */}
              {activeTab === 'suppliers' && (
                <div className="p-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Create Supplier Form */}
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Supplier</h3>
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
                            <input
                              type="text"
                              value={supplierForm.name}
                              onChange={(e) => setSupplierForm({...supplierForm, name: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Bodega Acediano"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Country *</label>
                            <input
                              type="text"
                              value={supplierForm.country}
                              onChange={(e) => setSupplierForm({...supplierForm, country: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Spain"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Contact Person</label>
                            <input
                              type="text"
                              value={supplierForm.contact_person}
                              onChange={(e) => setSupplierForm({...supplierForm, contact_person: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Juan Rodriguez"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                            <input
                              type="email"
                              value={supplierForm.email}
                              onChange={(e) => setSupplierForm({...supplierForm, email: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="juan@bodegaacediano.com"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                            <input
                              type="text"
                              value={supplierForm.phone}
                              onChange={(e) => setSupplierForm({...supplierForm, phone: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="+34 123 456 789"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Payment Terms (days)</label>
                            <input
                              type="number"
                              value={supplierForm.payment_terms}
                              onChange={(e) => setSupplierForm({...supplierForm, payment_terms: parseInt(e.target.value) || 30})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                          </div>
                        </div>
                        <button
                          onClick={createSupplier}
                          disabled={!supplierForm.name || !supplierForm.country || isSubmitting}
                          className={`w-full px-4 py-2 rounded-md text-white font-medium ${
                            !supplierForm.name || !supplierForm.country || isSubmitting
                              ? 'bg-gray-400 cursor-not-allowed'
                              : 'bg-blue-600 hover:bg-blue-700'
                          }`}
                        >
                          {isSubmitting ? 'Creating...' : 'Create Supplier'}
                        </button>
                      </div>
                    </div>

                    {/* Suppliers List */}
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">Existing Suppliers</h3>
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {suppliers.map((supplier) => (
                          <div key={supplier.id} className="border rounded-lg p-4">
                            <h4 className="font-medium text-gray-900">{supplier.name}</h4>
                            <p className="text-sm text-gray-600">{supplier.country}</p>
                            {supplier.contact_person && (
                              <p className="text-sm text-gray-600">Contact: {supplier.contact_person}</p>
                            )}
                            {supplier.email && (
                              <p className="text-sm text-gray-600">Email: {supplier.email}</p>
                            )}
                            <p className="text-sm text-gray-600">
                              Payment Terms: {supplier.payment_terms} days • Currency: {supplier.currency}
                            </p>
                          </div>
                        ))}
                        {suppliers.length === 0 && (
                          <p className="text-gray-500 text-center py-8">No suppliers yet. Create your first supplier!</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Wines Tab */}
              {activeTab === 'wines' && (
                <div className="p-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Create Wine Form */}
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Wine</h3>
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Wine Name *</label>
                            <input
                              type="text"
                              value={wineForm.name}
                              onChange={(e) => setWineForm({...wineForm, name: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="ACEDIANO Monastrell"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Producer *</label>
                            <input
                              type="text"
                              value={wineForm.producer}
                              onChange={(e) => setWineForm({...wineForm, producer: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Bodega Acediano"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Country *</label>
                            <input
                              type="text"
                              value={wineForm.country}
                              onChange={(e) => setWineForm({...wineForm, country: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="Spain"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Vintage</label>
                            <input
                              type="number"
                              value={wineForm.vintage || ''}
                              onChange={(e) => setWineForm({...wineForm, vintage: parseInt(e.target.value) || 0})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="2022"
                            />
                          </div>
                        </div>
                        <button
                          onClick={createWine}
                          disabled={!wineForm.name || !wineForm.producer || !wineForm.country || isSubmitting}
                          className={`w-full px-4 py-2 rounded-md text-white font-medium ${
                            !wineForm.name || !wineForm.producer || !wineForm.country || isSubmitting
                              ? 'bg-gray-400 cursor-not-allowed'
                              : 'bg-purple-600 hover:bg-purple-700'
                          }`}
                        >
                          {isSubmitting ? 'Creating...' : 'Create Wine'}
                        </button>
                      </div>
                    </div>

                    {/* Wines List */}
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">Existing Wines</h3>
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {wines.map((wine) => (
                          <div key={wine.id} className="border rounded-lg p-4">
                            <h4 className="font-medium text-gray-900">{wine.name}</h4>
                            <p className="text-sm text-gray-600">
                              {wine.producer} • {wine.country} {wine.vintage && `• ${wine.vintage}`}
                            </p>
                            {wine.product_category && (
                              <span className="inline-block bg-gray-100 text-gray-800 text-xs px-2 py-1 rounded mt-1">
                                {wine.product_category}
                              </span>
                            )}
                          </div>
                        ))}
                        {wines.length === 0 && (
                          <p className="text-gray-500 text-center py-8">No wines yet. Create your first wine!</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Wine Batches Tab */}
              {activeTab === 'batches' && (
                <div className="p-6">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Create Batch Form */}
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">Create New Wine Batch</h3>
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Batch Number *</label>
                            <input
                              type="text"
                              value={batchForm.batch_number}
                              onChange={(e) => setBatchForm({...batchForm, batch_number: e.target.value})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="ACEDIANO-2024-001"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">Total Bottles *</label>
                            <input
                              type="number"
                              value={batchForm.total_bottles}
                              onChange={(e) => setBatchForm({...batchForm, total_bottles: parseInt(e.target.value) || 0})}
                              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                              placeholder="144"
                            />
                          </div>
                        </div>
                        <button
                          onClick={createBatch}
                          disabled={!batchForm.batch_number || !batchForm.total_bottles || isSubmitting}
                          className={`w-full px-4 py-2 rounded-md text-white font-medium ${
                            !batchForm.batch_number || !batchForm.total_bottles || isSubmitting
                              ? 'bg-gray-400 cursor-not-allowed'
                              : 'bg-green-600 hover:bg-green-700'
                          }`}
                        >
                          {isSubmitting ? 'Creating...' : 'Create Wine Batch'}
                        </button>
                      </div>
                    </div>

                    {/* Batches List */}
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 mb-4">Existing Wine Batches</h3>
                      <div className="space-y-3 max-h-96 overflow-y-auto">
                        {batches.map((batch) => (
                          <div key={batch.id} className="border rounded-lg p-4">
                            <h4 className="font-medium text-gray-900">{batch.batch_number}</h4>
                            <p className="text-sm text-gray-600">
                              {batch.wine_name} • {batch.producer}
                            </p>
                            <p className="text-sm text-gray-600">
                              Bottles: {batch.total_bottles} • Status: {batch.status}
                            </p>
                            {batch.total_cost_nok_ore > 0 && (
                              <p className="text-sm text-gray-600">
                                Cost: {formatCurrency(batch.total_cost_nok_ore)}
                              </p>
                            )}
                          </div>
                        ))}
                        {batches.length === 0 && (
                          <p className="text-gray-500 text-center py-8">No wine batches yet. Create your first batch!</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </Authenticator>
  );
} 