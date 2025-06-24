"""
Wine tasting event fixtures for Phase 4
Realistic Norwegian wine tasting events with proper ROI tracking
"""
import uuid
from datetime import datetime, date, time, timedelta

def generate_tasting_event_fixtures():
    """Generate realistic wine tasting event fixtures"""
    fixtures = []
    
    # Corporate tasting event at Maaemo Restaurant
    tasting_1 = {
        'id': 'tasting-' + str(uuid.uuid4())[:8],
        'event_name': 'Premium Italian Wine Selection - Maaemo Restaurant',
        'event_date': date.today() + timedelta(days=14),
        'event_time': time(19, 0),  # 7:00 PM
        'venue_type': 'customer_location',
        'venue_name': 'Maaemo Restaurant',
        'venue_address': 'Schweigaards gate 15B, 0191 Oslo',
        'venue_cost_ore': 0,  # No venue cost for customer location
        'max_attendees': 25,
        'actual_attendees': 0,  # Event not yet held
        'event_type': 'corporate',
        'event_status': 'confirmed',
        'target_customer_segment': 'Fine dining restaurants',
        'marketing_objective': 'Introduce premium Italian wines to Michelin-starred restaurant, establish long-term partnership for wine program',
        'total_event_cost_ore': 1250000,  # 12,500 NOK estimated
        'estimated_revenue_impact_ore': 5000000,  # 50,000 NOK estimated
        'actual_revenue_impact_ore': 0,  # Event not yet completed
        'notes': 'Exclusive tasting for head sommelier and kitchen team. Focus on food pairing potential.',
        'active': True,
        'created_at': datetime.now() - timedelta(days=5),
        'updated_at': datetime.now() - timedelta(days=1)
    }
    fixtures.append(tasting_1)
    
    # Completed promotional event at rented venue
    tasting_2 = {
        'id': 'tasting-' + str(uuid.uuid4())[:8],
        'event_name': 'Spanish Wine Discovery Evening',
        'event_date': date.today() - timedelta(days=21),
        'event_time': time(18, 30),  # 6:30 PM
        'venue_type': 'rented_venue',
        'venue_name': 'Hotel Continental Oslo',
        'venue_address': 'Stortingsgata 24-26, 0117 Oslo',
        'venue_cost_ore': 850000,  # 8,500 NOK venue rental
        'max_attendees': 40,
        'actual_attendees': 35,
        'event_type': 'promotional',
        'event_status': 'completed',
        'target_customer_segment': 'Wine enthusiasts and restaurant buyers',
        'marketing_objective': 'Generate awareness for new Spanish wine imports, acquire new restaurant customers',
        'total_event_cost_ore': 2100000,  # 21,000 NOK total cost
        'estimated_revenue_impact_ore': 8000000,  # 80,000 NOK estimated
        'actual_revenue_impact_ore': 6750000,  # 67,500 NOK actual (good ROI)
        'notes': 'Very successful event. Generated 3 immediate orders and 5 follow-up meetings scheduled.',
        'active': True,
        'created_at': datetime.now() - timedelta(days=35),
        'updated_at': datetime.now() - timedelta(days=20)
    }
    fixtures.append(tasting_2)
    
    # Trade event at own premises
    tasting_3 = {
        'id': 'tasting-' + str(uuid.uuid4())[:8],
        'event_name': 'French Burgundy Masterclass',
        'event_date': date.today() - timedelta(days=45),
        'event_time': time(15, 0),  # 3:00 PM
        'venue_type': 'own_premises',
        'venue_name': 'Arctan Wines Tasting Room',
        'venue_address': 'Grensen 12, 0159 Oslo',
        'venue_cost_ore': 0,  # Own premises
        'max_attendees': 15,
        'actual_attendees': 12,
        'event_type': 'trade',
        'event_status': 'completed',
        'target_customer_segment': 'Wine professionals and sommeliers',
        'marketing_objective': 'Educate trade professionals on Burgundy terroir, establish expertise in French wines',
        'total_event_cost_ore': 950000,  # 9,500 NOK (expensive wines for tasting)
        'estimated_revenue_impact_ore': 4500000,  # 45,000 NOK estimated
        'actual_revenue_impact_ore': 5200000,  # 52,000 NOK actual (exceeded expectations)
        'notes': 'Excellent feedback from attendees. Two large orders placed immediately after event.',
        'active': True,
        'created_at': datetime.now() - timedelta(days=60),
        'updated_at': datetime.now() - timedelta(days=44)
    }
    fixtures.append(tasting_3)
    
    return fixtures

