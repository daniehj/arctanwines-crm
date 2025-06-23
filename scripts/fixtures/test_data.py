#!/usr/bin/env python3
"""
Test Fixtures for Migration Testing
Provides realistic Norwegian wine import CRM test data
"""

from datetime import datetime, timedelta
import uuid

def generate_wine_batch_fixtures():
    """Generate realistic Norwegian wine batch test data for current schema"""
    fixtures = []
    
    # Italian wines - common in Norwegian import
    fixtures.extend([
        {
            'id': 'batch-' + str(uuid.uuid4())[:8],
            'batch_number': 'FONT-BAR-2024-001',
            'wine_name': 'Barolo DOCG',
            'producer': 'Fontanafredda',
            'total_bottles': 12,
            'status': 'AVAILABLE',
            'total_cost_nok_ore': 582600,  # 5826.00 NOK (485.50 per bottle)
            'target_price_nok_ore': 64900,  # 649.00 NOK per bottle
            'import_date': datetime.now() - timedelta(days=30),
            'active': True,
            'created_at': datetime.now() - timedelta(days=30),
            'updated_at': datetime.now() - timedelta(days=5)
        },
        {
            'id': 'batch-' + str(uuid.uuid4())[:8],
            'batch_number': 'BROL-CC-2024-002',
            'wine_name': 'Chianti Classico DOCG',
            'producer': 'Castello di Brolio',
            'total_bottles': 24,
            'status': 'AVAILABLE',
            'total_cost_nok_ore': 588000,  # 5880.00 NOK (245.00 per bottle)
            'target_price_nok_ore': 32900,  # 329.00 NOK per bottle
            'import_date': datetime.now() - timedelta(days=20),
            'active': True,
            'created_at': datetime.now() - timedelta(days=20),
            'updated_at': datetime.now() - timedelta(days=2)
        }
    ])
    
    # French wines
    fixtures.extend([
        {
            'id': 'batch-' + str(uuid.uuid4())[:8],
            'batch_number': 'FEVRE-CHB-2024-003',
            'wine_name': 'Chablis Premier Cru',
            'producer': 'Domaine William Fèvre',
            'total_bottles': 6,
            'status': 'ORDERED',
            'total_cost_nok_ore': 231000,  # 2310.00 NOK (385.00 per bottle)
            'target_price_nok_ore': 52500,  # 525.00 NOK per bottle
            'import_date': datetime.now() - timedelta(days=15),
            'active': True,
            'created_at': datetime.now() - timedelta(days=15),
            'updated_at': datetime.now() - timedelta(days=1)
        }
    ])
    
    # Spanish wines
    fixtures.extend([
        {
            'id': 'batch-' + str(uuid.uuid4())[:8],
            'batch_number': 'VEGA-RDD-2024-004',
            'wine_name': 'Ribera del Duero Crianza',
            'producer': 'Vega Sicilia',
            'total_bottles': 18,
            'status': 'SOLD_OUT',
            'total_cost_nok_ore': 585000,  # 5850.00 NOK (325.00 per bottle)
            'target_price_nok_ore': 45000,  # 450.00 NOK per bottle
            'import_date': datetime.now() - timedelta(days=45),
            'active': True,
            'created_at': datetime.now() - timedelta(days=45),
            'updated_at': datetime.now() - timedelta(days=10)
        }
    ])
    
    return fixtures

def generate_customer_fixtures():
    """Generate realistic Norwegian customer test data"""
    fixtures = []
    
    # Norwegian restaurants and wine bars
    fixtures.extend([
        {
            'id': 'cust-' + str(uuid.uuid4())[:8],
            'organization_number': '123456789',
            'name': 'Maaemo Restaurant AS',
            'customer_type': 'fine_dining',
            'contact_person': 'Esben Holmboe Bang',
            'email': 'wine@maaemo.no',
            'phone': '+47 22 17 99 69',
            'address_line1': 'Schweigaards gate 15B',
            'postal_code': '0191',
            'city': 'Oslo',
            'country': 'Norway',
            'vat_number': 'NO123456789MVA',
            'payment_terms': 30,
            'credit_limit_nok_ore': 10000000,  # 100,000 NOK
            'marketing_consent': True,
            'newsletter_subscription': True,
            'preferred_language': 'no',
            'notes': '3 Michelin star restaurant, premium wine selection',
            'fiken_customer_id': None,
            'active': True,
            'created_at': datetime.now() - timedelta(days=180),
            'updated_at': datetime.now() - timedelta(days=30)
        },
        {
            'id': 'cust-' + str(uuid.uuid4())[:8],
            'organization_number': '987654321',
            'name': 'Theatercaféen AS',
            'customer_type': 'restaurant',
            'contact_person': 'Lars Hansen',
            'email': 'wine@theatercafeen.no',
            'phone': '+47 22 82 40 50',
            'address_line1': 'Stortingsgata 24-26',
            'postal_code': '0117',
            'city': 'Oslo',
            'country': 'Norway',
            'vat_number': 'NO987654321MVA',
            'payment_terms': 14,
            'credit_limit_nok_ore': 5000000,  # 50,000 NOK
            'marketing_consent': True,
            'newsletter_subscription': False,
            'preferred_language': 'no',
            'notes': 'Historic restaurant, diverse wine program',
            'fiken_customer_id': None,
            'active': True,
            'created_at': datetime.now() - timedelta(days=120),
            'updated_at': datetime.now() - timedelta(days=15)
        },
        {
            'id': 'cust-' + str(uuid.uuid4())[:8],
            'organization_number': '456789123',
            'company_name': 'Vinmonopolet Avdeling Frogner',
            'contact_person': 'Kari Nordström',
            'email': 'frogner@vinmonopolet.no',
            'phone': '+47 815 35 110',
            'address': 'Bygdøy Allé 60, 0265 Oslo',
            'postal_code': '0265',
            'city': 'Oslo',
            'vat_number': 'NO456789123MVA',
            'payment_terms_days': 7,
            'discount_percentage': 0.0,
            'customer_category': 'retail',
            'notes': 'State monopoly retail location',
            'fiken_contact_id': None,
            'created_at': datetime.now() - timedelta(days=90),
            'updated_at': datetime.now() - timedelta(days=5)
        }
    ])
    
    return fixtures

