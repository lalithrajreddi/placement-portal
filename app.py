import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, CompanyProfile, StudentProfile, PlacementDrive, Application, ApplicationHistory
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create Admin User
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        admin = User(
            username='admin',
            email='admin@institute.edu',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_approved=True
        )
        db.session.add(admin)
        db.session.commit()

# --- Common Routes ---
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin': return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'company': return redirect(url_for('company_dashboard'))
        elif current_user.role == 'student': return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin': return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'company': return redirect(url_for('company_dashboard'))
        elif current_user.role == 'student': return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if user.is_blacklisted:
                flash('Your account is blacklisted.', 'danger')
                return redirect(url_for('login'))
            if user.role == 'company' and not user.is_approved:
                flash('Your account is pending admin approval.', 'warning')
                return redirect(url_for('login'))
                
            login_user(user)
            if user.role == 'admin': return redirect(url_for('admin_dashboard'))
            elif user.role == 'company': return redirect(url_for('company_dashboard'))
            elif user.role == 'student': return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form.get('role')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or Email already exists.', 'danger')
            return redirect(url_for('register'))
            
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            is_approved=True if role == 'student' else False # Company needs approval
        )
        db.session.add(new_user)
        db.session.commit()
        
        if role == 'company':
            company_name = request.form.get('company_name')
            hr_contact = request.form.get('hr_contact')
            website = request.form.get('website')
            company_profile = CompanyProfile(user_id=new_user.id, company_name=company_name, hr_contact=hr_contact, website=website)
            db.session.add(company_profile)
        elif role == 'student':
            full_name = request.form.get('full_name')
            degree = request.form.get('degree')
            student_profile = StudentProfile(user_id=new_user.id, full_name=full_name, degree=degree)
            db.session.add(student_profile)
            
        db.session.commit()
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Admin Routes ---
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': abort(403)
    num_students = StudentProfile.query.count()
    num_companies = CompanyProfile.query.count()
    num_drives = PlacementDrive.query.count()
    num_applications = Application.query.count()
    return render_template('admin/dashboard.html', 
        num_students=num_students, num_companies=num_companies, 
        num_drives=num_drives, num_applications=num_applications)

@app.route('/admin/companies')
@login_required
def admin_companies():
    if current_user.role != 'admin': abort(403)
    search_query = request.args.get('search', '')
    if search_query:
        companies = User.query.join(CompanyProfile).filter(
            User.role == 'company', 
            CompanyProfile.company_name.ilike(f'%{search_query}%')
        ).all()
    else:
        companies = User.query.filter_by(role='company').all()
    return render_template('admin/companies.html', companies=companies, search_query=search_query)

@app.route('/admin/company/<int:id>/action/<action>', methods=['POST'])
@login_required
def admin_company_action(id, action):
    if current_user.role != 'admin': abort(403)
    user = User.query.get_or_404(id)
    if action == 'approve': user.is_approved = True
    elif action == 'reject': db.session.delete(user.company_profile); db.session.delete(user)
    elif action == 'blacklist': user.is_blacklisted = not user.is_blacklisted
    db.session.commit()
    return redirect(url_for('admin_companies'))

@app.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin': abort(403)
    search_query = request.args.get('search', '')
    if search_query:
        students = User.query.join(StudentProfile).filter(
            User.role == 'student',
            (StudentProfile.full_name.ilike(f'%{search_query}%')) | 
            (StudentProfile.id.like(f'%{search_query}%'))
        ).all()
    else:
        students = User.query.filter_by(role='student').all()
    return render_template('admin/students.html', students=students, search_query=search_query)

@app.route('/admin/student/<int:id>/action/<action>', methods=['POST'])
@login_required
def admin_student_action(id, action):
    if current_user.role != 'admin': abort(403)
    user = User.query.get_or_404(id)
    if action == 'blacklist': user.is_blacklisted = not user.is_blacklisted
    db.session.commit()
    return redirect(url_for('admin_students'))

