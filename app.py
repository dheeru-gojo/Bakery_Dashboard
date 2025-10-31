from flask import Flask, request, render_template_string, jsonify, send_file
import sqlite3
import pandas as pd
import os
from datetime import datetime, date

app = Flask(__name__)
DB_FILE = 'sales.db'

# Initialize SQLite DB (run once)
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_type TEXT NOT NULL,
            amount REAL NOT NULL,
            time TEXT NOT NULL
        )
        ''')
        conn.commit()

init_db()

def add_sale(sale_type, amount):
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('INSERT INTO sales (sale_type, amount, time) VALUES (?, ?, ?)', (sale_type, amount, now))
        conn.commit()

def get_sales_for_day(day):
    day_start = day.strftime("%Y-%m-%d") + "T00:00:00"
    day_end = day.strftime("%Y-%m-%d") + "T23:59:59"
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT sale_type, amount, time FROM sales WHERE time BETWEEN ? AND ?", (day_start, day_end))
        return c.fetchall()

def get_all_sales():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT sale_type, amount, time FROM sales ORDER BY time")
        return c.fetchall()

@app.route('/', methods=['GET'])
def home():
    return 'Bakery POS Cloud is running!'

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    msg = None
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            add_sale('cash', amount)
            msg = f"Added cash sale: ₹{amount:.2f}"
        except Exception:
            msg = "Invalid input."

    today = date.today()
    sales = get_sales_for_day(today)
    cash_today = sum(amt for typ, amt, t in sales if typ == 'cash')
    upi_today = sum(amt for typ, amt, t in sales if typ == 'upi')
    cash_history = [(t[11:16], amt) for typ, amt, t in sales if typ == 'cash']
    upi_history = [(t[11:16], amt) for typ, amt, t in sales if typ == 'upi']

    return render_template_string("""
    <h2>Bakery POS Sales Dashboard (Persistent)</h2>
    <p style="color:green;">{{msg}}</p>
    <b>Today's Cash Sales:</b> ₹{{cash_today}}
    <br>
    <b>Today's UPI Sales:</b> ₹{{upi_today}}
    <br><br>
    <form method="post" style="margin-bottom:20px;">
        <label>Enter Cash Sale:</label>
        <input name="amount" type="number" step="0.01" required>
        <button type="submit">Add Cash</button>
    </form>
    <b>Cash sales (today):</b>
    <ul>
        {% for t, amt in cash_history %}
            <li>{{t}} - ₹{{amt}}</li>
        {% endfor %}
    </ul>
    <b>UPI sales (today):</b>
    <ul>
        {% for t, amt in upi_history %}
            <li>{{t}} - ₹{{amt}}</li>
        {% endfor %}
    </ul>
    <a href="/export">Download Sales Excel (All Records)</a>
    """, cash_today=cash_today, upi_today=upi_today, cash_history=cash_history, upi_history=upi_history, msg=msg)

@app.route('/api/add_upi_sale', methods=['POST'])
def add_upi():
    try:
        data = request.get_json()
        amount = float(data.get('amount'))
        add_sale('upi', amount)
        return jsonify({'status': 'success', 'added': amount}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'reason': str(e)}), 400

@app.route('/export')
def export_sales():
    # Export all sales to Excel (as CSV, which Excel opens)
    sales = get_all_sales()
    df = pd.DataFrame(sales, columns=['Type', 'Amount', 'DateTime'])
    export_file = 'sales_records.csv'
    df.to_csv(export_file, index=False)
    return send_file(export_file, as_attachment=True, download_name="sales_records.csv")

@app.route('/api/transaction/sms', methods=['GET', 'POST'])
def transaction_sms():
    if request.method == 'GET':
        return "API endpoint reachable", 200
    else:
        data = request.get_json()
        return jsonify({'message': 'Received', 'data': data}), 200

if __name__ == "__main__":
    app.run(debug=True)
