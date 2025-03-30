from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask_marshmallow import Marshmallow
from datetime import date
from typing import List
from marshmallow import ValidationError, fields
from sqlalchemy import select
from sqlalchemy.types import Date

app = Flask(__name__)

# Enter your MySQL password
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:<YOUR PASSWORD>@localhost/ecommerce_api'

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class=Base)
ma = Marshmallow(app)

## Models ##

class Customers(Base):
    __tablename__ = 'Customers'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(225), nullable=False)
    email: Mapped[str] = mapped_column(db.String(225))
    address: Mapped[str] = mapped_column(db.String(225))
    orders: Mapped[List['Orders']] = db.relationship(back_populates='customers')

## Association Table ##

order_products = db.Table('order_products',
    Base.metadata,
    db.Column('order_id', db.ForeignKey('orders.id')),
    db.Column('product_id', db.ForeignKey('products.id'))
)

class Orders(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable=False)
    customers_id: Mapped[int] = mapped_column(db.ForeignKey('Customers.id'))
    customers: Mapped['Customers'] = db.relationship(back_populates='orders')
    products: Mapped[List['Products']] = db.relationship(secondary=order_products, back_populates='orders')

class Products(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(primary_key=True)
    product_name: Mapped[str] = mapped_column(db.String(225), nullable=False)
    price: Mapped[float] = mapped_column(db.Float, nullable=False)
    orders: Mapped[List['Orders']] = db.relationship(secondary=order_products, back_populates='products')

## Schemas ##

class CustomerSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Customers

class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Orders

class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Products 

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many=True)

order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

## API Routes ##

# Create a new customer
@app.route('/customers', methods=['POST'])
def add_customer():

    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_customer = Customers(name=customer_data['name'], email=customer_data['email'], address=customer_data['address'])
    db.session.add(new_customer)
    db.session.commit()
    
    return customer_schema.jsonify(new_customer), 201

# GET all customers
@app.route('/customers', methods=['GET'])
def get_customers():

    query = select(Customers)
    result = db.session.execute(query).scalars()
    customers = result.all()
    return customers_schema.jsonify(customers), 200

# GET an individual customer
@app.route('/customers/<int:id>', methods=['GET'])
def get_customer(id):
    customers = db.session.get(Customers, id)
    return customer_schema.jsonify(customers), 200

# Update an existing customer
@app.route('/customers/<int:id>', methods=["PUT"] )
def update_customer(id):
    customer = db.session.get(Customers, id)
    
    if not customer: 
        return jsonify({"message": "Invalid customer id"}), 400
    
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    customer.name = customer_data['name']
    customer.email = customer_data['email']
    customer.address = customer_data['address']
    
    db.session.commit()
    return customer_schema.jsonify(customer), 200

# Delete a customer
@app.route('/customers/<int:id>', methods= ['DELETE'])
def delete_customer(id):
    customer = db.session.get(Customers, id)
    
    if not customer:
        return jsonify({"message": "Invalid customer id"}), 400
    
    db.session.delete(customer)
    db.session.commit()
    return jsonify({"message": f"successfully deleted customer {id}"}), 200

# Create a new product
@app.route('/products', methods =['POST'])
def create_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_product = Products(product_name=product_data['product_name'], price=product_data['price'])
    db.session.add(new_product)
    db.session.commit()
    
    return product_schema.jsonify(new_product), 201

# GET all products
@app.route('/products', methods=['GET'])
def get_products():
    query = select(Products)
    products = db.session.execute(query).scalars().all()
    
    return products_schema.jsonify(products), 200

# GET a single product by id
@app.route('/products/<int:id>', methods=['GET'])
def get_product(id):
    product = db.session.get(Products, id)
    return product_schema.jsonify(product), 200

# Update a product by id
@app.route('/products/<int:id>', methods=["PUT"])
def update_product(id):
    product = db.session.get(Products, id)
    
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e: #if there is an error, return the error message
        return jsonify(e.messages), 400
    
    product.product_name = product_data['product_name']
    product.price = product_data['price']
    
    db.session.commit()
    return product_schema.json

# DELETE a product by id
@app.route('/products/<int:id>', methods= ['DELETE'])
def delete_product(id):
    product = db.session.get(Products, id)
    
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": f"successfully deleted product {id}"}), 200

# Create an order
@app.route('/orders', methods =['POST'])
def create_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_order = Orders(customers_id=order_data['customers_id'])
    db.session.add(new_order)
    db.session.commit()
    
    return order_schema.jsonify(new_order), 201
    
# Add a product
@app.route('/orders/<int:order_id>/add_product/<int:product_id>', methods = ['GET'])
def add_product_to_order(order_id, product_id):
    
    order = db.session.get(Orders, order_id)
    product = db.session.get(Products, product_id)
    
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    
    if product in order.products:
        return jsonify({"message": "Product already in order"}), 400
    
    order.products.append(product) 
    db.session.commit()
    
    return jsonify({"message": f"Product {product_id} added to order {order_id}"}), 200

# Remove a product from an order 
@app.route('/orders/<int:order_id>/remove_product/<int:product_id>', methods = ['DELETE'])
def remove_product_from_order(order_id, product_id):
    
    order = db.session.get(Orders, order_id)
    product = db.session.get(Products, product_id)
    
    if not order:
        return jsonify({"message": "Invalid order id"}), 400 
    if not product:
        return jsonify({"message": "Invalid product id"}), 400
    
    if product not in order.products:
        return jsonify({"message": "Product not in order"}), 400
    
    order.products.remove(product)
    db.session.commit()
    
    return jsonify({"message": f"Product {product_id} removed from order {order_id}"})

# GET all orders for a customer by id
@app.route('/customers/<int:customers_id>/orders', methods=['GET'])
def get_customer_orders(customers_id):
    customer = db.session.get(customer, customers_id)
    
    if not customer:
        return jsonify({"message": "Invalid customer id"}), 400
    
    orders = customer.orders
    return orders_schema.jsonify(orders), 200

# GET all products for an order by id
@app.route('/orders/<int:order_id>/products', methods=['GET'])
def get_order_products(order_id):
    order = db.session.get(Orders, order_id)
    
    if not order:
        return jsonify({"message": "Invalid order id"}), 400
    
    products = order.products
    return products_schema.jsonify(products), 200

## Database Creation ##
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)