from datetime import datetime
from src.models.user import db
from src.models.product import Product

class Cart(db.Model):
    __tablename__ = 'carts'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('CartItem', backref='cart', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [item.to_dict() for item in self.items],
            'total_items': sum(item.quantity for item in self.items),
            'total_amount': sum(item.quantity * item.price for item in self.items)
        }

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('carts.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Price at time of adding to cart
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='cart_items', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'cart_id': self.cart_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'price': float(self.price),
            'subtotal': float(self.price * self.quantity),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'product': {
                'id': self.product.id,
                'sku': self.product.sku,
                'title': self.product.title,
                'brand': self.product.brand,
                'image': self.product.image,
                'in_stock': self.product.in_stock,
                'quantity_available': self.product.quantity
            } if self.product else None
        }

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(255), nullable=True)
    
    # Order status
    status = db.Column(db.String(50), nullable=False, default='pending')  # pending, confirmed, processing, shipped, delivered, cancelled
    
    # Customer information
    customer_email = db.Column(db.String(255), nullable=False)
    customer_name = db.Column(db.String(255), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=True)
    
    # Billing address
    billing_address_line1 = db.Column(db.String(255), nullable=False)
    billing_address_line2 = db.Column(db.String(255), nullable=True)
    billing_city = db.Column(db.String(100), nullable=False)
    billing_state = db.Column(db.String(100), nullable=False)
    billing_zip = db.Column(db.String(20), nullable=False)
    billing_country = db.Column(db.String(100), nullable=False, default='US')
    
    # Shipping address
    shipping_address_line1 = db.Column(db.String(255), nullable=False)
    shipping_address_line2 = db.Column(db.String(255), nullable=True)
    shipping_city = db.Column(db.String(100), nullable=False)
    shipping_state = db.Column(db.String(100), nullable=False)
    shipping_zip = db.Column(db.String(20), nullable=False)
    shipping_country = db.Column(db.String(100), nullable=False, default='US')
    
    # Order totals
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    shipping_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Payment information
    payment_method = db.Column(db.String(50), nullable=True)  # credit_card, paypal, etc.
    payment_status = db.Column(db.String(50), nullable=False, default='pending')  # pending, paid, failed, refunded
    payment_reference = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    shipped_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'status': self.status,
            'customer_email': self.customer_email,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'billing_address': {
                'line1': self.billing_address_line1,
                'line2': self.billing_address_line2,
                'city': self.billing_city,
                'state': self.billing_state,
                'zip': self.billing_zip,
                'country': self.billing_country
            },
            'shipping_address': {
                'line1': self.shipping_address_line1,
                'line2': self.shipping_address_line2,
                'city': self.shipping_city,
                'state': self.shipping_state,
                'zip': self.shipping_zip,
                'country': self.shipping_country
            },
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'shipping_amount': float(self.shipping_amount),
            'discount_amount': float(self.discount_amount),
            'total_amount': float(self.total_amount),
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'payment_reference': self.payment_reference,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'items': [item.to_dict() for item in self.items],
            'total_items': sum(item.quantity for item in self.items)
        }

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    # Product details at time of order (for historical accuracy)
    product_sku = db.Column(db.String(100), nullable=False)
    product_title = db.Column(db.String(255), nullable=False)
    product_brand = db.Column(db.String(100), nullable=True)
    
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='order_items', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_sku': self.product_sku,
            'product_title': self.product_title,
            'product_brand': self.product_brand,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'product': {
                'id': self.product.id,
                'sku': self.product.sku,
                'title': self.product.title,
                'brand': self.product.brand,
                'image': self.product.image
            } if self.product else None
        }

