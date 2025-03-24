from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------------
# Database Models
# ---------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=True)  # For display in dropdown

class Borrower(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    course = db.Column(db.String(100), nullable=False)
    year_level = db.Column(db.Integer, nullable=False)

    transactions = db.relationship('Transaction', backref='borrower', lazy=True)


class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    copy_number = db.Column(db.Integer, nullable=False)
    condition = db.Column(db.String(20), nullable=False, default="Good")

    project = db.relationship('Project', backref='inventory_items')

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey('borrower.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='Pending')

    project = db.relationship('Project')


# ---------------------
# Routes
# ---------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_pw = generate_password_hash(password, method='sha256')
        new_user = User(name=name, email=email, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/projects')
@login_required
def projects():
    return render_template('projects.html')

@app.route('/inventory')
@login_required
def inventory():
    inventories = Inventory.query.all()
    projects = Project.query.all()
    return render_template('inventory.html', inventories=inventories, projects=projects)

@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    if request.method == 'POST':
        borrower_id = request.form.get('borrower_id')
        
        if not borrower_id:
            # Only try to get name if we're adding a new borrower
            name = request.form.get('name')
            student_id = request.form.get('student_id')
            course = request.form.get('course')
            year_level = request.form.get('year_level')

            if not name or not student_id:
                flash('Please fill out borrower details.', 'danger')
                return redirect(url_for('transactions'))

            new_borrower = Borrower(name=name, student_id=student_id, course=course, year_level=year_level)
            db.session.add(new_borrower)
            db.session.commit()
            borrower_id = new_borrower.id

        # Proceed with the transaction
        project_id = request.form['project_id']
        due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
        transaction = Transaction(
            borrower_id=borrower_id,
            project_id=project_id,
            due_date=due_date,
            status='Borrowed'
        )
        db.session.add(transaction)
        db.session.commit()
        flash('Transaction created successfully!', 'success')
        return redirect(url_for('transactions'))

    transactions = Transaction.query.all()
    borrowers = Borrower.query.all()
    available_projects = Project.query.all()
    return render_template('transactions.html', transactions=transactions, borrowers=borrowers, available_projects=available_projects)

# ---------------------
# Inventory Functions
# ---------------------

@app.route('/add_inventory', methods=['POST'])
@login_required
def add_inventory():
    project_id = request.form['project_id']
    copy_number = request.form['copy_number']
    condition = request.form['condition']

    new_item = Inventory(project_id=project_id, copy_number=copy_number, condition=condition)
    db.session.add(new_item)
    db.session.commit()
    flash('New inventory item added!', 'success')
    return redirect(url_for('inventory'))

@app.route('/edit_inventory/<int:id>', methods=['POST'])
@login_required
def edit_inventory(id):
    item = Inventory.query.get_or_404(id)
    item.condition = request.form['condition']
    db.session.commit()
    flash('Inventory updated successfully!', 'success')
    return redirect(url_for('inventory'))

@app.route('/delete_inventory/<int:id>')
@login_required
def delete_inventory(id):
    item = Inventory.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Inventory deleted.', 'danger')
    return redirect(url_for('inventory'))

@app.route('/return_search', methods=['POST'])
@login_required
def return_search():
    # placeholder logic – you can modify it later!
    search_type = request.form['search_type']
    search_value = request.form['search_value']
    flash(f'Searched by {search_type} for "{search_value}" (functionality coming soon!)', 'info')
    return redirect(url_for('transactions'))

@app.route('/add_project', methods=['POST'])
@login_required
def add_project():
    title = request.form['title']
    category = request.form['category']
    new_project = Project(title=title, category=category)
    db.session.add(new_project)
    db.session.commit()
    flash('New project added successfully!', 'success')
    return redirect(url_for('projects'))

@app.route('/process_return/<int:id>', methods=['POST'])
@login_required
def process_return(id):
    # Sample logic
    transaction = Transaction.query.get_or_404(id)
    transaction.return_date = datetime.utcnow()
    transaction.status = "Returned"
    db.session.commit()
    flash('Transaction marked as returned!', 'success')
    return redirect(url_for('transactions'))




# ---------------------
# Run the app
# ---------------------

if __name__ == '__main__':
    if not os.path.exists('inventory.db'):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