def generate_tasting_attendee_fixtures(tasting_ids, customer_ids):
    """Generate realistic tasting attendee fixtures"""
    if not tasting_ids:
        return []
    
    fixtures = []
    
    # Attendees for Corporate event (tasting_1)
    if len(tasting_ids) > 0:
        # Existing customer attendee
        if customer_ids:
            fixtures.append({
                'id': 'attendee-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[0],
                'customer_id': customer_ids[0],  # Maaemo Restaurant
                'attendee_name': 'Erik Vindahl',
                'attendee_email': 'erik.vindahl@maaemo.no',
                'attendee_phone': '+47 22 17 99 69',
                'attendee_type': 'existing_customer',
                'rsvp_status': 'confirmed',
                'follow_up_required': True,
                'post_event_interest_level': None,  # Event not yet held
                'potential_order_value_ore': 2500000,  # 25,000 NOK potential
                'active': True,
                'created_at': datetime.now() - timedelta(days=3),
                'updated_at': datetime.now() - timedelta(days=1)
            })
        
        # Industry professional attendee
        fixtures.append({
            'id': 'attendee-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[0],
            'customer_id': None,
            'attendee_name': 'Astrid Løvberg',
            'attendee_email': 'astrid@vinmonopolet.no',
            'attendee_phone': '+47 98 76 54 32',
            'attendee_type': 'industry',
            'rsvp_status': 'confirmed',
            'follow_up_required': True,
            'post_event_interest_level': None,
            'potential_order_value_ore': 0,  # Industry contact, not direct buyer
            'active': True,
            'created_at': datetime.now() - timedelta(days=4),
            'updated_at': datetime.now() - timedelta(days=2)
        })
    
    # Attendees for completed promotional event (tasting_2)
    if len(tasting_ids) > 1:
        # Prospect who became interested
        fixtures.append({
            'id': 'attendee-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[1],
            'customer_id': None,
            'attendee_name': 'Magnus Haugen',
            'attendee_email': 'magnus@restaurantkontrast.no',
            'attendee_phone': '+47 91 23 45 67',
            'attendee_type': 'prospect',
            'rsvp_status': 'attended',
            'follow_up_required': True,
            'post_event_interest_level': 4,  # High interest
            'potential_order_value_ore': 1800000,  # 18,000 NOK potential
            'active': True,
            'created_at': datetime.now() - timedelta(days=25),
            'updated_at': datetime.now() - timedelta(days=20)
        })
        
        # Existing customer who attended
        if len(customer_ids) > 1:
            fixtures.append({
                'id': 'attendee-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[1],
                'customer_id': customer_ids[1],  # Theatercaféen
                'attendee_name': 'Lise Andersen',
                'attendee_email': 'lise@theatercafeen.no',
                'attendee_phone': '+47 22 82 40 50',
                'attendee_type': 'existing_customer',
                'rsvp_status': 'attended',
                'follow_up_required': False,
                'post_event_interest_level': 5,  # Very high interest
                'potential_order_value_ore': 3200000,  # 32,000 NOK potential
                'active': True,
                'created_at': datetime.now() - timedelta(days=25),
                'updated_at': datetime.now() - timedelta(days=19)
            })
    
    # Attendees for trade event (tasting_3)
    if len(tasting_ids) > 2:
        # Industry professional
        fixtures.append({
            'id': 'attendee-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[2],
            'customer_id': None,
            'attendee_name': 'Kari Bjørnstad',
            'attendee_email': 'kari@sommelier.no',
            'attendee_phone': '+47 95 87 65 43',
            'attendee_type': 'industry',
            'rsvp_status': 'attended',
            'follow_up_required': False,
            'post_event_interest_level': 5,
            'potential_order_value_ore': 0,  # Industry contact
            'active': True,
            'created_at': datetime.now() - timedelta(days=50),
            'updated_at': datetime.now() - timedelta(days=44)
        })
    
    return fixtures

