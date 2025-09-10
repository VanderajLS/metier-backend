from flask import Blueprint, request, jsonify, session
from src.models.user import db
from src.models.product import Product
from src.models.order import Cart, CartItem, Order, OrderItem
from datetime import datetime
import uuid
import random
import string

order_bp = Blueprint('order', __name__, url_prefix='/api/orders')

def generate_order_number():
    """Generate a unique order number"""
    timestamp = datetime.now().strftime('%Y%m%d')
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"MET-{timestamp}-{random_suffix}"

def calculate_tax(subtotal, tax_rate=0.08):
    """Calculate tax amount (8% default)"""
    return round(float(subtotal) * tax_rate, 2)

def calculate_shipping(subtotal, free_shipping_threshold=500.00):
    """Calculate shipping cost"""
    if float(subtotal) >= free_shipping_threshold:
        return 0.00
    return 25.00  # Flat rate shipping

@order_bp.route('/checkout', methods=['POST'])
def create_order():
    """Create an order from cart contents"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = [
            'customer_email', 'customer_name',
            'billing_address_line1', 'billing_city', 'billing_state', 'billing_zip',
            'shipping_address_line1', 'shipping_city', 'shipping_state', 'shipping_zip'
        ]
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Get cart
        session_id = session.get('session_id')
        if not session_id:
            return jsonify({'error': 'No active cart found'}), 400
        
        cart = Cart.query.filter_by(session_id=session_id).first()
        if not cart or not cart.items:
            return jsonify({'error': 'Cart is empty'}), 400
        
        # Validate cart items availability
        for item in cart.items:
            if not item.product.in_stock:
                return jsonify({'error': f'Product {item.product.title} is out of stock'}), 400
            if item.quantity > item.product.quantity:
                return jsonify({'error': f'Only {item.product.quantity} of {item.product.title} available'}), 400
        
        # Calculate totals
        subtotal = sum(item.quantity * item.price for item in cart.items)
        tax_amount = calculate_tax(subtotal)
        shipping_amount = calculate_shipping(subtotal)
        discount_amount = 0  # TODO: Implement discount logic
        total_amount = subtotal + tax_amount + shipping_amount - discount_amount
        
        # Create order
        order = Order(
            order_number=generate_order_number(),
            session_id=session_id,
            customer_email=data['customer_email'],
            customer_name=data['customer_name'],
            customer_phone=data.get('customer_phone'),
            
            # Billing address
            billing_address_line1=data['billing_address_line1'],
            billing_address_line2=data.get('billing_address_line2'),
            billing_city=data['billing_city'],
            billing_state=data['billing_state'],
            billing_zip=data['billing_zip'],
            billing_country=data.get('billing_country', 'US'),
            
            # Shipping address
            shipping_address_line1=data['shipping_address_line1'],
            shipping_address_line2=data.get('shipping_address_line2'),
            shipping_city=data['shipping_city'],
            shipping_state=data['shipping_state'],
            shipping_zip=data['shipping_zip'],
            shipping_country=data.get('shipping_country', 'US'),
            
            # Totals
            subtotal=subtotal,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            discount_amount=discount_amount,
            total_amount=total_amount,
            
            # Payment info
            payment_method=data.get('payment_method', 'credit_card'),
            payment_status='pending'
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items
        for cart_item in cart.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                product_sku=cart_item.product.sku,
                product_title=cart_item.product.title,
                product_brand=cart_item.product.brand,
                quantity=cart_item.quantity,
                unit_price=cart_item.price,
                total_price=cart_item.quantity * cart_item.price
            )
            db.session.add(order_item)
            
            # Update product inventory
            cart_item.product.quantity -= cart_item.quantity
            if cart_item.product.quantity <= 0:
                cart_item.product.in_stock = False
        
        # Clear cart
        CartItem.query.filter_by(cart_id=cart.id).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Order created successfully',
            'order': order.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@order_bp.route('/<order_number>', methods=['GET'])
def get_order(order_number):
    """Get order details by order number"""
    try:
        order = Order.query.filter_by(order_number=order_number).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        return jsonify({'order': order.to_dict()})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_bp.route('', methods=['GET'])
def get_orders():
    """Get orders (admin endpoint)"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status')
        
        query = Order.query
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'pagination': {
                'page': orders.page,
                'pages': orders.pages,
                'per_page': orders.per_page,
                'total': orders.total,
                'has_next': orders.has_next,
                'has_prev': orders.has_prev
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_bp.route('/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status (admin endpoint)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}), 400
        
        order = Order.query.get(order_id)
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # Update timestamps based on status
        if new_status == 'shipped' and old_status != 'shipped':
            order.shipped_at = datetime.utcnow()
        elif new_status == 'delivered' and old_status != 'delivered':
            order.delivered_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': f'Order status updated to {new_status}',
            'order': order.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@order_bp.route('/stats', methods=['GET'])
def get_order_stats():
    """Get order statistics (admin endpoint)"""
    try:
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        processing_orders = Order.query.filter_by(status='processing').count()
        shipped_orders = Order.query.filter_by(status='shipped').count()
        
        # Recent orders
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
        
        # Revenue calculation (confirmed and processing orders)
        revenue_query = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.status.in_(['confirmed', 'processing', 'shipped', 'delivered'])
        ).scalar()
        total_revenue = float(revenue_query) if revenue_query else 0
        
        return jsonify({
            'stats': {
                'total_orders': total_orders,
                'pending_orders': pending_orders,
                'processing_orders': processing_orders,
                'shipped_orders': shipped_orders,
                'total_revenue': total_revenue
            },
            'recent_orders': [{
                'id': order.id,
                'order_number': order.order_number,
                'customer_name': order.customer_name,
                'total_amount': float(order.total_amount),
                'status': order.status,
                'created_at': order.created_at.isoformat() if order.created_at else None
            } for order in recent_orders]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@order_bp.route('/<order_number>/confirm-payment', methods=['POST'])
def confirm_payment(order_number):
    """Confirm payment for an order"""
    try:
        data = request.get_json()
        payment_reference = data.get('payment_reference')
        
        order = Order.query.filter_by(order_number=order_number).first()
        if not order:
            return jsonify({'error': 'Order not found'}), 404
        
        order.payment_status = 'paid'
        order.payment_reference = payment_reference
        order.status = 'confirmed'
        order.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment confirmed successfully',
            'order': order.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

