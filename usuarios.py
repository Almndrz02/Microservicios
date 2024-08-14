from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import re
from datetime import timedelta

app = Flask(__name__)

# Configurar la base de datos MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://ser00:automa@localhost/micro_ser'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configurar JWT
app.config['JWT_SECRET_KEY'] = 'seguro'  
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_TOKEN_LOCATION'] = ['headers']  

db = SQLAlchemy(app)
jwt = JWTManager(app)

# Definir el modelo de usuario
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __init__(self, email, username, password):
        self.email = email
        self.username = username
        self.password = generate_password_hash(password)

def validate_password(password):
    """
    Valida que la contraseña cumpla con los requisitos:
    """
    if (8 <= len(password) <= 15 and
            re.search("[A-Z]", password) and
            re.search("[a-z]", password) and
            re.search("[!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~]", password)):
        return True
    return False

@app.route('/verify_user', methods=['GET'])
@jwt_required()
def verify_user():
    """
    Verifica si el usuario existe mediante su correo electrónico.
    """
    current_user_id = get_jwt_identity()  # Obtiene el ID del usuario desde el token JWT
    email = request.args.get('email')  # Obtiene el correo electrónico de los parámetros de la solicitud

    if not email:
        return jsonify({"error": "Se requiere el correo electrónico"}), 400

    user = Usuario.query.filter_by(email=email).first()

    if not user or user.id != current_user_id:
        return jsonify({"error": "Usuario no encontrado o no autorizado"}), 404

    return jsonify({"message": "Usuario verificado", "user_id": user.id}), 200


@app.route('/register', methods=['POST'])
def register():
    """
    Registro de nuevos usuarios:
    - Valida el email, username, y password.
    - Guarda al usuario en la base de datos.
    """
    data = request.json
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not email or not username or not password:
        return jsonify({"error": "Email, username y password son requeridos."}), 400

    if not validate_password(password):
        return jsonify({"error": "La contraseña no cumple con los requisitos de seguridad."}), 400

    if Usuario.query.filter_by(email=email).first() or Usuario.query.filter_by(username=username).first():
        return jsonify({"error": "El usuario ya existe."}), 400

    nuevo_usuario = Usuario(email=email, username=username, password=password)
    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({"message": "Usuario registrado exitosamente."}), 201

@app.route('/login', methods=['POST'])
def login():
    """
    Microservicio de Login:
    - Permite el ingreso mediante correo electrónico o nombre de usuario.
    """
    data = request.json
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')

    if not password or (not email and not username):
        return jsonify({"error": "Se requiere email o username y password."}), 400

    # Busca al usuario por email o username
    user = Usuario.query.filter_by(email=email).first() or \
           Usuario.query.filter_by(username=username).first()

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Verifica si la contraseña es correcta
    if not check_password_hash(user.password, password):
        return jsonify({"error": "Credenciales incorrectas"}), 401

    # Genera el token JWT
    access_token = create_access_token(identity=user.id)
    return jsonify({"message": "¡Login exitoso!", "token": access_token}), 200

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    """
    Ruta protegida que requiere autenticación JWT.
    """
    current_user_id = get_jwt_identity()
    return jsonify({"message": f"Acceso permitido para el usuario con ID: {current_user_id}"}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8001, debug=True)
