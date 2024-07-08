from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from flask_marshmallow import Marshmallow
from datetime import date
from typing import List
from marshmallow import ValidationError, fields
from sqlalchemy import select, delete

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/ecomm' # need to add password here

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(app, model_class= Base) # Creating a instance of our database.
ma = Marshmallow(app) # Creating an instance of our Marshmallow library.

class Customer(Base):
    __tablename__ = "customer"

    id: Mapped[int] = mapped_column (primary_key= True)
    customer_name: Mapped[str] = mapped_column(db.String(75), nullable= False)
    email: Mapped[str] = mapped_column(db.String(150))
    phone: Mapped[str] = mapped_column(db.String(16))

    orders: Mapped[List["Orders"]] = db.relationship(back_populates = 'customer')
    
order_products = db.Table("order_products", Base.metadata, db.Column('order_id', db.ForeignKey('orders.id'), primary_key = True), db.Column('product_id', db.ForeignKey('products_id'), primary_key = True))

class Orders(Base):
    __tablename__ = 'orders'
    id: Mapped[int] = mapped_column(primary_key= True)
    order_date: Mapped[date] = mapped_column(db.Date, nullable = False)
    customer_id: Mapped[int] = mapped_column(db.ForeignKey('customer_id'))

    customer: Mapped['Customer'] = db.relationship(back_populates = 'orders')
    products: Mapped[List['Products']] = db.relationship(secondary = order_products)

    # Creating our products table:
class Products(Base):
    __tablename__ = 'products'
    id: Mapped[int] = mapped_column(primary_key= True)
    product_name: Mapped[str] = mapped_column(db.String(300), nullable= False)
    price: Mapped[float] = mapped_column(db.Float, nullable= False)

with app.app_context():
    db.create_all()

# Using schema to validate each of our classes:

class CustomerSchema(ma.Schema):
    id = fields.Integer(required= False)
    customer_name = fields.String(required= True)
    email = fields.String()
    phone = fields.String()

    class Meta:
        fields = ('id', 'customer_id', 'email', 'phone')

class OrderSchema(ma.Schema):
    id = fields.Integer(required= False)
    order_date = fields.Date(required= False)
    customer_id = fields.Integer(required= True)

    class Meta:
        fields = ('id', 'order_date', 'customer_id', 'items')

class ProductSchema(ma.Schema):
    id = fields.Integer(required= False)
    product_name = fields.String(required= True)
    price = fields.Float(required= True)

    class Meta:
        fields = ('id', 'product_name', 'price')

customer_schema = CustomerSchema()
customers_schema = CustomerSchema(many= True)
order_schema = OrderSchema()
orders_schema = OrderSchema(many= True)
product_schema = ProductSchema()
products_schema = ProductSchema(many= True)

@app.route('/')
def home():
    return "Welcome to our Flask Application!"

# Creating a GET method to obtain all of our customers.
@app.route("/customers", methods= ['GET'])
def get_customers():
    query = select(Customer)
    result = db.session.execute(query).scalars()
    customers = result.all()
    return customer_schema.jsonify(customers)

# Creating a GET method to obtain a single customer from our customers table.

@app.route('/customers/<int:id>', methods= ['GET'])
def get_customer(id):
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalars().first()

    if result is None:
        return jsonify({'Error': 'Customer not found'}), 404
    
    return customer_schema.jsonify(result)

# Using a POST request to create new customers.

@app.route('/customers', methods= ['POST'])
def add_customer():
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify({e.messages}), 400
    new_customer = Customer(customer_name = customer_data['customer_name'], email = customer_data['email'], phone = customer_data['phone'])
    db.session.add(new_customer) # Adding to our database instance.
    db.session.commit() # Committing our changes.

    return jsonify({"Message": "New customer successfully added."}), 201

# Using a PUT request to update a user's info.

@app.route('/customers/<int:id>', methods= ['PUT'])
def update_customer():
    query = select(Customer).where(Customer.id == id)
    result = db.session.execute(query).scalar()
    if result is None:
        return jsonify({"Error: Customer not found"}), 404
    customer = result
    try:
        customer_data = customer_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    for field, value in customer_data.items():
        setattr(customer, field, value)

    db.session.commit()
    return jsonify({"Message": "Customer details were updated successfully."})

# Creating a DELETE request to delete a customer from our customer table.

@app.route('/customers/<int:id>', methods= ['DELETE'])
def delete_customer(id):
    query = delete(Customer).where(Customer.id == id)
    result = db.session.execute(query)

    if result.rowcount == 0:
        return jsonify({"Error": "Customer not found"})
    db.session.commit()
    return jsonify ({"Message": "Customer deleted."}), 200

# Using a POST request to add new products.

@app.route('/products', methods= ['POST'])
def add_product():
    try:
        product_data = product_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_product = Products(product_data= product_data['product_name'],price= product_data['price'])

    db.session.add(new_product)
    db.session.commit()

    return jsonify({"Message": "Your new product has been added successfully."}), 201

# Using a POST request to create new orders.

@app.route('/orders', methods= ['POST'])
def add_order():
    try:
        order_data = order_schema.load(request.json)
    except ValidationError as e:
        return jsonify(e.messages), 400
    
    new_order = Orders(order_date= date.today(), customer_id= order_data['customer_id'])

    for item_id in order_data['items']:
        query = select(Products).where(Products.id == item_id)
        item = db.session.execute(query).scalar()
        new_order.products.append(item)

    db.session.add(new_order)
    db.session.commit()
    
    return jsonify({"Message": "Your new order has been placed successfully."}), 201

# Using a GET request to get items in an order using the order id.

@app.route('/order_items/<int:id>', methods= ['GET'])
def order_items(id):
    query = select(Orders).filter(Orders.id == id)
    order = db.session.execute(query).scalar()

    return products_schema.jsonify(order.products)

if __name__ == "__main__":
    app.run(debug= True)