@app.route('/admin/drives')
@login_required
def admin_drives():
    if current_user.role != 'admin': abort(403)
    drives = PlacementDrive.query.all()
    return render_template('admin/drives.html', drives=drives)

@app.route('/admin/drive/<int:id>/action/<action>', methods=['POST'])
@login_required
def admin_drive_action(id, action):
    if current_user.role != 'admin': abort(403)
    drive = PlacementDrive.query.get_or_404(id)
    if action == 'approve': drive.status = 'Approved'
    elif action == 'reject': drive.status = 'Rejected'
    db.session.commit()
    return redirect(url_for('admin_drives'))

@app.route('/admin/history')
@login_required
def admin_history():
    if current_user.role != 'admin': abort(403)
    applications = Application.query.all()
    return render_template('admin/history.html', applications=applications)


# --- Company Routes ---
@app.route('/company')
@login_required
def company_dashboard():
    if current_user.role != 'company': abort(403)
    drives = current_user.company_profile.drives
    total_drives = len(drives)
    active_drives = len([d for d in drives if d.status == 'Approved'])
    total_apps = sum(len(d.applications) for d in drives)
    shortlisted_apps = sum(len([a for a in d.applications if a.status in ['Shortlisted', 'Selected']]) for d in drives)
    return render_template('company/dashboard.html', drives=drives, total_drives=total_drives, active_drives=active_drives, total_apps=total_apps, shortlisted_apps=shortlisted_apps)

