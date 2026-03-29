from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class PrintJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False) # stored secure name
    original_filename = db.Column(db.String(255), nullable=False)
    copies = db.Column(db.Integer, default=1)
    color = db.Column(db.String(10), default='B&W') # 'Color' or 'B&W'
    page_range = db.Column(db.String(50), default='All')
    status = db.Column(db.String(20), default='Pending') # Pending, Printing, Completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False) # store plain or simple hash for demo
