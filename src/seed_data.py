#!/usr/bin/env python3
"""
Seed script to populate the database with sample product data
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.product import db, Product, ProductDetail, ProductImage, Inventory, Category, Fitment, Alias
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def seed_categories():
    """Create product categories"""
    categories = [
        {'name': 'Turbochargers', 'slug': 'turbochargers'},
        {'name': 'Turbocharger Components', 'slug': 'turbocharger-components'},
        {'name': 'Intercoolers', 'slug': 'intercoolers'},
        {'name': 'Electronics', 'slug': 'electronics'},
        {'name': 'Intake Systems', 'slug': 'intake-systems'},
        {'name': 'Exhaust Systems', 'slug': 'exhaust-systems'},
    ]
    
    for cat_data in categories:
        existing = Category.query.filter_by(slug=cat_data['slug']).first()
        if not existing:
            category = Category(**cat_data)
            db.session.add(category)
    
    db.session.commit()
    print("✓ Categories created")

def seed_products():
    """Create sample products"""
    
    # Get categories
    turbo_cat = Category.query.filter_by(slug='turbochargers').first()
    turbo_comp_cat = Category.query.filter_by(slug='turbocharger-components').first()
    intercooler_cat = Category.query.filter_by(slug='intercoolers').first()
    electronics_cat = Category.query.filter_by(slug='electronics').first()
    intake_cat = Category.query.filter_by(slug='intake-systems').first()
    
    products_data = [
        {
            'product': {
                'sku': 'MP17029',
                'title': 'Compressor Wheel (Wicked Wheel)',
                'brand': 'Métier (Excellence Engineered)',
                'price': 299.00,
                'msrp': 349.00,
                'category_id': turbo_comp_cat.id if turbo_comp_cat else None,
                'model': 'GTP38'
            },
            'details': {
                'short_desc': 'Upgraded billet compressor wheel for GTP38 turbochargers',
                'long_desc': 'This is an upgraded billet compressor wheel (wicked wheel style) designed for the Garrett GTP38 turbocharger, widely used in Ford Powerstroke 7.3L diesel engines. Wicked wheels are known for improving throttle response, reducing turbo surge, and enhancing airflow efficiency.',
                'specs': {
                    'Part Number': 'MP17029',
                    'OE Reference': '170293',
                    'Model Compatibility': 'GTP38',
                    'Quantity': '1 pc',
                    'Material': 'Billet Aluminum',
                    'Finish': 'Machined',
                    'Weight': '0.8 lbs',
                    'Warranty': '2 Years',
                    'compatibility': 'Ford Powerstroke 7.3L (1994.5–2003)'
                },
                'install_notes': 'Professional installation recommended. Requires turbocharger disassembly and balancing.'
            },
            'inventory': {
                'on_hand': 12,
                'on_order': 5,
                'backorderable': True
            },
            'fitment': [
                {
                    'year_from': 1994,
                    'year_to': 2003,
                    'make': 'Ford',
                    'model': 'F-250',
                    'submodel': 'Super Duty',
                    'engine': '7.3L Powerstroke',
                    'notes': 'GTP38 turbocharger applications'
                },
                {
                    'year_from': 1994,
                    'year_to': 2003,
                    'make': 'Ford',
                    'model': 'F-350',
                    'submodel': 'Super Duty',
                    'engine': '7.3L Powerstroke',
                    'notes': 'GTP38 turbocharger applications'
                }
            ],
            'aliases': [
                {'alias_type': 'OEM', 'value': '170293'},
                {'alias_type': 'ALT', 'value': 'GTP38-WHEEL'}
            ]
        },
        {
            'product': {
                'sku': 'MET-7811',
                'title': 'GTX 2867R Turbocharger',
                'brand': 'Metier',
                'price': 899.00,
                'msrp': 999.00,
                'category_id': turbo_cat.id if turbo_cat else None,
                'model': 'GTX-2867R'
            },
            'details': {
                'short_desc': 'High-performance turbocharger for Subaru WRX STI',
                'long_desc': 'The GTX 2867R is a precision-engineered turbocharger designed for high-performance applications. Features dual ball bearing construction and Inconel turbine wheel for maximum durability.',
                'specs': {
                    'compressor_inducer_mm': '54.0',
                    'turbine_housing': '0.64 A/R',
                    'bearing': 'Dual ball',
                    'material': 'Inconel/Aluminum',
                    'compatibility': 'Subaru WRX STI 2015-2018'
                },
                'install_notes': 'Requires up-pipe adapter for proper installation'
            },
            'inventory': {
                'on_hand': 17,
                'on_order': 20,
                'backorderable': True
            },
            'fitment': [
                {
                    'year_from': 2015,
                    'year_to': 2018,
                    'make': 'Subaru',
                    'model': 'WRX',
                    'submodel': 'STI',
                    'engine': '2.5L EJ25',
                    'notes': 'Requires up-pipe adapter'
                }
            ],
            'aliases': [
                {'alias_type': 'OEM', 'value': '14411-AA710'},
                {'alias_type': 'ALT', 'value': 'GTX2867R-64'}
            ]
        },
        {
            'product': {
                'sku': 'MET-5432',
                'title': '500HP Intercooler Kit',
                'brand': 'Metier',
                'price': 549.00,
                'msrp': 599.00,
                'category_id': intercooler_cat.id if intercooler_cat else None,
                'model': 'IC-500'
            },
            'details': {
                'short_desc': 'Front-mount intercooler kit for increased cooling capacity',
                'long_desc': 'Complete front-mount intercooler kit designed to handle up to 500HP. Includes all necessary piping, couplers, and hardware for installation.',
                'specs': {
                    'core_size': '24x12x3',
                    'inlet_outlet': '2.5 inch',
                    'material': 'Aluminum',
                    'finish': 'Polished',
                    'compatibility': 'Subaru WRX 2015-2021'
                },
                'install_notes': 'Professional installation recommended'
            },
            'inventory': {
                'on_hand': 8,
                'on_order': 15,
                'backorderable': True
            },
            'fitment': [
                {
                    'year_from': 2015,
                    'year_to': 2021,
                    'make': 'Subaru',
                    'model': 'WRX',
                    'submodel': 'Base',
                    'engine': '2.0L FA20',
                    'notes': 'Complete kit included'
                }
            ],
            'aliases': [
                {'alias_type': 'OEM', 'value': '22611-AA000'},
                {'alias_type': 'ALT', 'value': 'IC500-KIT'}
            ]
        },
        {
            'product': {
                'sku': 'MET-9876',
                'title': 'Electronic Boost Controller',
                'brand': 'Metier',
                'price': 359.00,
                'msrp': 399.00,
                'category_id': electronics_cat.id if electronics_cat else None,
                'model': 'EBC-300'
            },
            'details': {
                'short_desc': 'Precision electronic boost control system',
                'long_desc': 'Advanced electronic boost controller with dual solenoid design for precise boost control. Features multiple boost maps and safety features.',
                'specs': {
                    'max_boost': '35 PSI',
                    'solenoids': 'Dual',
                    'display': 'LCD',
                    'maps': '8',
                    'compatibility': 'Universal Application'
                },
                'install_notes': 'Requires ECU tuning for optimal performance'
            },
            'inventory': {
                'on_hand': 0,
                'on_order': 10,
                'backorderable': False
            },
            'fitment': [
                {
                    'year_from': 2015,
                    'year_to': 2021,
                    'make': 'Subaru',
                    'model': 'WRX',
                    'submodel': 'Base',
                    'engine': '2.0L FA20',
                    'notes': 'ECU tuning required'
                }
            ],
            'aliases': [
                {'alias_type': 'OEM', 'value': '45142-AA100'},
                {'alias_type': 'ALT', 'value': 'EBC300-V2'}
            ]
        },
        {
            'product': {
                'sku': 'MET-3344',
                'title': 'Cold Air Intake System',
                'brand': 'Metier',
                'price': 299.00,
                'msrp': 349.00,
                'category_id': intake_cat.id if intake_cat else None,
                'model': 'CAI-WRX'
            },
            'details': {
                'short_desc': 'High-flow cold air intake system',
                'long_desc': 'Complete cold air intake system designed to increase airflow and improve throttle response. Features high-flow air filter and mandrel-bent aluminum tubing.',
                'specs': {
                    'filter_type': 'High-flow cotton',
                    'tubing_material': 'Aluminum',
                    'tubing_diameter': '3 inch',
                    'finish': 'Polished',
                    'compatibility': 'Subaru WRX 2015-2021'
                },
                'install_notes': 'Installation time approximately 2 hours'
            },
            'inventory': {
                'on_hand': 25,
                'on_order': 0,
                'backorderable': True
            },
            'fitment': [
                {
                    'year_from': 2015,
                    'year_to': 2021,
                    'make': 'Subaru',
                    'model': 'WRX',
                    'submodel': 'Base',
                    'engine': '2.0L FA20',
                    'notes': 'Direct bolt-on installation'
                }
            ],
            'aliases': [
                {'alias_type': 'ALT', 'value': 'CAI-WRX-15'}
            ]
        }
    ]
    
    for product_data in products_data:
        # Check if product already exists
        existing = Product.query.filter_by(sku=product_data['product']['sku']).first()
        if existing:
            continue
            
        # Create product
        product = Product(**product_data['product'])
        db.session.add(product)
        db.session.flush()  # Get the product ID
        
        # Create product details
        if 'details' in product_data:
            details = ProductDetail(
                product_id=product.id,
                **product_data['details']
            )
            db.session.add(details)
        
        # Create inventory
        if 'inventory' in product_data:
            inventory = Inventory(
                product_id=product.id,
                **product_data['inventory']
            )
            db.session.add(inventory)
        
        # Create placeholder images
        for i in range(3):
            image = ProductImage(
                product_id=product.id,
                url=f'/api/placeholder/600/400',
                alt_text=f'{product.title} - View {i+1}',
                sort_order=i,
                is_primary=(i == 0)
            )
            db.session.add(image)
        
        # Create fitment records
        if 'fitment' in product_data:
            for fit_data in product_data['fitment']:
                fitment = Fitment(
                    product_id=product.id,
                    **fit_data
                )
                db.session.add(fitment)
        
        # Create aliases
        if 'aliases' in product_data:
            for alias_data in product_data['aliases']:
                alias = Alias(
                    product_id=product.id,
                    **alias_data
                )
                db.session.add(alias)
    
    db.session.commit()
    print("✓ Products created")

def main():
    app = create_app()
    
    with app.app_context():
        print("Seeding database with sample data...")
        
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Seed data
        seed_categories()
        seed_products()
        
        print("✓ Database seeding completed!")
        
        # Print summary
        product_count = Product.query.count()
        category_count = Category.query.count()
        print(f"✓ Created {category_count} categories and {product_count} products")

if __name__ == '__main__':
    main()