def generate_tasting_wine_fixtures(tasting_ids, wine_ids):
    """Generate realistic tasting wine fixtures"""
    if not tasting_ids:
        return []
    
    fixtures = []
    
    # Wines for Corporate event (tasting_1) - Premium Italian selection
    if len(tasting_ids) > 0:
        # Wine from catalog
        if wine_ids:
            fixtures.append({
                'id': 'tasting-wine-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[0],
                'wine_id': wine_ids[0] if len(wine_ids) > 0 else None,
                'wine_name': None,  # Will use from catalog
                'wine_producer': None,
                'wine_vintage': None,
                'bottles_used': 2,
                'wine_source': 'imported_stock',
                'cost_per_bottle_ore': 45000,  # 450 NOK per bottle
                'tasting_order': 1,
                'tasting_notes': 'Excellent reception from sommelier team. Perfect balance for their menu.',
                'customer_feedback': '{"average_rating": 4.8, "comments": ["Exceptional quality", "Perfect for our wine program"]}',
                'popularity_score': 4.80,
                'follow_up_orders': 0,  # Event not yet held
                'active': True,
                'created_at': datetime.now() - timedelta(days=5),
                'updated_at': datetime.now() - timedelta(days=1)
            })
        
        # External wine brought for comparison
        fixtures.append({
            'id': 'tasting-wine-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[0],
            'wine_id': None,
            'wine_name': 'Barolo DOCG 2018',
            'wine_producer': 'Giacomo Conterno',
            'wine_vintage': 2018,
            'bottles_used': 1,
            'wine_source': 'brought_external',
            'cost_per_bottle_ore': 125000,  # 1,250 NOK per bottle (premium)
            'tasting_order': 2,
            'tasting_notes': 'Benchmark wine for comparison. Showed our quality level.',
            'customer_feedback': None,  # Event not yet held
            'popularity_score': None,
            'follow_up_orders': 0,
            'active': True,
            'created_at': datetime.now() - timedelta(days=5),
            'updated_at': datetime.now() - timedelta(days=1)
        })
    
    # Wines for completed promotional event (tasting_2) - Spanish wines
    if len(tasting_ids) > 1:
        # Popular Spanish red
        fixtures.append({
            'id': 'tasting-wine-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[1],
            'wine_id': wine_ids[1] if len(wine_ids) > 1 else None,
            'wine_name': None,
            'wine_producer': None,
            'wine_vintage': None,
            'bottles_used': 3,
            'wine_source': 'imported_stock',
            'cost_per_bottle_ore': 28000,  # 280 NOK per bottle
            'tasting_order': 1,
            'tasting_notes': 'Most popular wine of the evening. Generated immediate interest.',
            'customer_feedback': '{"average_rating": 4.5, "comments": ["Great value", "Perfect for our restaurant", "Would order immediately"]}',
            'popularity_score': 4.50,
            'follow_up_orders': 2,  # Two immediate orders
            'active': True,
            'created_at': datetime.now() - timedelta(days=25),
            'updated_at': datetime.now() - timedelta(days=19)
        })
        
        # Premium Spanish white
        fixtures.append({
            'id': 'tasting-wine-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[1],
            'wine_id': None,
            'wine_name': 'Albariño Rías Baixas DO 2022',
            'wine_producer': 'Pazo de Señoráns',
            'wine_vintage': 2022,
            'bottles_used': 2,
            'wine_source': 'purchased_for_event',
            'cost_per_bottle_ore': 32000,  # 320 NOK per bottle
            'tasting_order': 2,
            'tasting_notes': 'Excellent feedback on freshness and minerality.',
            'customer_feedback': '{"average_rating": 4.2, "comments": ["Fresh and crisp", "Great seafood pairing"]}',
            'popularity_score': 4.20,
            'follow_up_orders': 1,
            'active': True,
            'created_at': datetime.now() - timedelta(days=25),
            'updated_at': datetime.now() - timedelta(days=19)
        })
    
    # Wines for trade event (tasting_3) - French Burgundy
    if len(tasting_ids) > 2:
        # Premium Burgundy
        fixtures.append({
            'id': 'tasting-wine-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[2],
            'wine_id': None,
            'wine_name': 'Gevrey-Chambertin 2019',
            'wine_producer': 'Domaine Armand Rousseau',
            'wine_vintage': 2019,
            'bottles_used': 1,
            'wine_source': 'purchased_for_event',
            'cost_per_bottle_ore': 95000,  # 950 NOK per bottle (very premium)
            'tasting_order': 1,
            'tasting_notes': 'Exceptional quality demonstration. Established our credibility in French wines.',
            'customer_feedback': '{"average_rating": 5.0, "comments": ["Absolutely stunning", "World-class quality", "Must have for our wine list"]}',
            'popularity_score': 5.00,
            'follow_up_orders': 1,
            'active': True,
            'created_at': datetime.now() - timedelta(days=50),
            'updated_at': datetime.now() - timedelta(days=44)
        })
    
    return fixtures

