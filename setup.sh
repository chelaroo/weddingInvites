#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up wedding website application...${NC}"

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}PostgreSQL not found. Installing...${NC}"
    sudo apt-get update
    sudo apt-get install -y postgresql postgresql-contrib
fi

# Generate random password for database user
DB_PASSWORD=$(openssl rand -base64 12)
DB_USER="customUser"
DB_NAME="weddingInvites"
APP_SECRET_KEY=$(openssl rand -base64 24)

# Create database user and database
echo -e "${GREEN}Creating database user and database...${NC}"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" || echo "User already exists"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" || echo "Database already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -c "ALTER USER $DB_USER WITH SUPERUSER;"

# Connect to the database and create the table
echo -e "${GREEN}Creating tables...${NC}"
sudo -u postgres psql -d $DB_NAME << EOF
CREATE TABLE IF NOT EXISTS guests (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    attendance_status VARCHAR(20) NOT NULL,
    coming_with VARCHAR(255) NOT NULL,
    bringing_children BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
EOF

# Create .env file
echo -e "${GREEN}Creating .env file...${NC}"
cat > .env << EOF
DATABASE_USER=$DB_USER
DATABASE_PASSWORD=$DB_PASSWORD
DATABASE_NAME=$DB_NAME
HOST=localhost
SECRET_KEY=$APP_SECRET_KEY
EOF

# Set up Python virtual environment
echo -e "${GREEN}Setting up Python virtual environment...${NC}"
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Initialize the database with Flask-Migrate
echo -e "${GREEN}Initializing Flask-Migrate...${NC}"
export FLASK_APP=app.py
flask db init || echo "Flask migrations already initialized"
flask db migrate -m "Initial migration" || echo "Migration already exists"
flask db upgrade

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${YELLOW}Database credentials have been saved to .env file${NC}"
echo -e "${YELLOW}You can now run the application with: python app.py${NC}"

# Print database connection info
echo -e "${GREEN}Database connection information:${NC}"
echo "Database User: $DB_USER"
echo "Database Password: $DB_PASSWORD"
echo "Database Name: $DB_NAME"
echo "Host: localhost"

# Uncomment to run the application
# python app.py