# 🍞 Speantag Bakery Expense & Inventory Tracking System

**Motto: "Making food medicinal for your health"**

A comprehensive Flask-based expense tracking system designed specifically for Speantag Bakery to streamline financial and inventory records.

## 🌟 Features

### 📄 Page 1: Daily Sales Recording
- Record daily sales activities with item name, quantity, and unit price
- Automatic calculation of total sales amount for each item
- Save data by date with support for record updates/deletes
- Real-time total calculation as you input data

### 📄 Page 2: Market Purchase Entry
- Input total amount taken to the market
- Record multiple items bought with quantity and unit price
- Auto-calculate total price per item
- System calculates total spent and remaining balance
- Store by date of purchase
- Automatic inventory updates when items are purchased

### 📄 Page 3: Inventory Usage & Profit Tracking
- Track total quantity in stock and cost per unit
- Record quantity used with automatic remaining quantity updates
- Auto-calculate cost used and expected profit
- Track item-level and overall profit/loss per session
- Real-time validation to prevent over-usage

### 📅 Summary & Reporting
- Generate monthly summaries with comprehensive statistics
- Filter data by date ranges
- Export reports to PDF or Excel format
- Track total revenue, expenses, and net profit
- Monitor current inventory status

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation Steps

1. **Clone or download the project files**

2. **Navigate to the project directory**
   ```bash
   cd Speantag_Bakery_Expense
   ```

3. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. **Install required dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your web browser and go to: `http://localhost:5000`

## 📊 System Overview

### Database Structure
The system uses SQLite database with the following models:

- **DailySale**: Records individual sales transactions
- **MarketPurchase**: Records market shopping trips
- **PurchaseItem**: Individual items purchased during market trips
- **InventoryItem**: Current inventory status for each item
- **InventoryUsage**: Records of inventory usage with profit calculations

### Key Features

#### 🛒 Daily Sales
- Simple form to record sales with automatic total calculation
- View recent sales for the current month
- Delete sales records with confirmation
- Real-time total calculation as you type

#### 🛍️ Market Purchase
- Dynamic form to add multiple items
- Automatic calculation of total spent and remaining balance
- Updates inventory automatically when items are purchased
- Tracks purchase history by date

#### 📦 Inventory Usage
- Select from available inventory items
- Record quantity used with automatic validation
- Calculate cost used and expected profit (30% margin)
- View current inventory status and recent usage

#### 📈 Reports & Analytics
- Comprehensive financial summaries
- Date range filtering
- Export to Excel (multiple sheets) or PDF
- Real-time statistics dashboard

## 💰 Financial Tracking

The system automatically calculates:
- **Total Revenue**: Sum of all sales
- **Total Expenses**: Sum of all market purchases
- **Cost Used**: Value of inventory items used
- **Expected Profit**: 30% margin on used inventory
- **Net Profit**: Revenue - Expenses - Cost Used + Expected Profit

## 🎨 User Interface

- **Modern, responsive design** with Bootstrap 5
- **Beautiful gradient themes** with bakery-inspired colors
- **Interactive elements** with hover effects and animations
- **Mobile-friendly** layout that works on all devices
- **Intuitive navigation** with clear icons and labels

## 📁 File Structure

```
Speantag_Bakery_Expense/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/            # HTML templates
│   ├── base.html         # Base template with navigation
│   ├── daily_sales.html  # Daily sales page
│   ├── market_purchase.html # Market purchase page
│   ├── inventory_usage.html # Inventory usage page
│   └── reports.html      # Reports and analytics page
└── static/               # Static files (CSS, JS)
    ├── css/
    └── js/
```

## 🔧 Configuration

The application uses the following default configuration:
- **Database**: SQLite (`bakery_expenses.db`)
- **Secret Key**: Configured for session management
- **Port**: 5000 (default Flask port)

## 📊 Data Export

### Excel Export
- Multiple sheets: Sales, Purchases, Inventory Usage
- Formatted data with proper headers
- Date range filtering

### PDF Export
- Professional report layout
- Summary statistics
- Detailed transaction tables
- Branded with Speantag Bakery header

## 🛡️ Data Validation

- **Input validation** for all forms
- **Quantity validation** to prevent over-usage
- **Date validation** for proper record keeping
- **Confirmation dialogs** for destructive actions

## 🔄 Workflow

1. **Record Sales**: Daily sales are recorded with item details
2. **Market Purchases**: When going to market, record all items bought
3. **Inventory Usage**: Track usage of purchased items
4. **Generate Reports**: View summaries and export data

## 🎯 Business Benefits

- **Streamlined Operations**: Easy recording of daily activities
- **Financial Transparency**: Clear view of revenue, expenses, and profit
- **Inventory Management**: Automatic tracking of stock levels
- **Data Export**: Professional reports for analysis and record keeping
- **Profit Tracking**: Real-time calculation of expected profits

## 🚀 Getting Started

1. Install the system following the installation steps above
2. Start with recording some sample sales data
3. Add market purchases to build inventory
4. Record inventory usage to see profit calculations
5. Generate reports to view overall performance

## 📞 Support

For technical support or questions about the system, please contact your IT consultant.

---

**Speantag Bakery** - Making food medicinal for your health 🍞❤️ 