def generate_tasting_cost_fixtures(tasting_ids):
    """Generate realistic tasting cost fixtures"""
    if not tasting_ids:
        return []
    
    fixtures = []
    
    # Costs for Corporate event (tasting_1)
    if len(tasting_ids) > 0:
        fixtures.extend([
            {
                'id': 'cost-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[0],
                'cost_category': 'catering',
                'cost_description': 'Artisanal cheese and charcuterie selection',
                'supplier_name': 'Delikatessen Fenaknoken',
                'amount_ore': 450000,  # 4,500 NOK
                'cost_date': date.today() - timedelta(days=2),
                'invoice_reference': 'DELI-2024-0156',
                'fiken_transaction_id': None,
                'cost_type': 'fixed',
                'active': True,
                'created_at': datetime.now() - timedelta(days=3),
                'updated_at': datetime.now() - timedelta(days=1)
            },
            {
                'id': 'cost-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[0],
                'cost_category': 'materials',
                'cost_description': 'Professional tasting glasses and materials',
                'supplier_name': 'Riedel Norge',
                'amount_ore': 280000,  # 2,800 NOK
                'cost_date': date.today() - timedelta(days=5),
                'invoice_reference': 'RIEDEL-2024-0089',
                'fiken_transaction_id': None,
                'cost_type': 'fixed',
                'active': True,
                'created_at': datetime.now() - timedelta(days=6),
                'updated_at': datetime.now() - timedelta(days=4)
            },
            {
                'id': 'cost-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[0],
                'cost_category': 'staff',
                'cost_description': 'Sommelier consultant fee',
                'supplier_name': 'Nordic Wine Academy',
                'amount_ore': 520000,  # 5,200 NOK
                'cost_date': date.today() - timedelta(days=1),
                'invoice_reference': 'NWA-2024-0234',
                'fiken_transaction_id': None,
                'cost_type': 'fixed',
                'active': True,
                'created_at': datetime.now() - timedelta(days=4),
                'updated_at': datetime.now() - timedelta(days=1)
            }
        ])
    
    # Costs for completed promotional event (tasting_2)
    if len(tasting_ids) > 1:
        fixtures.extend([
            {
                'id': 'cost-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[1],
                'cost_category': 'venue',
                'cost_description': 'Hotel Continental event room rental',
                'supplier_name': 'Hotel Continental Oslo',
                'amount_ore': 850000,  # 8,500 NOK
                'cost_date': date.today() - timedelta(days=22),
                'invoice_reference': 'CONT-2024-0445',
                'fiken_transaction_id': 12345,
                'cost_type': 'fixed',
                'active': True,
                'created_at': datetime.now() - timedelta(days=30),
                'updated_at': datetime.now() - timedelta(days=20)
            },
            {
                'id': 'cost-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[1],
                'cost_category': 'catering',
                'cost_description': 'Spanish tapas and appetizers',
                'supplier_name': 'Iberico Catering',
                'amount_ore': 720000,  # 7,200 NOK
                'cost_date': date.today() - timedelta(days=21),
                'invoice_reference': 'IBER-2024-0167',
                'fiken_transaction_id': 12346,
                'cost_type': 'variable_per_person',
                'active': True,
                'created_at': datetime.now() - timedelta(days=25),
                'updated_at': datetime.now() - timedelta(days=19)
            },
            {
                'id': 'cost-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[1],
                'cost_category': 'marketing',
                'cost_description': 'Event invitations and promotional materials',
                'supplier_name': 'Grafisk Design Studio',
                'amount_ore': 180000,  # 1,800 NOK
                'cost_date': date.today() - timedelta(days=35),
                'invoice_reference': 'GDS-2024-0089',
                'fiken_transaction_id': 12347,
                'cost_type': 'fixed',
                'active': True,
                'created_at': datetime.now() - timedelta(days=40),
                'updated_at': datetime.now() - timedelta(days=30)
            }
        ])
    
    return fixtures

