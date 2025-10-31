from flask import Flask, request, render_template_string, jsonify, send_file
import sqlite3
import pandas as pd
import os
from datetime import datetime, date

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(__file__), 'sales.db')

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
    return 'Sinshi Bakery POS Cloud is running!'

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
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Sinshi Bakery Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background: #f5f6fa; }
            .card { box-shadow: 0 2px 10px #0001; margin-bottom: 24px; }
            h1, h2 { color: #562b04; }
            .btn-cash { background: #ffaf40; color: #fff; }
            .btn-cash:hover { background: #ffc353; color: #444; }
            .summary-box {
                border-radius: 14px;
                background: #fff;
                padding: 20px;
                margin-bottom: 20px;
                text-align: center;
            }
            .history-list { max-height: 180px; overflow-y:auto; }
            .refresh-btn { background: #2386ef; color: #fff; margin-left: 10px; }
            @media (max-width: 767px) {
                .summary-box, .card {padding: 12px;}
                .refresh-btn {margin: 10px 0 0 0;}
            }
        </style>
    </head>
    <body>
    <div class="container my-4">
        <div class="d-flex flex-column flex-md-row align-items-center justify-content-between">
            <h1 class="mb-2 text-center flex-grow-1">Sinshi Bakery</h1>
            <button class="refresh-btn btn btn-primary btn-lg" onclick="window.location.reload()">Refresh</button>
        </div>
        <h2 class="mb-4 text-center" style="font-size:1.4rem;">Sales Dashboard</h2>
        {% if msg %}
            <div class="alert alert-success text-center">{{ msg }}</div>
        {% endif %}
        <div class="row justify-content-center mb-3">
            <div class="col-12 col-md-5">
                <div class="summary-box mb-3">
                    <div class="fw-bold" style="font-size:1.2rem;">Today's Cash Sales</div>
                    <div class="display-6">₹{{ cash_today }}</div>
                </div>
            </div>
            <div class="col-12 col-md-5">
                <div class="summary-box mb-3">
                    <div class="fw-bold" style="font-size:1.2rem;">Today's UPI Sales</div>
                    <div class="display-6">₹{{ upi_today }}</div>
                </div>
            </div>
        </div>
        <div class="row justify-content-center mb-4">
            <div class="col-12 col-md-6">
                <div class="card p-3">
                    <h5 class="mb-3 text-center">Add a Cash Sale</h5>
                    <form method="post" class="d-flex align-items-center justify-content-center flex-wrap gap-2">
                        <input name="amount" class="form-control me-2" type="number" step="0.01" placeholder="Cash Sale Amount" style="max-width:140px;" required>
                        <button type="submit" class="btn btn-cash px-4">Add</button>
                    </form>
                </div>
            </div>
        </div>
        <div class="row gy-3">
            <div class="col-12 col-md-6">
                <div class="card p-3">
                    <h6 class="fw-bold mb-2">Cash Sales (Today)</h6>
                    <ul class="list-group history-list">
                    {% for t, amt in cash_history %}
                        <li class="list-group-item d-flex justify-content-between">
                            <span>{{ t }}</span> <span>₹{{ amt }}</span>
                        </li>
                    {% else %}
                        <li class="list-group-item">No cash sales yet</li>
                    {% endfor %}
                    </ul>
                </div>
            </div>
            <div class="col-12 col-md-6">
                <div class="card p-3">
                    <h6 class="fw-bold mb-2">UPI Sales (Today)</h6>
                    <ul class="list-group history-list">
                    {% for t, amt in upi_history %}
                        <li class="list-group-item d-flex justify-content-between">
                            <span>{{ t }}</span> <span>₹{{ amt }}</span>
                        </li>
                    {% else %}
                        <li class="list-group-item">No UPI sales yet</li>
                    {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
        <div class="text-center mt-4">
            <a href="/export" class="btn btn-success btn-lg">Download Sales Excel (All Records)</a>
        </div>
    </div>
    </body>
    </html>
    """,
    cash_today=cash_today,
    upi_today=upi_today,
    cash_history=cash_history,
    upi_history=upi_history,
    msg=msg)

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

# (Do NOT add if __name__ == "__main__": block)
