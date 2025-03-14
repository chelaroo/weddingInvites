import os
from flask import Flask, render_template, request, jsonify, make_response, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import re
import bleach
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict

# Load environment variables
load_dotenv()

app = Flask(__name__, static_url_path='/static')

# Use environment variables for sensitive data
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@{os.getenv('HOST')}/{os.getenv('DATABASE_NAME')}"
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')  # Make sure to set this
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add security headers middleware
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# Rate limiting decorator
request_history = defaultdict(list)

def rate_limit(max_requests=5, window_seconds=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            now = datetime.now()
            ip = request.remote_addr
            
            # Clean old requests
            request_history[ip] = [req_time for req_time in request_history[ip] 
                                 if req_time > now - timedelta(seconds=window_seconds)]
            
            if len(request_history[ip]) >= max_requests:
                return jsonify({'status': 'error', 'message': 'Too many requests'}), 429
            
            request_history[ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Input validation functions
def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_name(name):
    if not name:
        return False
    # Allow letters, spaces, and common name characters
    return bool(re.match(r'^[a-zA-ZăâîșțĂÂÎȘȚ\s\'-]{1,255}$', name))

def sanitize_input(text):
    if not text:
        return text
    # Remove any HTML tags and escape special characters
    cleaned = bleach.clean(str(text).strip(), tags=[], attributes={})
    return cleaned

# Database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Guest Model
class Guest(db.Model):
    __tablename__ = 'guests'  # Specify the correct table name
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    attendance_status = db.Column(db.String(20), nullable=False)  # Changed from 'attendance'
    coming_with = db.Column(db.String(255), nullable=False)  # Changed length to accommodate names
    bringing_children = db.Column(db.Boolean, nullable=False)  # Changed from String to Boolean
    created_at = db.Column(db.DateTime, nullable=True, server_default=db.func.now())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)
def submit():
    if request.cookies.get('submitted'):
        return jsonify({'status': 'error', 'message': 'Ați trimis deja un răspuns.'}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Format de date invalid.'}), 400

        # Get form data with proper error handling
        name = data.get('name')
        email = data.get('email')
        attendance = data.get('attendance')
        coming_with = data.get('accompanied')
        children = data.get('children')
        
        # Debug logging
        print("Received data:", {
            'name': name,
            'email': email,
            'attendance': attendance,
            'coming_with': coming_with,
            'children': children
        })
        
        # Basic presence validation
        if not all([name, email, attendance]):
            missing_fields = []
            if not name: missing_fields.append("nume")
            if not email: missing_fields.append("email")
            if not attendance: missing_fields.append("confirmare prezență")
            
            return jsonify({
                'status': 'error', 
                'message': f'Vă rugăm completați toate câmpurile: {", ".join(missing_fields)}'
            }), 400
        
        # For declined attendance, we don't need to validate coming_with and children
        if attendance != 'declined':
            if not all([coming_with is not None, children]):
                missing_fields = []
                if coming_with is None: missing_fields.append("însoțitor")
                if not children: missing_fields.append("copii")
                
                return jsonify({
                    'status': 'error', 
                    'message': f'Vă rugăm completați toate câmpurile: {", ".join(missing_fields)}'
                }), 400
        
        # Sanitize inputs
        name = sanitize_input(name)
        email = sanitize_input(email)
        
        # Only sanitize coming_with if it's not 'n/a'
        if coming_with != 'n/a':
            coming_with = sanitize_input(coming_with)

        # Validate name
        if not validate_name(name):
            return jsonify({
                'status': 'error', 
                'message': 'Numele poate conține doar litere, spații și caracterele \'-\''
            }), 400
            
        # Validate email
        if not validate_email(email):
            return jsonify({
                'status': 'error', 
                'message': 'Formatul adresei de email este invalid.'
            }), 400
            
        # Validate attendance
        if attendance not in ['confirmed', 'declined', 'undecided']:
            return jsonify({
                'status': 'error', 
                'message': 'Opțiune de prezență invalidă.'
            }), 400
            
        # Only validate coming_with and children if attendance is not declined
        if attendance != 'declined':
            # Validate coming_with
            if coming_with != 'alone' and not validate_name(coming_with):
                return jsonify({
                    'status': 'error', 
                    'message': 'Numele însoțitorului poate conține doar litere, spații și caracterele \'-\''
                }), 400
                
            # Validate children option
            if children not in ['yes', 'no']:
                return jsonify({
                    'status': 'error', 
                    'message': 'Opțiune invalidă pentru copii.'
                }), 400

        # Convert children to boolean
        bringing_children = (children == 'yes') if children != 'n/a' else False

        # Check for existing email
        existing_guest = Guest.query.filter_by(email=email).first()
        if existing_guest:
            return jsonify({
                'status': 'error', 
                'message': 'Acest email a fost deja înregistrat.'
            }), 400

        # Create new guest
        try:
            new_guest = Guest(
                name=name,
                email=email,
                attendance_status=attendance,
                coming_with=coming_with,
                bringing_children=bringing_children
            )
            
            db.session.add(new_guest)
            db.session.commit()
            print("Successfully added guest to database")
            
        except Exception as db_error:
            db.session.rollback()
            print(f"Database error: {str(db_error)}")
            return jsonify({
                'status': 'error', 
                'message': f'Eroare la salvarea datelor: {str(db_error)}'
            }), 500

        response = make_response(jsonify({
            'status': 'success', 
            'message': 'Răspunsul dvs. a fost înregistrat. Vă mulțumim!'
        }))
        response.set_cookie(
            'submitted', 
            'true', 
            max_age=60*60*24*365,
            httponly=True,
            secure=True,
            samesite='Strict'
        )
        return response

    except Exception as e:
        db.session.rollback()
        print(f"Error in submit: {str(e)}")
        return jsonify({
            'status': 'error', 
            'message': f'A apărut o eroare: {str(e)}'
        }), 500

@app.route('/check-submission', methods=['GET'])
def check_submission():
    submitted_cookie = request.cookies.get('submitted')
    print(f"Cookie value: {submitted_cookie}")  # Debug print
    
    if submitted_cookie:
        return jsonify({'hasSubmitted': True}), 200
    return jsonify({'hasSubmitted': False}), 200

@app.route('/robots.txt')
def robots():
    return send_from_directory(app.static_folder, 'robots.txt')

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=80)
