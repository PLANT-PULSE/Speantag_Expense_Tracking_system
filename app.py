from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from decimal import Decimal, ROUND_HALF_UP
import json
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'speantag_bakery_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bakery_expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')

db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Custom Jinja2 filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object"""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []

@app.template_filter('strftime')
def strftime_filter(value, format_string):
    """Format datetime object to string"""
    if hasattr(value, 'strftime'):
        return value.strftime(format_string)
    return str(value)

@app.template_filter('strptime')
def strptime_filter(value, format_string):
    """Parse string to datetime object"""
    try:
        from datetime import datetime
        return datetime.strptime(value, format_string)
    except (ValueError, TypeError):
        return value

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models
class DailySale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity_sold = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    
    sale_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MarketPurchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_amount_taken = db.Column(db.Float, nullable=False)
    total_amount_spent = db.Column(db.Float, nullable=False)
    remaining_balance = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PurchaseItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    market_purchase_id = db.Column(db.Integer, db.ForeignKey('market_purchase.id'), nullable=False)
    item_name = db.Column(db.String(100), nullable=False)
    quantity_purchased = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False, unique=True)
    total_quantity = db.Column(db.Float, default=0)
    cost_per_unit = db.Column(db.Float, default=0)
    remaining_quantity = db.Column(db.Float, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

class InventoryUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    quantity_used = db.Column(db.Float, nullable=False)
    cost_used = db.Column(db.Float, nullable=False)
    expected_profit = db.Column(db.Float, default=0)
    usage_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    profile_image = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6 support
    user_agent = db.Column(db.Text, nullable=True)
    session_id = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(255), nullable=True)
    risk_level = db.Column(db.String(20), default='low')  # low, medium, high, critical
    activity_metadata = db.Column(db.Text, nullable=True)  # JSON string for additional data

class FraudAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    alert_type = db.Column(db.String(100), nullable=False)  # suspicious_login, unusual_transaction, etc.
    severity = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    description = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)

class SavedActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(255), nullable=True)
    page_name = db.Column(db.String(100), nullable=False)  # daily-sales, market-purchase, etc.
    activities_data = db.Column(db.Text, nullable=False)  # JSON string of activities
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)  # Optional user notes

# Helper functions for activity logging and fraud detection
def get_client_info():
    """Get client IP address and user agent from request"""
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip_address and ',' in ip_address:
        ip_address = ip_address.split(',')[0].strip()
    user_agent = request.headers.get('User-Agent', '')
    return ip_address, user_agent

def log_user_activity(user_id, action, details=None, risk_level='low', metadata=None, session_id=None):
    """Enhanced activity logging with security information"""
    ip_address, user_agent = get_client_info()
    session_id = session.get('user_session_id', str(uuid.uuid4()))

    # Store session ID for tracking
    if 'user_session_id' not in session:
        session['user_session_id'] = session_id

    activity_metadata = json.dumps(metadata) if metadata else None

    activity = UserActivity(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        session_id=session_id,
        risk_level=risk_level,
        activity_metadata=activity_metadata
    )

    db.session.add(activity)
    db.session.commit()

    # Check for fraudulent activity
    check_fraud_detection(user_id, action, ip_address, user_agent, details)

def check_fraud_detection(user_id, action, ip_address, user_agent, details):
    """Fraud detection logic"""
    user = User.query.get(user_id)
    if not user:
        return

    # Check for suspicious login patterns
    if action == 'Login':
        # Check for multiple failed login attempts
        recent_failed_logins = UserActivity.query.filter(
            UserActivity.user_id == user_id,
            UserActivity.action == 'Failed Login',
            UserActivity.timestamp >= datetime.utcnow() - timedelta(hours=1)
        ).count()

        if recent_failed_logins >= 3:
            create_fraud_alert(
                user_id=user_id,
                alert_type='multiple_failed_logins',
                severity='high',
                description=f'Multiple failed login attempts ({recent_failed_logins}) detected for user {user.name}',
                ip_address=ip_address,
                user_agent=user_agent
            )

        # Check for unusual login time (outside business hours)
        current_hour = datetime.utcnow().hour
        if current_hour < 6 or current_hour > 22:  # Outside 6 AM - 10 PM
            create_fraud_alert(
                user_id=user_id,
                alert_type='unusual_login_time',
                severity='medium',
                description=f'Unusual login time ({current_hour}:00) for user {user.name}',
                ip_address=ip_address,
                user_agent=user_agent
            )

    # Check for unusual transaction amounts
    elif 'sale' in action.lower() or 'purchase' in action.lower():
        # Extract amount from details if possible
        amount = extract_amount_from_details(details)
        if amount and amount > 10000:  # Threshold for large transactions
            create_fraud_alert(
                user_id=user_id,
                alert_type='large_transaction',
                severity='medium',
                description=f'Large transaction amount (${amount:.2f}) by user {user.name}',
                ip_address=ip_address,
                user_agent=user_agent
            )

    # Check for rapid successive actions (potential automation)
    recent_activities = UserActivity.query.filter(
        UserActivity.user_id == user_id,
        UserActivity.timestamp >= datetime.utcnow() - timedelta(minutes=5)
    ).count()

    if recent_activities > 20:  # More than 20 actions in 5 minutes
        create_fraud_alert(
            user_id=user_id,
            alert_type='rapid_activity',
            severity='high',
            description=f'Rapid successive activities ({recent_activities}) detected for user {user.name}',
            ip_address=ip_address,
            user_agent=user_agent
        )

def create_fraud_alert(user_id, alert_type, severity, description, ip_address, user_agent):
    """Create a fraud alert"""
    alert = FraudAlert(
        user_id=user_id,
        alert_type=alert_type,
        severity=severity,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.session.add(alert)
    db.session.commit()

def extract_amount_from_details(details):
    """Extract monetary amount from activity details"""
    if not details:
        return None

    import re
    # Look for patterns like $123.45 or 123.45
    amount_match = re.search(r'\$?(\d+(?:\.\d{2})?)', details)
    if amount_match:
        try:
            return float(amount_match.group(1))
        except ValueError:
            pass
    return None

# Routes
@app.route('/')
@login_required
def index():
    return redirect(url_for('daily_sales'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        profile_image = request.files.get('profile_image')

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return redirect(url_for('signup'))

        # Check if this is the first user (admin)
        is_first_user = User.query.count() == 0

        user = User(name=name, email=email, phone=phone, is_admin=is_first_user)
        user.set_password(password)

        if profile_image and profile_image.filename:
            filename = secure_filename(profile_image.filename)
            profile_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            user.profile_image = filename

        db.session.add(user)
        db.session.commit()

        # Log activity
        log_user_activity(user.id, 'Account Created', f'User {name} signed up')

        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)

            # Create session ID for activity tracking
            session_id = str(uuid.uuid4())
            session['user_session_id'] = session_id

            # Log successful login activity
            try:
                log_user_activity(user.id, 'Login', f'User {user.name} logged in', session_id=session_id)
            except Exception as e:
                # Log the error but don't fail the login
                print(f"Error logging login activity: {e}")
            return redirect(url_for('index'))
        else:
            # Log failed login attempt
            try:
                log_user_activity(user.id if user else None, 'Failed Login', f'Failed login attempt for email: {email}', risk_level='medium')
            except Exception as e:
                # Log the error but don't fail the login process
                print(f"Error logging failed login: {e}")
            flash('Invalid email or password!', 'error')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # Log activity
    log_user_activity(current_user.id, 'Logout', f'User {current_user.name} logged out')
    logout_user()
    return redirect(url_for('login'))

@app.route('/daily-sales', methods=['GET', 'POST'])
@login_required
def daily_sales():
    if request.method == 'POST':
        item_name = request.form['item_name']
        quantity_sold = float(request.form['quantity_sold'])
        unit_price = float(request.form['unit_price'])
        sale_date = datetime.strptime(request.form['sale_date'], '%Y-%m-%d').date()
        
        total_amount = quantity_sold * unit_price
        
        new_sale = DailySale(
            item_name=item_name,
            quantity_sold=quantity_sold,
            unit_price=unit_price,
            total_amount=total_amount,
            sale_date=sale_date
        )
        
        db.session.add(new_sale)
        db.session.commit()

        # Log activity
        log_user_activity(current_user.id, 'Recorded Sale', f'Sale of {item_name} for ${total_amount:.2f}')

        flash('Sale recorded successfully!', 'success')
        return redirect(url_for('daily_sales'))
    
    # Get sales for the current month
    current_month = date.today().replace(day=1)
    sales = DailySale.query.filter(DailySale.sale_date >= current_month).order_by(DailySale.sale_date.desc()).all()
    
    return render_template('daily_sales.html', sales=sales, today=date.today().strftime('%Y-%m-%d'))

@app.route('/delete-sale/<int:sale_id>')
@login_required
def delete_sale(sale_id):
    sale = DailySale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()

    # Log activity
    log_user_activity(current_user.id, 'Deleted Sale', f'Deleted sale of {sale.item_name} for ${sale.total_amount:.2f}', risk_level='medium')

    flash('Sale deleted successfully!', 'success')
    return redirect(url_for('daily_sales'))

@app.route('/market-purchase', methods=['GET', 'POST'])
@login_required
def market_purchase():
    if request.method == 'POST':
        total_amount_taken = float(request.form['total_amount_taken'])
        purchase_date = datetime.strptime(request.form['purchase_date'], '%Y-%m-%d').date()
        
        # Create market purchase record
        market_purchase = MarketPurchase(
            total_amount_taken=total_amount_taken,
            total_amount_spent=0,
            remaining_balance=total_amount_taken,
            purchase_date=purchase_date
        )
        db.session.add(market_purchase)
        db.session.flush()  # Get the ID
        
        # Process purchase items
        item_names = request.form.getlist('item_name[]')
        quantities = request.form.getlist('quantity_purchased[]')
        unit_prices = request.form.getlist('unit_price[]')
        
        total_spent = 0
        
        for i in range(len(item_names)):
            if item_names[i].strip():
                quantity = float(quantities[i])
                unit_price = float(unit_prices[i])
                total_price = quantity * unit_price
                total_spent += total_price
                
                purchase_item = PurchaseItem(
                    market_purchase_id=market_purchase.id,
                    item_name=item_names[i],
                    quantity_purchased=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.session.add(purchase_item)
                
                # Update inventory
                inventory_item = InventoryItem.query.filter_by(item_name=item_names[i]).first()
                if inventory_item:
                    # Add to existing inventory
                    new_total = inventory_item.total_quantity + quantity
                    new_cost = ((inventory_item.total_quantity * inventory_item.cost_per_unit) + total_price) / new_total
                    inventory_item.total_quantity = new_total
                    inventory_item.remaining_quantity = new_total
                    inventory_item.cost_per_unit = new_cost
                    inventory_item.last_updated = datetime.utcnow()
                else:
                    # Create new inventory item
                    new_inventory = InventoryItem(
                        item_name=item_names[i],
                        total_quantity=quantity,
                        cost_per_unit=unit_price,
                        remaining_quantity=quantity
                    )
                    db.session.add(new_inventory)
        
        market_purchase.total_amount_spent = total_spent
        market_purchase.remaining_balance = total_amount_taken - total_spent
        
        db.session.commit()

        # Log activity
        log_user_activity(current_user.id, 'Recorded Market Purchase', f'Purchase for ${total_spent:.2f} on {purchase_date}')

        flash('Market purchase recorded successfully!', 'success')
        return redirect(url_for('market_purchase'))
    
    # Get purchases for the current month
    current_month = date.today().replace(day=1)
    purchases = MarketPurchase.query.filter(MarketPurchase.purchase_date >= current_month).order_by(MarketPurchase.purchase_date.desc()).all()
    
    return render_template('market_purchase.html', purchases=purchases)

@app.route('/inventory-usage', methods=['GET', 'POST'])
@login_required
def inventory_usage():
    if request.method == 'POST':
        inventory_item_id = int(request.form['inventory_item_id'])
        quantity_used = float(request.form['quantity_used'])
        usage_date = datetime.strptime(request.form['usage_date'], '%Y-%m-%d').date()
        
        inventory_item = InventoryItem.query.get_or_404(inventory_item_id)
        
        if quantity_used > inventory_item.remaining_quantity:
            flash('Quantity used cannot exceed remaining quantity!', 'error')
            return redirect(url_for('inventory_usage'))
        
        cost_used = quantity_used * inventory_item.cost_per_unit
        expected_profit = cost_used * 0.3  # Assuming 30% profit margin
        
        # Update remaining quantity
        inventory_item.remaining_quantity -= quantity_used
        inventory_item.last_updated = datetime.utcnow()
        
        # Record usage
        usage = InventoryUsage(
            inventory_item_id=inventory_item_id,
            quantity_used=quantity_used,
            cost_used=cost_used,
            expected_profit=expected_profit,
            usage_date=usage_date
        )
        
        db.session.add(usage)
        db.session.commit()

        # Log activity
        log_user_activity(current_user.id, 'Recorded Inventory Usage', f'Used {quantity_used} of {inventory_item.item_name} on {usage_date}')

        flash('Inventory usage recorded successfully!', 'success')
        return redirect(url_for('inventory_usage'))
    
    inventory_items = InventoryItem.query.filter(InventoryItem.remaining_quantity > 0).all()
    usage_records = InventoryUsage.query.order_by(InventoryUsage.usage_date.desc()).limit(20).all()
    
    return render_template('inventory_usage.html', inventory_items=inventory_items, usage_records=usage_records)

@app.route('/reports')
@login_required
def reports():
    # Get date range from query parameters
    start_date = request.args.get('start_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get data for the date range
    sales = DailySale.query.filter(
        DailySale.sale_date >= start_dt,
        DailySale.sale_date <= end_dt
    ).all()
    
    purchases = MarketPurchase.query.filter(
        MarketPurchase.purchase_date >= start_dt,
        MarketPurchase.purchase_date <= end_dt
    ).all()
    
    usage_records = InventoryUsage.query.filter(
        InventoryUsage.usage_date >= start_dt,
        InventoryUsage.usage_date <= end_dt
    ).all()
    
    # Calculate totals
    total_revenue = sum(sale.total_amount for sale in sales)
    total_expenses = sum(purchase.total_amount_spent for purchase in purchases)
    total_cost_used = sum(usage.cost_used for usage in usage_records)
    total_expected_profit = sum(usage.expected_profit for usage in usage_records)
    
    net_profit = total_revenue - total_expenses - total_cost_used + total_expected_profit
    
    # Get current inventory
    current_inventory = InventoryItem.query.all()
    
    return render_template('reports.html',
                         sales=sales,
                         purchases=purchases,
                         usage_records=usage_records,
                         total_revenue=total_revenue,
                         total_expenses=total_expenses,
                         total_cost_used=total_cost_used,
                         total_expected_profit=total_expected_profit,
                         net_profit=net_profit,
                         current_inventory=current_inventory,
                         start_date=start_date,
                         end_date=end_date)

@app.route('/export-excel')
@login_required
def export_excel():
    start_date = request.args.get('start_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get data
    sales = DailySale.query.filter(
        DailySale.sale_date >= start_dt,
        DailySale.sale_date <= end_dt
    ).all()
    
    purchases = MarketPurchase.query.filter(
        MarketPurchase.purchase_date >= start_dt,
        MarketPurchase.purchase_date <= end_dt
    ).all()
    
    usage_records = InventoryUsage.query.filter(
        InventoryUsage.usage_date >= start_dt,
        InventoryUsage.usage_date <= end_dt
    ).all()
    
    # Create Excel file
    with pd.ExcelWriter('bakery_report.xlsx', engine='openpyxl') as writer:
        # Sales sheet
        sales_data = []
        for sale in sales:
            sales_data.append({
                'Date': sale.sale_date,
                'Item': sale.item_name,
                'Quantity': sale.quantity_sold,
                'Unit Price': sale.unit_price,
                'Total Amount': sale.total_amount
            })
        
        if sales_data:
            df_sales = pd.DataFrame(sales_data)
            df_sales.to_excel(writer, sheet_name='Sales', index=False)
        
        # Purchases sheet
        purchases_data = []
        for purchase in purchases:
            purchases_data.append({
                'Date': purchase.purchase_date,
                'Amount Taken': purchase.total_amount_taken,
                'Amount Spent': purchase.total_amount_spent,
                'Remaining Balance': purchase.remaining_balance
            })
        
        if purchases_data:
            df_purchases = pd.DataFrame(purchases_data)
            df_purchases.to_excel(writer, sheet_name='Purchases', index=False)
        
        # Usage sheet
        usage_data = []
        for usage in usage_records:
            item = InventoryItem.query.get(usage.inventory_item_id)
            usage_data.append({
                'Date': usage.usage_date,
                'Item': item.item_name if item else 'Unknown',
                'Quantity Used': usage.quantity_used,
                'Cost Used': usage.cost_used,
                'Expected Profit': usage.expected_profit
            })
        
        if usage_data:
            df_usage = pd.DataFrame(usage_data)
            df_usage.to_excel(writer, sheet_name='Inventory Usage', index=False)
    
    return send_file('bakery_report.xlsx', as_attachment=True, download_name=f'bakery_report_{start_date}_to_{end_date}.xlsx')

@app.route('/export-pdf')
@login_required
def export_pdf():
    start_date = request.args.get('start_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Get data
    sales = DailySale.query.filter(
        DailySale.sale_date >= start_dt,
        DailySale.sale_date <= end_dt
    ).all()
    
    purchases = MarketPurchase.query.filter(
        MarketPurchase.purchase_date >= start_dt,
        MarketPurchase.purchase_date <= end_dt
    ).all()
    
    usage_records = InventoryUsage.query.filter(
        InventoryUsage.usage_date >= start_dt,
        InventoryUsage.usage_date <= end_dt
    ).all()
    
    # Calculate totals
    total_revenue = sum(sale.total_amount for sale in sales)
    total_expenses = sum(purchase.total_amount_spent for purchase in purchases)
    total_cost_used = sum(usage.cost_used for usage in usage_records)
    total_expected_profit = sum(usage.expected_profit for usage in usage_records)
    net_profit = total_revenue - total_expenses - total_cost_used + total_expected_profit
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    title = Paragraph("Speantag Bakery - Financial Report", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Summary section
    summary_data = [
        ['Period', f'{start_date} to {end_date}'],
        ['Total Revenue', f'${total_revenue:.2f}'],
        ['Total Expenses', f'${total_expenses:.2f}'],
        ['Total Cost Used', f'${total_cost_used:.2f}'],
        ['Total Expected Profit', f'${total_expected_profit:.2f}'],
        ['Net Profit', f'${net_profit:.2f}']
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))
    
    # Sales table
    if sales:
        sales_title = Paragraph("Sales Records", styles['Heading2'])
        story.append(sales_title)
        story.append(Spacer(1, 6))
        
        sales_data = [['Date', 'Item', 'Quantity', 'Unit Price', 'Total']]
        for sale in sales:
            sales_data.append([
                sale.sale_date.strftime('%Y-%m-%d'),
                sale.item_name,
                str(sale.quantity_sold),
                f'${sale.unit_price:.2f}',
                f'${sale.total_amount:.2f}'
            ])
        
        sales_table = Table(sales_data)
        sales_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(sales_table)
        story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'bakery_report_{start_date}_to_{end_date}.pdf',
        mimetype='application/pdf'
    )

@app.route('/save-activities')
@login_required
def save_activities():
    today = date.today()

    # Get user's activities for today
    activities = UserActivity.query.filter(
        UserActivity.user_id == current_user.id,
        db.func.date(UserActivity.timestamp) == today
    ).order_by(UserActivity.timestamp).all()

    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []

    styles = getSampleStyleSheet()
    title = Paragraph(f"Daily Activities Report - {current_user.name}", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))

    # Summary
    summary_data = [
        ['Date', today.strftime('%Y-%m-%d')],
        ['User', current_user.name],
        ['Total Activities', str(len(activities))]
    ]

    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # Activities table
    if activities:
        activities_title = Paragraph("Activities", styles['Heading2'])
        story.append(activities_title)
        story.append(Spacer(1, 6))

        activities_data = [['Time', 'Action', 'Details']]
        for activity in activities:
            activities_data.append([
                activity.timestamp.strftime('%H:%M:%S'),
                activity.action,
                activity.details or ''
            ])

        activities_table = Table(activities_data)
        activities_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(activities_table)

    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'activities_{current_user.name}_{today}.pdf',
        mimetype='application/pdf'
    )

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Fixed admin credentials
        if name == 'priscilla' and email == 'speantagtradingent@gmail.com' and password == 'admin123':
            session['admin_logged_in'] = True
            # Log admin login
            log_user_activity(None, 'Admin Login', f'Admin {name} logged in', risk_level='low', metadata={'admin_name': name})
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials!', 'error')

    return render_template('admin_login.html')

@app.route('/admin-logout')
def admin_logout():
    # Log admin logout
    log_user_activity(None, 'Admin Logout', 'Admin logged out', risk_level='low', metadata={'admin_name': 'priscilla'})
    session.pop('admin_logged_in', None)
    flash('Admin logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/resolve-alert/<int:alert_id>', methods=['POST'])
def resolve_alert(alert_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    alert = FraudAlert.query.get_or_404(alert_id)
    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = 'priscilla'  # Admin name

    db.session.commit()

    # Log the resolution
    log_user_activity(None, 'Fraud Alert Resolved', f'Resolved alert: {alert.description}', risk_level='low',
                     metadata={'alert_id': alert_id, 'admin_name': 'priscilla'})

    flash('Fraud alert resolved successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/save-page-activities/<page_name>', methods=['POST'])
@login_required
def save_page_activities(page_name):
    """Save user's activities for the current page/session"""
    try:
        # Get user's activities for the current session
        session_id = session.get('user_session_id')
        if not session_id:
            flash('No active session found!', 'error')
            return redirect(request.referrer or url_for('index'))

        # Get activities for this session and page
        activities = UserActivity.query.filter(
            UserActivity.user_id == current_user.id,
            UserActivity.session_id == session_id
        ).order_by(UserActivity.timestamp).all()

        # Convert activities to JSON
        activities_data = []
        for activity in activities:
            activities_data.append({
                'action': activity.action,
                'details': activity.details,
                'timestamp': activity.timestamp.isoformat(),
                'ip_address': activity.ip_address,
                'risk_level': activity.risk_level
            })

        # Save the activities
        saved_activity = SavedActivity(
            user_id=current_user.id,
            session_id=session_id,
            page_name=page_name,
            activities_data=json.dumps(activities_data),
            notes=request.form.get('notes', '')
        )

        db.session.add(saved_activity)
        db.session.commit()

        # Log the save action
        log_user_activity(current_user.id, 'Activities Saved', f'Saved activities for page: {page_name}')

        flash(f'Activities saved successfully for {page_name}!', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Error saving activities. Please try again.', 'error')
        print(f"Error saving activities: {e}")

    return redirect(request.referrer or url_for('index'))

@app.route('/my-activities')
@login_required
def my_activities():
    """View user's saved activities"""
    saved_activities = SavedActivity.query.filter_by(user_id=current_user.id).order_by(SavedActivity.saved_at.desc()).all()

    # Group activities by date
    activities_by_date = {}
    for activity in saved_activities:
        date_key = activity.saved_at.date()
        if date_key not in activities_by_date:
            activities_by_date[date_key] = []
        activities_by_date[date_key].append(activity)

    return render_template('my_activities.html', activities_by_date=activities_by_date)

@app.route('/view-saved-activity/<int:activity_id>')
@login_required
def view_saved_activity(activity_id):
    """View details of a specific saved activity"""
    saved_activity = SavedActivity.query.filter_by(id=activity_id, user_id=current_user.id).first_or_404()

    # Parse the activities data
    activities_data = json.loads(saved_activity.activities_data)

    return render_template('view_saved_activity.html',
                          saved_activity=saved_activity,
                          activities_data=activities_data)

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Get date range from query parameters
    start_date = request.args.get('start_date', date.today().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', date.today().strftime('%Y-%m-%d'))

    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()

    # Get financial data
    sales = DailySale.query.filter(
        DailySale.sale_date >= start_dt,
        DailySale.sale_date <= end_dt
    ).all()

    purchases = MarketPurchase.query.filter(
        MarketPurchase.purchase_date >= start_dt,
        MarketPurchase.purchase_date <= end_dt
    ).all()

    usage_records = InventoryUsage.query.filter(
        InventoryUsage.usage_date >= start_dt,
        InventoryUsage.usage_date <= end_dt
    ).all()

    # Calculate totals
    total_income = sum(sale.total_amount for sale in sales)
    total_expenses = sum(purchase.total_amount_spent for purchase in purchases)
    total_cost_used = sum(usage.cost_used for usage in usage_records)
    balance = total_income - total_expenses - total_cost_used
    profit_loss = balance

    # Get recent transactions (combine all types)
    transactions = []

    for sale in sales[-10:]:  # Last 10 sales
        transactions.append({
            'date': sale.sale_date,
            'description': f'Sale: {sale.item_name}',
            'category': 'Sales',
            'amount': sale.total_amount,
            'type': 'income'
        })

    for purchase in purchases[-10:]:  # Last 10 purchases
        transactions.append({
            'date': purchase.purchase_date,
            'description': f'Purchase: {purchase.total_amount_spent:.2f} spent',
            'category': 'Purchases',
            'amount': purchase.total_amount_spent,
            'type': 'expense'
        })

    for usage in usage_records[-10:]:  # Last 10 usage records
        item = InventoryItem.query.get(usage.inventory_item_id)
        transactions.append({
            'date': usage.usage_date,
            'description': f'Usage: {item.item_name if item else "Unknown"}',
            'category': 'Inventory Usage',
            'amount': usage.cost_used,
            'type': 'expense'
        })

    # Sort transactions by date (most recent first)
    transactions.sort(key=lambda x: x['date'], reverse=True)
    transactions = transactions[:20]  # Show last 20 transactions

    # Category breakdown
    category_breakdown = {
        'Sales': total_income,
        'Purchases': total_expenses,
        'Inventory Usage': total_cost_used
    }

    # Monthly summary (current month vs previous month)
    current_month = date.today().replace(day=1)
    prev_month = (current_month - timedelta(days=1)).replace(day=1)

    current_month_sales = DailySale.query.filter(
        DailySale.sale_date >= current_month
    ).all()
    prev_month_sales = DailySale.query.filter(
        DailySale.sale_date >= prev_month,
        DailySale.sale_date < current_month
    ).all()

    current_month_income = sum(s.total_amount for s in current_month_sales)
    prev_month_income = sum(s.total_amount for s in prev_month_sales)

    monthly_summary = {
        'current_month': current_month.strftime('%B %Y'),
        'current_income': current_month_income,
        'prev_month': prev_month.strftime('%B %Y'),
        'prev_income': prev_month_income,
        'growth': ((current_month_income - prev_month_income) / prev_month_income * 100) if prev_month_income > 0 else 0
    }

    # Get comprehensive activity data
    activities = UserActivity.query.join(User).order_by(UserActivity.timestamp.desc()).limit(100).all()

    # Get fraud alerts
    fraud_alerts = FraudAlert.query.order_by(FraudAlert.timestamp.desc()).limit(20).all()
    unresolved_alerts = FraudAlert.query.filter_by(resolved=False).order_by(FraudAlert.timestamp.desc()).all()

    # Get user session tracking
    user_sessions = {}
    for activity in activities:
        if activity.session_id:
            if activity.session_id not in user_sessions:
                user_sessions[activity.session_id] = {
                    'user_id': activity.user_id,
                    'user_name': User.query.get(activity.user_id).name if User.query.get(activity.user_id) else 'Unknown',
                    'login_time': None,
                    'logout_time': None,
                    'activities': [],
                    'ip_address': activity.ip_address,
                    'user_agent': activity.user_agent
                }

            session_data = user_sessions[activity.session_id]
            session_data['activities'].append(activity)

            if activity.action == 'Login':
                session_data['login_time'] = activity.timestamp
            elif activity.action == 'Logout':
                session_data['logout_time'] = activity.timestamp

    # Get user stats
    users = User.query.all()
    total_users = len(users)
    active_users_today = len(set(a.user_id for a in activities if a.timestamp.date() == date.today()))

    # Get risk analysis
    high_risk_activities = [a for a in activities if a.risk_level in ['high', 'critical']]
    suspicious_ips = {}
    for activity in activities:
        if activity.ip_address:
            if activity.ip_address not in suspicious_ips:
                suspicious_ips[activity.ip_address] = []
            suspicious_ips[activity.ip_address].append(activity)

    # Filter suspicious IPs (more than 3 different users from same IP)
    suspicious_ips = {ip: acts for ip, acts in suspicious_ips.items() if len(set(a.user_id for a in acts)) > 3}

    return render_template('admin_dashboard.html',
                          total_income=total_income,
                          total_expenses=total_expenses,
                          balance=balance,
                          profit_loss=profit_loss,
                          transactions=transactions,
                          category_breakdown=category_breakdown,
                          monthly_summary=monthly_summary,
                          activities=activities,
                          fraud_alerts=fraud_alerts,
                          unresolved_alerts=unresolved_alerts,
                          user_sessions=user_sessions,
                          users=users,
                          total_users=total_users,
                          active_users_today=active_users_today,
                          high_risk_activities=high_risk_activities,
                          suspicious_ips=suspicious_ips,
                          start_date=start_date,
                          end_date=end_date)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 