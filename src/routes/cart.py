from flask import Blueprint, request, jsonify, session
from src.models.user import db
from src.models.product import Product
from src.models.order import Cart, CartItem
import uuid

cart_bp = Blueprint('cart', __name__, url_prefix='/api/cart')

def get_or_create_session_id():
    """Get or create a session ID for cart management"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

def get_or_create_cart(session_id, user_id=None):
    """Get or create a cart for the session/user"""
    cart = Cart.query.filter_by(session_id=session_id).first()
    if not cart:
        cart = Cart(session_id=session_id, user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart

@cart_bp.route('', methods=['GET'])
def get_cart():
    """Get the current cart contents"""
    try:
        session_id = get_or_create_session_id()
        cart = get_or_create_cart(session_id)
        
        return jsonify({
            'cart': cart.to_dict(),
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/add', methods=['POST'])
def add_to_cart():
    """Add a product to the cart"""
    try:
        data = request.get_json()
        product_id = data.get('product_id')
        quantity = data.get('quantity', 1)
        
        if not product_id:
            return jsonify({'error': 'Product ID is required'}), 400
        
        # Validate product exists and is in stock
        product = Product.query.get(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        if not product.in_stock:
            return jsonify({'error': 'Product is out of stock'}), 400
        
        if quantity > product.quantity:
            return jsonify({'error': f'Only {product.quantity} items available'}), 400
        
        session_id = get_or_create_session_id()
        cart = get_or_create_cart(session_id)
        
        # Check if item already exists in cart
        existing_item = CartItem.query.filter_by(
            cart_id=cart.id,
            product_id=product_id
        ).first()
        
        if existing_item:
            # Update quantity
            new_quantity = existing_item.quantity + quantity
            if new_quantity > product.quantity:
                return jsonify({'error': f'Only {product.quantity} items available'}), 400
            
            existing_item.quantity = new_quantity
            existing_item.updated_at = db.func.now()
        else:
            # Add new item
            cart_item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity,
                price=product.price
            )
            db.session.add(cart_item)
        
        # Update cart timestamp
        cart.updated_at = db.func.now()
        db.session.commit()
        
        return jsonify({
            'message': 'Product added to cart',
            'cart': cart.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/update', methods=['PUT'])
def update_cart_item():
    """Update quantity of a cart item"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        quantity = data.get('quantity')
        
        if not item_id or quantity is None:
            return jsonify({'error': 'Item ID and quantity are required'}), 400
        
        if quantity < 0:
            return jsonify({'error': 'Quantity must be non-negative'}), 400
        
        session_id = get_or_create_session_id()
        cart = Cart.query.filter_by(session_id=session_id).first()
        
        if not cart:
            return jsonify({'error': 'Cart not found'}), 404
        
        cart_item = CartItem.query.filter_by(
            id=item_id,
            cart_id=cart.id
        ).first()
        
        if not cart_item:
            return jsonify({'error': 'Cart item not found'}), 404
        
        # Check product availability
        if quantity > cart_item.product.quantity:
            return jsonify({'error': f'Only {cart_item.product.quantity} items available'}), 400
        
        if quantity == 0:
            # Remove item from cart
            db.session.delete(cart_item)
        else:
            # Update quantity
            cart_item.quantity = quantity
            cart_item.updated_at = db.func.now()
        
        # Update cart timestamp
        cart.updated_at = db.func.now()
        db.session.commit()
        
        return jsonify({
            'message': 'Cart updated successfully',
            'cart': cart.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/remove/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    """Remove an item from the cart"""
    try:
        session_id = get_or_create_session_id()
        cart = Cart.query.filter_by(session_id=session_id).first()
        
        if not cart:
            return jsonify({'error': 'Cart not found'}), 404
        
        cart_item = CartItem.query.filter_by(
            id=item_id,
            cart_id=cart.id
        ).first()
        
        if not cart_item:
            return jsonify({'error': 'Cart item not found'}), 404
        
        db.session.delete(cart_item)
        cart.updated_at = db.func.now()
        db.session.commit()
        
        return jsonify({
            'message': 'Item removed from cart',
            'cart': cart.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/clear', methods=['DELETE'])
def clear_cart():
    """Clear all items from the cart"""
    try:
        session_id = get_or_create_session_id()
        cart = Cart.query.filter_by(session_id=session_id).first()
        
        if not cart:
            return jsonify({'message': 'Cart is already empty'})
        
        # Delete all cart items
        CartItem.query.filter_by(cart_id=cart.id).delete()
        cart.updated_at = db.func.now()
        db.session.commit()
        
        return jsonify({
            'message': 'Cart cleared successfully',
            'cart': cart.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/count', methods=['GET'])
def get_cart_count():
    """Get the total number of items in the cart"""
    try:
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'count': 0})
        
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart:
            return jsonify({'count': 0})
        
        total_items = sum(item.quantity for item in cart.items)
        
        return jsonify({'count': total_items})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

