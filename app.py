import os
import uuid
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from models import db, PrintJob, Vendor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey_vendor_auth'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'uploads')
app.config['PYTHONINSPECT'] = True # Just in case

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# Background job to clean up old files
def cleanup_old_files():
    with app.app_context():
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
        old_jobs = PrintJob.query.filter(PrintJob.created_at < cutoff_time).all()
        for job in old_jobs:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], job.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.delete(job)
        db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=cleanup_old_files, trigger="interval", hours=1)
scheduler.start()

with app.app_context():
    db.create_all()
    # Create default vendor if not exists
    if not Vendor.query.filter_by(username='vendor').first():
        hashed_pw = generate_password_hash('vendor123', method='pbkdf2:sha256')
        default_vendor = Vendor(username='vendor', password=hashed_pw)
        db.session.add(default_vendor)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'document' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['document']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    copies = int(request.form.get('copies', 1))
    color = request.form.get('color', 'B&W')
    page_range = request.form.get('page_range', 'All')
    
    token = str(uuid.uuid4())[:8].upper() # 8 char token for easy entry
    
    # Save file securely
    original_filename = secure_filename(file.filename)
    extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'bin'
    secure_name = f"{token}.{extension}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)
    file.save(file_path)
    
    # Generate QR Code
    qr = qrcode.make(token)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    # Save to db
    new_job = PrintJob(
        token=token,
        filename=secure_name,
        original_filename=original_filename,
        copies=copies,
        color=color,
        page_range=page_range
    )
    db.session.add(new_job)
    db.session.commit()
    
    return jsonify({
        'token': token,
        'qr_code': qr_b64,
        'message': 'Upload successful!'
    })


@app.route('/status/<token>', methods=['GET'])
def check_status(token):
    job = PrintJob.query.filter_by(token=token.upper()).first()
    if not job:
        return jsonify({'error': 'Invalid token'}), 404
        
    return jsonify({
        'status': job.status,
        'filename': job.original_filename,
        'copies': job.copies,
        'color': job.color,
        'page_range': job.page_range
    })

# Vendor Routes

@app.route('/vendor', methods=['GET', 'POST'])
def vendor_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        vendor = Vendor.query.filter_by(username=username).first()
        
        if vendor and check_password_hash(vendor.password, password):
            session['vendor_logged_in'] = True
            return redirect(url_for('vendor_dashboard'))
        else:
            flash('Invalid credentials')
            
    return render_template('vendor_login.html')

@app.route('/vendor/logout')
def vendor_logout():
    session.pop('vendor_logged_in', None)
    return redirect(url_for('vendor_login'))

@app.route('/vendor/dashboard')
def vendor_dashboard():
    if not session.get('vendor_logged_in'):
        return redirect(url_for('vendor_login'))
        
    jobs = PrintJob.query.order_by(PrintJob.created_at.desc()).all()
    return render_template('vendor_dashboard.html', jobs=jobs)

@app.route('/vendor/update_status/<token>', methods=['POST'])
def update_status(token):
    if not session.get('vendor_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    job = PrintJob.query.filter_by(token=token.upper()).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
        
    data = request.get_json()
    new_status = data.get('status')
    if new_status in ['Pending', 'Printing', 'Completed']:
        job.status = new_status
        db.session.commit()
        return jsonify({'success': True, 'status': job.status})
        
    return jsonify({'error': 'Invalid status'}), 400

@app.route('/file/<token>')
def download_file(token):
    if not session.get('vendor_logged_in'):
        return "Unauthorized", 401
        
    job = PrintJob.query.filter_by(token=token.upper()).first()
    if not job:
        return "Not found", 404
        
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], job.filename)
    if not os.path.exists(file_path):
        return "File not found on server", 404
        
    return send_file(file_path, as_attachment=True, download_name=job.original_filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
