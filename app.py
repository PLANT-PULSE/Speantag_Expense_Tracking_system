from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import os
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from decimal import Decimal, ROUND_HALF_UP

app = Flask(__name__)
app.config['SECRET_KEY'] = 'speantag_bakery_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bakery_expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

# Routes
@app.route('/')
def index():
    return redirect(url_for('daily_sales'))

@app.route('/daily-sales', methods=['GET', 'POST'])
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
        flash('Sale recorded successfully!', 'success')
        return redirect(url_for('daily_sales'))
    
    # Get sales for the current month
    current_month = date.today().replace(day=1)
    sales = DailySale.query.filter(DailySale.sale_date >= current_month).order_by(DailySale.sale_date.desc()).all()
    
    return render_template('daily_sales.html', sales=sales, today=date.today().strftime('%Y-%m-%d'))

@app.route('/delete-sale/<int:sale_id>')
def delete_sale(sale_id):
    sale = DailySale.query.get_or_404(sale_id)
    db.session.delete(sale)
    db.session.commit()
    flash('Sale deleted successfully!', 'success')
    return redirect(url_for('daily_sales'))

@app.route('/market-purchase', methods=['GET', 'POST'])
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
        flash('Market purchase recorded successfully!', 'success')
        return redirect(url_for('market_purchase'))
    
    # Get purchases for the current month
    current_month = date.today().replace(day=1)
    purchases = MarketPurchase.query.filter(MarketPurchase.purchase_date >= current_month).order_by(MarketPurchase.purchase_date.desc()).all()
    
    return render_template('market_purchase.html', purchases=purchases)

@app.route('/inventory-usage', methods=['GET', 'POST'])
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
        flash('Inventory usage recorded successfully!', 'success')
        return redirect(url_for('inventory_usage'))
    
    inventory_items = InventoryItem.query.filter(InventoryItem.remaining_quantity > 0).all()
    usage_records = InventoryUsage.query.order_by(InventoryUsage.usage_date.desc()).limit(20).all()
    
    return render_template('inventory_usage.html', inventory_items=inventory_items, usage_records=usage_records)

@app.route('/reports')
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 