@app.route('/company/drive/create', methods=['GET', 'POST'])
@login_required
def company_create_drive():
    if current_user.role != 'company': abort(403)
    if request.method == 'POST':
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        eligibility_criteria = request.form.get('eligibility_criteria')
        deadline_str = request.form.get('application_deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        
        drive = PlacementDrive(
            company_id=current_user.company_profile.id,
            job_title=job_title,
            job_description=job_description,
            eligibility_criteria=eligibility_criteria,
            application_deadline=deadline
        )
        db.session.add(drive)
        db.session.commit()
        flash('Drive created successfully and is pending admin approval.', 'success')
        return redirect(url_for('company_dashboard'))
    return render_template('company/create_drive.html')

@app.route('/company/drive/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def company_edit_drive(id):
    if current_user.role != 'company': abort(403)
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company_profile.id: abort(403)
    
    if request.method == 'POST':
        drive.job_title = request.form.get('job_title')
        drive.job_description = request.form.get('job_description')
        drive.eligibility_criteria = request.form.get('eligibility_criteria')
        deadline_str = request.form.get('application_deadline')
        drive.application_deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        # status reset pending maybe? No, let's keep it as is.
        db.session.commit()
        return redirect(url_for('company_dashboard'))

    return render_template('company/edit_drive.html', drive=drive)
    
@app.route('/company/drive/<int:id>/delete', methods=['POST'])
@login_required
def company_delete_drive(id):
    if current_user.role != 'company': abort(403)
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company_profile.id: abort(403)
    # Delete associated applications
    Application.query.filter_by(drive_id=drive.id).delete()
    db.session.delete(drive)
    db.session.commit()
    return redirect(url_for('company_dashboard'))
    
@app.route('/company/drive/<int:id>/close', methods=['POST'])
@login_required
def company_close_drive(id):
    if current_user.role != 'company': abort(403)
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company_profile.id: abort(403)
    drive.status = 'Closed'
    db.session.commit()
    return redirect(url_for('company_dashboard'))


@app.route('/company/drive/<int:id>/applications')
@login_required
def company_drive_applications(id):
    if current_user.role != 'company': abort(403)
    drive = PlacementDrive.query.get_or_404(id)
    if drive.company_id != current_user.company_profile.id: abort(403)
    return render_template('company/applications.html', drive=drive)

@app.route('/company/application/<int:id>/status', methods=['POST'])
@login_required
def company_update_application(id):
    if current_user.role != 'company': abort(403)
    app = Application.query.get_or_404(id)
    if app.drive.company_id != current_user.company_profile.id: abort(403)
    
    new_status = request.form.get('status')
    if new_status in ['Shortlisted', 'Selected', 'Rejected']:
        app.status = new_status
        history = ApplicationHistory(application_id=app.id, status=new_status, changed_by='company')
        db.session.add(history)
        db.session.commit()
    return redirect(url_for('company_drive_applications', id=app.drive_id))


# --- Student Routes ---
@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role != 'student': abort(403)
    search_query = request.args.get('search', '')
    query = PlacementDrive.query.filter_by(status='Approved')
    
    if search_query:
        query = query.join(CompanyProfile).filter(
            (PlacementDrive.job_title.ilike(f'%{search_query}%')) |
            (CompanyProfile.company_name.ilike(f'%{search_query}%'))
        )
    drives = query.all()
    applied_drives = [a.drive_id for a in current_user.student_profile.applications]
    
    total_available_drives = PlacementDrive.query.filter_by(status='Approved').count()
    total_applied = len(applied_drives)
    shortlisted = len([a for a in current_user.student_profile.applications if a.status in ['Shortlisted', 'Selected']])
    
    return render_template('student/dashboard.html', drives=drives, applied_drives=applied_drives, search_query=search_query, total_available_drives=total_available_drives, total_applied=total_applied, shortlisted=shortlisted)

@app.route('/student/drive/<int:id>/apply', methods=['POST'])
@login_required
def student_apply(id):
    if current_user.role != 'student': abort(403)
    drive = PlacementDrive.query.get_or_404(id)
    if drive.status != 'Approved':
        flash('Cannot apply to this drive.', 'danger')
        return redirect(url_for('student_dashboard'))
        
    existing_app = Application.query.filter_by(student_id=current_user.student_profile.id, drive_id=drive.id).first()
    if existing_app:
        flash('You have already applied.', 'warning')
        return redirect(url_for('student_dashboard'))
        
    application = Application(student_id=current_user.student_profile.id, drive_id=drive.id)
    db.session.add(application)
    db.session.flush() # flush to get application.id
    history = ApplicationHistory(application_id=application.id, status='Applied', changed_by='student')
    db.session.add(history)
    db.session.commit()
    flash('Applied successfully!', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/student/history')
@login_required
def student_history():
    if current_user.role != 'student': abort(403)
    applications = current_user.student_profile.applications
    return render_template('student/history.html', applications=applications)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student': abort(403)
    if request.method == 'POST':
        current_user.student_profile.full_name = request.form.get('full_name')
        current_user.student_profile.degree = request.form.get('degree')
        
        if 'resume' in request.files:
            file = request.files['resume']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{current_user.username}_resume_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                current_user.student_profile.resume_url = filename
            elif file.filename != '':
                flash('Invalid file type for resume. Allowed: pdf, doc, docx.', 'danger')
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    return render_template('student/profile.html')

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- API Endpoints ---
@app.route('/api/stats')
@login_required
def api_stats():
    if current_user.role == 'admin':
        return jsonify({
            'students': StudentProfile.query.count(),
            'companies': CompanyProfile.query.count(),
            'drives': PlacementDrive.query.count(),
            'applications': Application.query.count()
        })
    elif current_user.role == 'company':
        drives = current_user.company_profile.drives
        drive_ids = [d.id for d in drives]
        applications = Application.query.filter(Application.drive_id.in_(drive_ids)).count() if drive_ids else 0
        return jsonify({
            'drives': len(drives),
            'applications': applications
        })
    return jsonify({'error': 'Unauthorized'}), 403

@app.route('/api/drives')
def api_drives():
    drives = PlacementDrive.query.filter_by(status='Approved').all()
    data = []
    for d in drives:
        data.append({
            'id': d.id,
            'company': d.company.company_name,
            'title': d.job_title,
            'deadline': d.application_deadline.isoformat()
        })
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=8000)