def generate_tasting_outcome_fixtures(tasting_ids, customer_ids):
    """Generate realistic tasting outcome fixtures"""
    if not tasting_ids:
        return []
    
    fixtures = []
    
    # Outcomes for completed promotional event (tasting_2)
    if len(tasting_ids) > 1:
        # Immediate order outcome
        if customer_ids:
            fixtures.append({
                'id': 'outcome-' + str(uuid.uuid4())[:8],
                'tasting_id': tasting_ids[1],
                'customer_id': customer_ids[1] if len(customer_ids) > 1 else customer_ids[0],
                'outcome_type': 'immediate_order',
                'outcome_value_ore': 2450000,  # 24,500 NOK order
                'outcome_date': date.today() - timedelta(days=20),
                'notes': 'Large order placed immediately after tasting. Customer very impressed with Spanish selection.',
                'active': True,
                'created_at': datetime.now() - timedelta(days=20),
                'updated_at': datetime.now() - timedelta(days=19)
            })
        
        # Follow-up meeting outcome
        fixtures.append({
            'id': 'outcome-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[1],
            'customer_id': None,  # Prospect, not yet customer
            'outcome_type': 'follow_up_meeting',
            'outcome_value_ore': 1800000,  # 18,000 NOK estimated value
            'outcome_date': date.today() - timedelta(days=15),
            'notes': 'Meeting scheduled with Restaurant Kontrast. High potential for ongoing partnership.',
            'active': True,
            'created_at': datetime.now() - timedelta(days=18),
            'updated_at': datetime.now() - timedelta(days=15)
        })
        
        # Newsletter signup outcome
        fixtures.append({
            'id': 'outcome-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[1],
            'customer_id': None,
            'outcome_type': 'newsletter_signup',
            'outcome_value_ore': 0,  # No immediate value
            'outcome_date': date.today() - timedelta(days=21),
            'notes': 'Three new newsletter signups from attendees. Building prospect database.',
            'active': True,
            'created_at': datetime.now() - timedelta(days=21),
            'updated_at': datetime.now() - timedelta(days=20)
        })
    
    # Outcomes for trade event (tasting_3)
    if len(tasting_ids) > 2:
        # Large immediate order
        fixtures.append({
            'id': 'outcome-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[2],
            'customer_id': customer_ids[0] if customer_ids else None,
            'outcome_type': 'immediate_order',
            'outcome_value_ore': 3200000,  # 32,000 NOK order
            'outcome_date': date.today() - timedelta(days=44),
            'notes': 'Major order for Burgundy wines. Established credibility in premium French wine segment.',
            'active': True,
            'created_at': datetime.now() - timedelta(days=44),
            'updated_at': datetime.now() - timedelta(days=43)
        })
        
        # Referral outcome
        fixtures.append({
            'id': 'outcome-' + str(uuid.uuid4())[:8],
            'tasting_id': tasting_ids[2],
            'customer_id': None,
            'outcome_type': 'referral',
            'outcome_value_ore': 2000000,  # 20,000 NOK estimated value
            'outcome_date': date.today() - timedelta(days=40),
            'notes': 'Sommelier referred us to two other high-end restaurants. Meetings scheduled.',
            'active': True,
            'created_at': datetime.now() - timedelta(days=40),
            'updated_at': datetime.now() - timedelta(days=39)
        })
    
    return fixtures 