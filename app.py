from flask import Flask, render_template, request, redirect, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, json, subprocess, zipfile, psutil, re, time, shutil, threading, logging
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)
app.secret_key = "devil-cloud-advanced-secret-key-2024"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = 'bots'

db = SQLAlchemy(app)

# -------------------------------
# DATABASE MODELS
# -------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    storage_limit = db.Column(db.Integer, default=500)  # MB
    bot_limit = db.Column(db.Integer, default=10)
    active = db.Column(db.Boolean, default=True)

class Bot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    language = db.Column(db.String(20), nullable=False)  # python, php, node, bash
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='stopped')  # running, stopped, error
    pid = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_started = db.Column(db.DateTime, nullable=True)
    cpu_usage = db.Column(db.Float, default=0.0)
    memory_usage = db.Column(db.Float, default=0.0)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bot_id = db.Column(db.Integer, db.ForeignKey('bot.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    level = db.Column(db.String(20), default='info')  # info, warning, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------------------
# INITIALIZATION
# -------------------------------
def init_db():
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@devilcloud.com',
                password=generate_password_hash('admin123'),
                is_admin=True,
                storage_limit=10240,  # 10GB
                bot_limit=100
            )
            db.session.add(admin)
            db.session.commit()

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def allowed_file(filename):
    ALL
