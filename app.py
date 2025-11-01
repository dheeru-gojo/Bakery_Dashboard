from flask import Flask, request, jsonify, send_from_directory, Response
import os
from datetime import datetime, date, timedelta, timezone
import io
import csv
import sqlite3
import threading
import pytz

app = Flask(__name__)

# Database setup
DATABASE = 'bakery_sales.db'
lock = threading.Lock()

# IST Timezone
IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    """Get current time in IST."""
    return datetime.now(IST)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database with sales table."""
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                mode TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                time TEXT NOT NULL,
                date TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

# Initialize database on startup
init_db()

# ===== ENDPOINTS FOR N8N WEBHOOK =====
@app.route("/api/add_sale", methods=["POST"])
def add_sale():
    """Generic endpoint to add any sale (cash or UPI). Can be called by n8n or frontend."""
    try:
        data = request.get_json()
        amount = float(data.get("amount", 0))
        mode = data.get("mode", "upi")

        # Get current time in IST
        now_ist = get_ist_now()
        timestamp = now_ist.strftime("%Y-%m-%d %H:%M:%S")
        time_only = now_ist.strftime("%H:%M")
        date_only = now_ist.strftime("%d-%m-%Y")

        with lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO sales (amount, mode, timestamp, time, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (amount, mode, timestamp, time_only, date_only))
            conn.commit()
            conn.close()

        return jsonify({
            "status": "success", 
            "amount": amount, 
            "mode": mode, 
            "timestamp": timestamp
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/add_cash", methods=["POST"])
def add_cash():
    """Specific endpoint for adding cash sales from the dashboard form."""
    try:
        data = request.get_json()
        amount = float(data.get("amount", 0))

        # Get current time in IST
        now_ist = get_ist_now()
        timestamp = now_ist.strftime("%Y-%m-%d %H:%M:%S")
        time_only = now_ist.strftime("%H:%M")
        date_only = now_ist.strftime("%d-%m-%Y")

        with lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO sales (amount, mode, timestamp, time, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (amount, "cash", timestamp, time_only, date_only))
            conn.commit()
            conn.close()

        return jsonify({
            "status": "success", 
            "amount": amount, 
            "mode": "cash", 
            "timestamp": timestamp
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/add_upi", methods=["POST"])
def add_upi():
    """Specific endpoint for n8n to post UPI sales."""
    try:
        data = request.get_json()
        amount = float(data.get("amount", 0))

        # Get current time in IST
        now_ist = get_ist_now()
        timestamp = now_ist.strftime("%Y-%m-%d %H:%M:%S")
        time_only = now_ist.strftime("%H:%M")
        date_only = now_ist.strftime("%d-%m-%Y")

        # n8n might send date and time separately
        upi_time = data.get("time", time_only)
        upi_date = data.get("date", date_only)

        with lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO sales (amount, mode, timestamp, time, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (amount, "upi", timestamp, upi_time, upi_date))
            conn.commit()
            conn.close()

        return jsonify({
            "status": "success", 
            "amount": amount, 
            "mode": "upi", 
            "timestamp": timestamp
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

# ===== ENDPOINTS FOR DASHBOARD =====
@app.route("/api/sales/today")
def api_sales_today():
    """Returns today's sales broken down by cash and UPI with individual entries."""
    try:
        today = get_ist_now().strftime("%d-%m-%Y")

        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            # Get cash sales
            c.execute('SELECT time, amount FROM sales WHERE mode = ? AND date = ? ORDER BY time', ("cash", today))
            cash_sales = [{"time": row["time"], "amount": row["amount"]} for row in c.fetchall()]

            # Get UPI sales
            c.execute('SELECT time, amount FROM sales WHERE mode = ? AND date = ? ORDER BY time', ("upi", today))
            upi_sales = [{"time": row["time"], "amount": row["amount"]} for row in c.fetchall()]

            conn.close()

        return jsonify({
            "cashSales": cash_sales,
            "upiSales": upi_sales
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/dashboard_data")
def api_dashboard_data():
    """Returns aggregated totals."""
    try:
        today = get_ist_now().strftime("%d-%m-%Y")

        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            # Get totals
            c.execute('SELECT SUM(amount) as total FROM sales WHERE mode = ? AND date = ?', ("cash", today))
            cash_total = c.fetchone()["total"] or 0

            c.execute('SELECT SUM(amount) as total FROM sales WHERE mode = ? AND date = ?', ("upi", today))
            upi_total = c.fetchone()["total"] or 0

            total_sales = cash_total + upi_total

            # Get last sale
            c.execute('SELECT amount, mode, timestamp FROM sales ORDER BY timestamp DESC LIMIT 1')
            last_sale_row = c.fetchone()
            last_sale = last_sale_row if last_sale_row else None

            conn.close()

        last_sale_text = f"{last_sale['amount']} ({last_sale['mode']}) at {last_sale['timestamp']}" if last_sale else "N/A"

        return jsonify({
            "cashSales": cash_total,
            "upiSales": upi_total,
            "totalSales": total_sales,
            "lastSale": last_sale_text
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/all_sales")
def api_all_sales():
    """Returns all sales records."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT * FROM sales ORDER BY timestamp DESC')
            sales = [dict(row) for row in c.fetchall()]
            conn.close()

        return jsonify(sales), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/export")
def export_csv():
    """Export all sales as CSV file."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT date, time, amount, mode, timestamp FROM sales ORDER BY timestamp DESC')
            rows = c.fetchall()
            conn.close()

        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Date', 'Time', 'Amount', 'Mode', 'Full Timestamp'])

        # Write data
        for row in rows:
            writer.writerow([row["date"], row["time"], row["amount"], row["mode"], row["timestamp"]])

        # Prepare response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=bakery_sales.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ===== SERVE FRONTEND =====
@app.route('/')
def dashboard():
    """Serve the main dashboard HTML page."""
    return send_from_directory('.', 'dashboard.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve any other static files if needed."""
    return send_from_directory('.', path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)