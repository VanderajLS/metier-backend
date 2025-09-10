from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
import csv
import io
import os
from src.models.product import Product, Category, Fitment, Alias, db

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

ALLOWED_EXTENSIONS = {'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@admin_bp.route('/products', methods=['GET'])
def get_admin_products():
    """Get all products for admin management"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = Product.query
        
        if search:
            query = query.filter(
                db.or_(
                    Product.title.ilike(f'%{search}%'),
                    Product.sku.ilike(f'%{search}%'),
                    Product.brand.ilike(f'%{search}%')
                )
            )
        
        products = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        return jsonify({
            'products': [{
                'id': p.id,
                'sku': p.sku,
                'title': p.title,
                'brand': p.brand,
                'category': p.category.name if p.category else None,
                'price': float(p.price),
                'msrp': float(p.msrp) if p.msrp else None,
                'quantity': p.quantity,
                'in_stock': p.in_stock,
                'created_at': p.created_at.isoformat() if p.created_at else None
            } for p in products.items],
            'pagination': {
                'page': products.page,
                'pages': products.pages,
                'per_page': products.per_page,
                'total': products.total,
                'has_next': products.has_next,
                'has_prev': products.has_prev
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products', methods=['POST'])
def create_product():
    """Create a new product"""
    try:
        data = request.get_json()
        
        # Find or create category
        category = None
        if data.get('category_name'):
            category = Category.query.filter_by(name=data['category_name']).first()
            if not category:
                category = Category(
                    name=data['category_name'],
                    slug=data['category_name'].lower().replace(' ', '-')
                )
                db.session.add(category)
                db.session.flush()
        
        product = Product(
            sku=data['sku'],
            title=data['title'],
            brand=data.get('brand', ''),
            short_desc=data.get('short_desc', ''),
            long_desc=data.get('long_desc', ''),
            price=data['price'],
            msrp=data.get('msrp'),
            quantity=data.get('quantity', 0),
            in_stock=data.get('in_stock', True),
            category_id=category.id if category else None,
            weight=data.get('weight'),
            dimensions=data.get('dimensions'),
            install_notes=data.get('install_notes', ''),
            specs=data.get('specs', {}),
            rating=data.get('rating', 4.5),
            reviews=data.get('reviews', 0)
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify({
            'message': 'Product created successfully',
            'product_id': product.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """Update an existing product"""
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        # Update fields
        for field in ['sku', 'title', 'brand', 'short_desc', 'long_desc', 
                     'price', 'msrp', 'quantity', 'in_stock', 'weight', 
                     'dimensions', 'install_notes', 'rating', 'reviews']:
            if field in data:
                setattr(product, field, data[field])
        
        if 'specs' in data:
            product.specs = data['specs']
        
        # Handle category
        if 'category_name' in data:
            category = Category.query.filter_by(name=data['category_name']).first()
            if not category:
                category = Category(
                    name=data['category_name'],
                    slug=data['category_name'].lower().replace(' ', '-')
                )
                db.session.add(category)
                db.session.flush()
            product.category_id = category.id
        
        db.session.commit()
        
        return jsonify({'message': 'Product updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete a product"""
    try:
        product = Product.query.get_or_404(product_id)
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'message': 'Product deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/upload/products', methods=['POST'])
def upload_products_csv():
    """Upload products via CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only CSV files allowed'}), 400
        
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        created_count = 0
        updated_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_input, start=2):
            try:
                # Check if product exists
                existing_product = Product.query.filter_by(sku=row['sku']).first()
                
                # Find or create category
                category = None
                if row.get('category'):
                    category = Category.query.filter_by(name=row['category']).first()
                    if not category:
                        category = Category(
                            name=row['category'],
                            slug=row['category'].lower().replace(' ', '-')
                        )
                        db.session.add(category)
                        db.session.flush()
                
                # Prepare specs
                specs = {}
                for key, value in row.items():
                    if key.startswith('spec_') and value:
                        spec_name = key.replace('spec_', '').replace('_', ' ').title()
                        specs[spec_name] = value
                
                if existing_product:
                    # Update existing product
                    existing_product.title = row.get('title', existing_product.title)
                    existing_product.brand = row.get('brand', existing_product.brand)
                    existing_product.short_desc = row.get('short_desc', existing_product.short_desc)
                    existing_product.long_desc = row.get('long_desc', existing_product.long_desc)
                    existing_product.price = float(row.get('price', existing_product.price))
                    existing_product.msrp = float(row['msrp']) if row.get('msrp') else existing_product.msrp
                    existing_product.quantity = int(row.get('quantity', existing_product.quantity))
                    existing_product.in_stock = row.get('in_stock', '').lower() in ['true', '1', 'yes']
                    existing_product.category_id = category.id if category else existing_product.category_id
                    existing_product.weight = row.get('weight', existing_product.weight)
                    existing_product.dimensions = row.get('dimensions', existing_product.dimensions)
                    existing_product.install_notes = row.get('install_notes', existing_product.install_notes)
                    existing_product.specs = specs if specs else existing_product.specs
                    existing_product.rating = float(row.get('rating', existing_product.rating))
                    existing_product.reviews = int(row.get('reviews', existing_product.reviews))
                    
                    updated_count += 1
                else:
                    # Create new product
                    product = Product(
                        sku=row['sku'],
                        title=row.get('title', ''),
                        brand=row.get('brand', ''),
                        short_desc=row.get('short_desc', ''),
                        long_desc=row.get('long_desc', ''),
                        price=float(row.get('price', 0)),
                        msrp=float(row['msrp']) if row.get('msrp') else None,
                        quantity=int(row.get('quantity', 0)),
                        in_stock=row.get('in_stock', '').lower() in ['true', '1', 'yes'],
                        category_id=category.id if category else None,
                        weight=row.get('weight'),
                        dimensions=row.get('dimensions'),
                        install_notes=row.get('install_notes', ''),
                        specs=specs,
                        rating=float(row.get('rating', 4.5)),
                        reviews=int(row.get('reviews', 0))
                    )
                    
                    db.session.add(product)
                    created_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'message': 'CSV upload completed',
            'created': created_count,
            'updated': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/upload/fitment', methods=['POST'])
def upload_fitment_csv():
    """Upload fitment data via CSV file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only CSV files allowed'}), 400
        
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        created_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_input, start=2):
            try:
                # Find product by SKU
                product = Product.query.filter_by(sku=row['product_sku']).first()
                if not product:
                    errors.append(f"Row {row_num}: Product with SKU '{row['product_sku']}' not found")
                    continue
                
                # Check if fitment already exists
                existing_fitment = Fitment.query.filter_by(
                    product_id=product.id,
                    make=row['make'],
                    model=row['model'],
                    year_from=int(row['year_from']),
                    year_to=int(row['year_to']),
                    engine=row['engine']
                ).first()
                
                if not existing_fitment:
                    fitment = Fitment(
                        product_id=product.id,
                        make=row['make'],
                        model=row['model'],
                        submodel=row.get('submodel'),
                        year_from=int(row['year_from']),
                        year_to=int(row['year_to']),
                        engine=row['engine'],
                        notes=row.get('notes', '')
                    )
                    
                    db.session.add(fitment)
                    created_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                continue
        
        db.session.commit()
        
        return jsonify({
            'message': 'Fitment CSV upload completed',
            'created': created_count,
            'errors': errors
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/stats', methods=['GET'])
def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        total_products = Product.query.count()
        in_stock_products = Product.query.filter_by(in_stock=True).count()
        out_of_stock_products = total_products - in_stock_products
        total_categories = Category.query.count()
        
        # Recent products (last 10)
        recent_products = Product.query.order_by(Product.created_at.desc()).limit(10).all()
        
        # Low stock products (quantity < 5)
        low_stock_products = Product.query.filter(Product.quantity < 5, Product.in_stock == True).all()
        
        return jsonify({
            'stats': {
                'total_products': total_products,
                'in_stock_products': in_stock_products,
                'out_of_stock_products': out_of_stock_products,
                'total_categories': total_categories,
                'low_stock_count': len(low_stock_products)
            },
            'recent_products': [{
                'id': p.id,
                'sku': p.sku,
                'title': p.title,
                'created_at': p.created_at.isoformat() if p.created_at else None
            } for p in recent_products],
            'low_stock_products': [{
                'id': p.id,
                'sku': p.sku,
                'title': p.title,
                'quantity': p.quantity
            } for p in low_stock_products]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

