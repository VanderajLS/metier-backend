from src.models.user import db
from datetime import datetime
import json

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    model = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    brand = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    msrp = db.Column(db.Numeric(10, 2), nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, inactive, discontinued
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    details = db.relationship('ProductDetail', backref='product', uselist=False, cascade='all, delete-orphan')
    images = db.relationship('ProductImage', backref='product', cascade='all, delete-orphan')
    inventory = db.relationship('Inventory', backref='product', uselist=False, cascade='all, delete-orphan')
    fitment = db.relationship('Fitment', backref='product', cascade='all, delete-orphan')
    aliases = db.relationship('Alias', backref='product', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'sku': self.sku,
            'model': self.model,
            'title': self.title,
            'brand': self.brand,
            'category_id': self.category_id,
            'msrp': float(self.msrp) if self.msrp else None,
            'price': float(self.price),
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProductDetail(db.Model):
    __tablename__ = 'product_details'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    short_desc = db.Column(db.Text, nullable=True)
    long_desc = db.Column(db.Text, nullable=True)
    specs_json = db.Column(db.Text, nullable=True)  # JSON string of specifications
    install_notes = db.Column(db.Text, nullable=True)
    seo_slug = db.Column(db.String(200), nullable=True)
    
    @property
    def specs(self):
        if self.specs_json:
            try:
                return json.loads(self.specs_json)
            except json.JSONDecodeError:
                return {}
        return {}
    
    @specs.setter
    def specs(self, value):
        if value:
            self.specs_json = json.dumps(value)
        else:
            self.specs_json = None

class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    alt_text = db.Column(db.String(200), nullable=True)
    sort_order = db.Column(db.Integer, default=0)
    is_primary = db.Column(db.Boolean, default=False)

class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    on_hand = db.Column(db.Integer, default=0)
    on_order = db.Column(db.Integer, default=0)
    backorderable = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    sort_order = db.Column(db.Integer, default=0)
    
    # Self-referential relationship for parent/child categories
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    products = db.relationship('Product', backref='category')

class Fitment(db.Model):
    __tablename__ = 'fitment'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    year_from = db.Column(db.Integer, nullable=False)
    year_to = db.Column(db.Integer, nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    submodel = db.Column(db.String(100), nullable=True)
    engine = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

class Alias(db.Model):
    __tablename__ = 'aliases'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    alias_type = db.Column(db.String(20), nullable=False)  # OEM, ALT, SUPERSEDED
    value = db.Column(db.String(100), nullable=False)
    
    # Composite index for faster lookups
    __table_args__ = (db.Index('idx_alias_type_value', 'alias_type', 'value'),)

