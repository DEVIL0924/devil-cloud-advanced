#!/bin/bash

echo "Setting up DEVIL CLOUD Advanced..."
echo "Creating necessary directories..."

mkdir -p bots users logs data templates static/css static/js static/images

echo "Creating configuration files..."

# Create empty JSON files
echo "{}" > data/config.json
echo "{}" > data/users.json
echo "{}" > data/bots.json
echo '{"total_bots":0,"running_bots":0,"total_users":0,"total_uploads":0,"uptime":""}' > data/stats.json

echo "Creating default admin user..."
python3 -c "
import json
import hashlib
from datetime import datetime

config = json.load(open('data/config.json'))
config['admin_password'] = 'admin123'
json.dump(config, open('data/config.json', 'w'), indent=4)

users = json.load(open('data/users.json'))
users['admin'] = {
    'id': hashlib.md5('adminadmin@devilcloud.com'.encode()).hexdigest()[:10],
    'email': 'admin@devilcloud.com',
    'password': 'scrypt:32768:8:1$YOUR_HASH_HERE$1234567890abcdef',  # Will be updated on first login
    'is_admin': True,
    'created_at': datetime.now().isoformat(),
    'storage_limit': 10240,
    'bot_limit': 100,
    'active': True,
    'bots': []
}
json.dump(users, open('data/users.json', 'w'), indent=4)

print('Default admin: username=admin, password=admin123')
"

echo "Setting permissions..."
chmod -R 755 data bots users logs

echo "Setup complete!"
echo "To run the application:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Run: python app.py"
echo "3. Access at: http://localhost:10000"
