from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)

# Configuración de la base de datos (ajusta según tu configuración)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://ser00:automa@localhost/ventas_autos'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración JWT
app.config['JWT_SECRET_KEY'] = 'seguro' 
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'  
app.config['JWT_HEADER_TYPE'] = 'Bearer' 

db = SQLAlchemy(app)
jwt = JWTManager(app)

#Define el modelo Car
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    color = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    stock = db.Column(db.Integer, nullable=False)

    def __init__(self, id, name, brand, model, year, price, color, description, stock):
        self.id = id
        self.name = name
        self.brand = brand
        self.model = model
        self.year = year
        self.price = price
        self.color = color
        self.description = description
        self.stock = stock

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'model': self.model,
            'year': self.year,
            'price': self.price,
            'color': self.color,
            'description': self.description,
            'stock': self.stock
        }

# Crear la base de datos y tablas:
with app.app_context():
    db.create_all()

import requests  # Importa la biblioteca requests

#Ruta para la renta de autos
@app.route('/rent', methods=['POST'])
@jwt_required()
def rent_car():
    """
    Función para rentar un auto.
    Verifica si el usuario existe y si el auto tiene stock disponible.
    """
    current_user_id = get_jwt_identity()  # Obtiene el ID del usuario desde el token JWT
    data = request.json

    car_id = data.get('car_id')
    user_email = data.get('email')  # Se espera que se proporcione el correo electrónico del usuario

    # Verificar si el auto existe y si tiene stock disponible
    car = Car.query.get(car_id)
    if not car:
        return jsonify({"error": "El auto no existe"}), 404
    if car.stock < 1:
        return jsonify({"error": "El auto no está disponible para renta"}), 409

    # Verificar si el usuario existe consultando el microservicio de usuarios
    user_service_url = f"http://localhost:8001/verify_user?email={user_email}"
    headers = {
        'Authorization': request.headers.get("Authorization")
    }
    response = requests.get(user_service_url, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "No se pudo verificar el usuario"}), response.status_code

    # Proceder con la renta
    car.stock -= 1  # Disminuir el stock
    db.session.commit()

    return jsonify({"success": "Renta exitosa", "car": car.to_dict()}), 200

# Definir las Rutas del Microservicio
# Ruta para Crear un Nuevo Auto (POST):
@app.route('/cars', methods=['POST'])
def create_car():
    data = request.json

    # Lista de campos obligatorios
    required_params = ['id', 'name', 'brand', 'model', 'year', 'price', 'color', 'stock']

    # Verifica que todos los campos obligatorios estén presentes y no sean cadenas vacías
    missing_params = [param for param in required_params if param not in data or not data[param]]
    
    if missing_params:
        return jsonify({"error": f"Campos faltantes o vacíos: {', '.join(missing_params)}"}), 400

    # Verifica si ya existe un producto con el mismo nombre o ID
    existing_car_name = Car.query.filter_by(name=data['name']).first()
    existing_car_id = Car.query.filter_by(id=data['id']).first()
    
    if existing_car_name:
        return jsonify({"error": "El producto ya existe con ese nombre"}), 409

    if existing_car_id:
        return jsonify({"error": "El ID del producto ya existe"}), 409
    
    # Si no existe, crea un nuevo producto
    new_car = Car(
        id=data['id'],
        name=data['name'],
        brand=data['brand'],
        model=data['model'],
        year=data['year'],
        price=data['price'],
        color=data['color'],
        description=data.get('description', ''),
        stock=data['stock']
    )

    db.session.add(new_car)
    db.session.commit()
    
    return jsonify({"success": "El producto fue creado exitosamente", "car": new_car.to_dict()}), 201

#Ruta para Obtener Todos los Autos o un Auto Específico (GET):
@app.route('/cars', methods=['GET'])
def get_cars():
    cars = Car.query.all()
    return jsonify({"success": "Productos listados exitosamente", "cars": [car.to_dict() for car in cars]}), 200


@app.route('/cars/<int:id>', methods=['GET'])
def get_car(id):
    car = Car.query.get(id)
    if car is None:
        return jsonify({"error": "El producto no existe"}), 404
    return jsonify({"success": "Producto encontrado", "car": car.to_dict()}), 200

#Ruta para Actualizar un Auto Existente (PUT):
@app.route('/cars/<int:id>', methods=['PUT'])
def update_car(id):
    car = Car.query.get(id)

    if car is None:
        return jsonify({"error": "El producto no encontrado"}), 404

    data = request.json
    car.name = data.get('name', car.name)
    car.brand = data.get('brand', car.brand)
    car.model = data.get('model', car.model)
    car.year = data.get('year', car.year)
    car.price = data.get('price', car.price)
    car.color = data.get('color', car.color)
    car.description = data.get('description', car.description)
    car.stock = data.get('stock', car.stock)

    db.session.commit()

    return jsonify({"success": "Producto actualizado exitosamente", "car": car.to_dict()}), 200

#Ruta para Eliminar un Auto (DELETE):
@app.route('/cars/<int:id>', methods=['DELETE'])
def delete_car(id):
    car = Car.query.get(id)

    if car is None:
        return jsonify({"error": "El producto no esta en el catálogo"}), 404

    db.session.delete(car)
    db.session.commit()

    return jsonify({"success": "Producto eliminado exitosamente"}), 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