def generate_order_fixtures(customer_ids, wine_batch_ids):
    """Generate realistic order test data"""
    if not customer_ids or not wine_batch_ids:
        return []
    
    fixtures = []
    
    # Recent order
    order_1 = {
        'id': 'order-' + str(uuid.uuid4())[:8],
        'customer_id': customer_ids[0],
        'order_number': 'ARW-2024-001',
        'order_date': datetime.now() - timedelta(days=7),
        'expected_delivery_date': datetime.now() + timedelta(days=14),
        'status': 'confirmed',
        'total_amount_nok': 2910.00,
        'vat_amount_nok': 727.50,
        'payment_status': 'pending',
        'payment_terms_days': 30,
        'discount_percentage': 5.0,
        'notes': 'Rush order for special event',
        'shipping_address': 'Schweigaards gate 15B, 0191 Oslo',
        'created_at': datetime.now() - timedelta(days=7),
        'updated_at': datetime.now() - timedelta(days=1)
    }
    fixtures.append(order_1)
    
    # Older fulfilled order
    order_2 = {
        'id': 'order-' + str(uuid.uuid4())[:8],
        'customer_id': customer_ids[1],
        'order_number': 'ARW-2024-002',
        'order_date': datetime.now() - timedelta(days=30),
        'expected_delivery_date': datetime.now() - timedelta(days=16),
        'status': 'delivered',
        'total_amount_nok': 5880.00,
        'vat_amount_nok': 1470.00,
        'payment_status': 'paid',
        'payment_terms_days': 14,
        'discount_percentage': 2.5,
        'notes': 'Monthly wine selection',
        'shipping_address': 'Stortingsgata 24-26, 0117 Oslo',
        'created_at': datetime.now() - timedelta(days=30),
        'updated_at': datetime.now() - timedelta(days=16)
    }
    fixtures.append(order_2)
    
    return fixtures

def generate_order_item_fixtures(order_ids, wine_batch_ids):
    """Generate realistic order item test data"""
    if not order_ids or not wine_batch_ids:
        return []
    
    fixtures = []
    
    # Items for first order
    if len(order_ids) > 0 and len(wine_batch_ids) > 0:
        fixtures.append({
            'id': 'item-' + str(uuid.uuid4())[:8],
            'order_id': order_ids[0],
            'wine_batch_id': wine_batch_ids[0],
            'quantity': 6,
            'unit_price_nok': 485.50,
            'total_price_nok': 2913.00,
            'margin_percentage': 35.0,
            'notes': 'Premium selection for wine dinner'
        })
    
    # Items for second order  
    if len(order_ids) > 1 and len(wine_batch_ids) > 1:
        fixtures.extend([
            {
                'id': 'item-' + str(uuid.uuid4())[:8],
                'order_id': order_ids[1],
                'wine_batch_id': wine_batch_ids[1],
                'quantity': 12,
                'unit_price_nok': 245.00,
                'total_price_nok': 2940.00,
                'margin_percentage': 28.0,
                'notes': 'House wine selection'
            },
            {
                'id': 'item-' + str(uuid.uuid4())[:8],
                'order_id': order_ids[1],
                'wine_batch_id': wine_batch_ids[2] if len(wine_batch_ids) > 2 else wine_batch_ids[0],
                'quantity': 6,
                'unit_price_nok': 385.00,
                'total_price_nok': 2310.00,
                'margin_percentage': 32.0,
                'notes': 'Premium white wine selection'
            }
        ])
    
    return fixtures 