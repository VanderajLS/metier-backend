from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_
from src.models.product import db, Product, ProductDetail, ProductImage, Inventory, Category, Fitment, Alias

product_bp = Blueprint('product', __name__)

@product_bp.route('/products', methods=['GET'])
def get_products():
    """Get products with optional search and filtering"""
    try:
        # Get query parameters
        search = request.args.get('search', '').strip()
        category = request.args.get('category', '').strip()
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        
        # Base query
        query = Product.query.filter(Product.status == 'active')
        
        # Search functionality
        if search:
            search_term = f"%{search}%"
            # Search in product fields and aliases
            alias_subquery = db.session.query(Alias.product_id).filter(
                Alias.value.ilike(search_term)
            ).subquery()
            
            query = query.filter(
                or_(
                    Product.title.ilike(search_term),
                    Product.sku.ilike(search_term),
                    Product.model.ilike(search_term),
                    Product.brand.ilike(search_term),
                    Product.id.in_(alias_subquery)
                )
            )
        
        # Category filtering
        if category:
            category_obj = Category.query.filter(Category.slug == category).first()
            if category_obj:
                query = query.filter(Product.category_id == category_obj.id)
        
        # Execute query with pagination
        products = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # Build response with product details
        result = []
        for product in products.items:
            product_data = product.to_dict()
            
            # Add category name
            if product.category:
                product_data['category'] = product.category.name
            
            # Add primary image
            primary_image = ProductImage.query.filter(
                ProductImage.product_id == product.id,
                ProductImage.is_primary == True
            ).first()
            if primary_image:
                product_data['image'] = primary_image.url
            else:
                # Fallback to first image
                first_image = ProductImage.query.filter(
                    ProductImage.product_id == product.id
                ).order_by(ProductImage.sort_order).first()
                product_data['image'] = first_image.url if first_image else '/api/placeholder/300/200'
            
            # Add inventory info
            if product.inventory:
                product_data['in_stock'] = product.inventory.on_hand > 0
                product_data['quantity'] = product.inventory.on_hand
            else:
                product_data['in_stock'] = False
                product_data['quantity'] = 0
            
            # Add basic specs for listing
            if product.details and product.details.specs:
                product_data['compatibility'] = product.details.specs.get('compatibility', '')
            
            # Add rating (mock for now)
            product_data['rating'] = 4.5
            product_data['reviews'] = 15
            
            result.append(product_data)
        
        return jsonify({
            'products': result,
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

@product_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product_detail(product_id):
    """Get detailed product information"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Build detailed product response
        product_data = product.to_dict()
        
        # Add category
        if product.category:
            product_data['category'] = product.category.name
        
        # Add product details
        if product.details:
            product_data['short_desc'] = product.details.short_desc
            product_data['long_desc'] = product.details.long_desc
            product_data['specs'] = product.details.specs
            product_data['install_notes'] = product.details.install_notes
        
        # Add images
        images = ProductImage.query.filter(
            ProductImage.product_id == product.id
        ).order_by(ProductImage.sort_order).all()
        product_data['images'] = [img.url for img in images]
        if not product_data['images']:
            product_data['images'] = ['/api/placeholder/600/400'] * 3
        
        # Add inventory
        if product.inventory:
            product_data['in_stock'] = product.inventory.on_hand > 0
            product_data['quantity'] = product.inventory.on_hand
            product_data['backorderable'] = product.inventory.backorderable
        else:
            product_data['in_stock'] = False
            product_data['quantity'] = 0
            product_data['backorderable'] = False
        
        # Add fitment information
        fitment = Fitment.query.filter(Fitment.product_id == product.id).all()
        product_data['fitment'] = []
        for fit in fitment:
            product_data['fitment'].append({
                'year_from': fit.year_from,
                'year_to': fit.year_to,
                'make': fit.make,
                'model': fit.model,
                'submodel': fit.submodel,
                'engine': fit.engine,
                'notes': fit.notes
            })
        
        # Add aliases
        aliases = Alias.query.filter(Alias.product_id == product.id).all()
        product_data['aliases'] = []
        for alias in aliases:
            product_data['aliases'].append({
                'type': alias.alias_type,
                'value': alias.value
            })
        
        # Add mock rating and reviews
        product_data['rating'] = 4.8
        product_data['reviews'] = 24
        
        return jsonify(product_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@product_bp.route('/products/<int:product_id>/related', methods=['GET'])
def get_related_products(product_id):
    """Get related products based on category and brand"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Find related products in same category or brand
        related = Product.query.filter(
            and_(
                Product.id != product_id,
                Product.status == 'active',
                or_(
                    Product.category_id == product.category_id,
                    Product.brand == product.brand
                )
            )
        ).limit(3).all()
        
        result = []
        for rel_product in related:
            product_data = {
                'id': rel_product.id,
                'title': rel_product.title,
                'price': float(rel_product.price),
                'image': '/api/placeholder/200/150'
            }
            
            # Add primary image if available
            primary_image = ProductImage.query.filter(
                ProductImage.product_id == rel_product.id,
                ProductImage.is_primary == True
            ).first()
            if primary_image:
                product_data['image'] = primary_image.url
            
            result.append(product_data)
        
        return jsonify({'related_products': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@product_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all product categories"""
    try:
        categories = Category.query.order_by(Category.sort_order, Category.name).all()
        
        result = []
        for category in categories:
            result.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'parent_id': category.parent_id
            })
        
        return jsonify({'categories': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

