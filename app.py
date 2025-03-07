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
    return bool(name and len(name) <= 255 and not re.search(r'[<>{}]', name))

def sanitize_input(text):
    return bleach.clean(text, strip=True)

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
    coming_with = db.Column(db.String(10), nullable=False)  # Changed from 'accompanied'
    bringing_children = db.Column(db.Boolean, nullable=False)  # Changed from String to Boolean
    created_at = db.Column(db.DateTime, nullable=True, server_default=db.func.now())

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
@rate_limit(max_requests=5, window_seconds=60)  # 5 requests per minute
def submit():
    if request.cookies.get('submitted'):
        return jsonify({'status': 'error', 'message': 'You have already submitted'}), 400

    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid data format'}), 400

        # Validate and sanitize inputs
        name = sanitize_input(data.get('name', ''))
        email = sanitize_input(data.get('email', ''))
        attendance_status = data.get('attendance')
        coming_with = data.get('accompanied')
        bringing_children = data.get('children')

        # Input validation
        if not validate_name(name):
            return jsonify({'status': 'error', 'message': 'Invalid name'}), 400
        if not validate_email(email):
            return jsonify({'status': 'error', 'message': 'Invalid email'}), 400
        if attendance_status not in ['confirmed', 'declined', 'undecided']:
            return jsonify({'status': 'error', 'message': 'Invalid attendance status'}), 400
        if coming_with not in ['alone', 'plus_one']:
            return jsonify({'status': 'error', 'message': 'Invalid guest option'}), 400
        if bringing_children not in ['yes', 'no']:
            return jsonify({'status': 'error', 'message': 'Invalid children option'}), 400

        # Check if email already exists
        existing_guest = Guest.query.filter_by(email=email).first()
        if existing_guest:
            return jsonify({'status': 'error', 'message': 'This email has already been registered'}), 400

        new_guest = Guest(
            name=name,
            email=email,
            attendance_status=attendance_status,
            coming_with=coming_with,
            bringing_children=(bringing_children == 'yes')
        )

        db.session.add(new_guest)
        db.session.commit()

        response = make_response(jsonify({'status': 'success', 'message': 'Response recorded'}))
        # Set secure cookie
        response.set_cookie(
            'submitted', 
            'true', 
            max_age=60*60*24*365,  # 1 year
            httponly=True,         # Prevent XSS
            secure=True,           # Only send over HTTPS
            samesite='Strict'      # Prevent CSRF
        )
        return response

    except Exception as e:
        db.session.rollback()
        # Log the error here but don't send details to client
        print(f"Error: {str(e)}")  # In production, use proper logging
        return jsonify({'status': 'error', 'message': 'An error occurred'}), 500

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
