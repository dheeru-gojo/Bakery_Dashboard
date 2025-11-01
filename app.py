from flask import Flask, request, jsonify, send_from_directory, Response
import os
from datetime import datetime, date, timedelta, timezone
import io
import csv
import sqlite3
import threading
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

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
    """Initialize database with sales and daily reports tables."""
    if not os.path.exists(DATABASE):
        conn = get_db_connection()
        c = conn.cursor()

        # Sales table
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

        # Customers table
        c.execute('''
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                timestamp TEXT NOT NULL,
                time TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY(transaction_id) REFERENCES sales(id)
            )
        ''')

        # Daily reports table
        c.execute('''
            CREATE TABLE daily_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                total_customers INTEGER,
                cash_sales REAL,
                upi_sales REAL,
                total_sales REAL,
                report_generated_at TEXT
            )
        ''')

        conn.commit()
        conn.close()

# Initialize database on startup
init_db()

# ===== SCHEDULER FOR END-OF-DAY REPORTS =====
def generate_daily_report():
    """Generate end-of-day report at 11 PM IST."""
    try:
        now_ist = get_ist_now()
        yesterday = (now_ist - timedelta(days=1)).strftime("%d-%m-%Y")

        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            # Get counts for yesterday
            c.execute('SELECT COUNT(*) as count FROM customers WHERE date = ?', (yesterday,))
            total_customers = c.fetchone()["count"] or 0

            c.execute('SELECT SUM(amount) as total FROM sales WHERE mode = ? AND date = ?', ("cash", yesterday))
            cash_sales = c.fetchone()["total"] or 0

            c.execute('SELECT SUM(amount) as total FROM sales WHERE mode = ? AND date = ?', ("upi", yesterday))
            upi_sales = c.fetchone()["total"] or 0

            total_sales = cash_sales + upi_sales
            report_time = now_ist.strftime("%Y-%m-%d %H:%M:%S")

            # Save report
            c.execute('''
                INSERT OR REPLACE INTO daily_reports 
                (date, total_customers, cash_sales, upi_sales, total_sales, report_generated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (yesterday, total_customers, cash_sales, upi_sales, total_sales, report_time))

            conn.commit()
            conn.close()

        print(f"Daily report generated for {yesterday}: {total_customers} customers, ₹{total_sales}")
    except Exception as e:
        print(f"Error generating daily report: {e}")

# Setup scheduler for 11 PM IST
scheduler = BackgroundScheduler(timezone=IST)
scheduler.add_job(generate_daily_report, 'cron', hour=23, minute=0)
scheduler.start()

# ===== ENDPOINTS FOR N8N WEBHOOK =====
@app.route("/api/add_sale", methods=["POST"])
def add_sale():
    """Generic endpoint to add any sale (cash or UPI)."""
    try:
        data = request.get_json()
        amount = float(data.get("amount", 0))
        mode = data.get("mode", "upi")

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

            sale_id = c.lastrowid

            c.execute('''
                INSERT INTO customers (transaction_id, timestamp, time, date)
                VALUES (?, ?, ?, ?)
            ''', (sale_id, timestamp, time_only, date_only))

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
    """Add cash sale with customer count."""
    try:
        data = request.get_json()
        amount = float(data.get("amount", 0))

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

            sale_id = c.lastrowid

            c.execute('''
                INSERT INTO customers (transaction_id, timestamp, time, date)
                VALUES (?, ?, ?, ?)
            ''', (sale_id, timestamp, time_only, date_only))

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
    """Add UPI sale with customer count."""
    try:
        data = request.get_json()
        amount = float(data.get("amount", 0))

        now_ist = get_ist_now()
        timestamp = now_ist.strftime("%Y-%m-%d %H:%M:%S")
        time_only = now_ist.strftime("%H:%M")
        date_only = now_ist.strftime("%d-%m-%Y")

        upi_time = data.get("time", time_only)
        upi_date = data.get("date", date_only)

        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            c.execute('''
                INSERT INTO sales (amount, mode, timestamp, time, date)
                VALUES (?, ?, ?, ?, ?)
            ''', (amount, "upi", timestamp, upi_time, upi_date))

            sale_id = c.lastrowid

            c.execute('''
                INSERT INTO customers (transaction_id, timestamp, time, date)
                VALUES (?, ?, ?, ?)
            ''', (sale_id, timestamp, upi_time, upi_date))

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
    """Returns today's sales with customer count."""
    try:
        today = get_ist_now().strftime("%d-%m-%Y")

        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            c.execute('SELECT time, amount FROM sales WHERE mode = ? AND date = ? ORDER BY time', ("cash", today))
            cash_sales = [{"time": row["time"], "amount": row["amount"]} for row in c.fetchall()]

            c.execute('SELECT time, amount FROM sales WHERE mode = ? AND date = ? ORDER BY time', ("upi", today))
            upi_sales = [{"time": row["time"], "amount": row["amount"]} for row in c.fetchall()]

            c.execute('SELECT COUNT(*) as count FROM customers WHERE date = ?', (today,))
            customer_count = c.fetchone()["count"] or 0

            conn.close()

        return jsonify({
            "cashSales": cash_sales,
            "upiSales": upi_sales,
            "customerCount": customer_count
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/dashboard_data")
def api_dashboard_data():
    """Returns aggregated totals with customer count."""
    try:
        today = get_ist_now().strftime("%d-%m-%Y")

        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            c.execute('SELECT SUM(amount) as total FROM sales WHERE mode = ? AND date = ?', ("cash", today))
            cash_total = c.fetchone()["total"] or 0

            c.execute('SELECT SUM(amount) as total FROM sales WHERE mode = ? AND date = ?', ("upi", today))
            upi_total = c.fetchone()["total"] or 0

            c.execute('SELECT COUNT(*) as count FROM customers WHERE date = ?', (today,))
            customer_count = c.fetchone()["count"] or 0

            total_sales = cash_total + upi_total

            c.execute('SELECT amount, mode, timestamp FROM sales ORDER BY timestamp DESC LIMIT 1')
            last_sale_row = c.fetchone()
            last_sale = last_sale_row if last_sale_row else None

            conn.close()

        last_sale_text = f"{last_sale['amount']} ({last_sale['mode']}) at {last_sale['timestamp']}" if last_sale else "N/A"

        return jsonify({
            "cashSales": cash_total,
            "upiSales": upi_total,
            "totalSales": total_sales,
            "customerCount": customer_count,
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

@app.route("/api/daily_report/<date_str>")
def api_daily_report(date_str):
    """Get daily report for a specific date (format: DD-MM-YYYY)."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            c.execute('SELECT * FROM daily_reports WHERE date = ?', (date_str,))
            report = c.fetchone()
            conn.close()

        if report:
            return jsonify(dict(report)), 200
        else:
            return jsonify({"error": "Report not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/latest_report")
def api_latest_report():
    """Get the latest daily report (for Telegram bot)."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            c.execute('SELECT * FROM daily_reports ORDER BY date DESC LIMIT 1')
            report = c.fetchone()
            conn.close()

        if report:
            return jsonify(dict(report)), 200
        else:
            return jsonify({"error": "No reports found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/all_reports")
def api_all_reports():
    """Get all daily reports."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT * FROM daily_reports ORDER BY date DESC')
            reports = [dict(row) for row in c.fetchall()]
            conn.close()

        return jsonify(reports), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/analytics/peak_hours")
def api_peak_hours():
    """Analyze peak hours based on historical data (for inventory planning)."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            # Get customer count by hour
            c.execute('''
                SELECT 
                    SUBSTR(time, 1, 2) as hour,
                    COUNT(*) as customer_count,
                    SUM(CASE WHEN s.mode = 'cash' THEN s.amount ELSE 0 END) as cash_sales,
                    SUM(CASE WHEN s.mode = 'upi' THEN s.amount ELSE 0 END) as upi_sales
                FROM customers cust
                LEFT JOIN sales s ON cust.transaction_id = s.id
                GROUP BY hour
                ORDER BY hour
            ''')

            peak_data = [dict(row) for row in c.fetchall()]
            conn.close()

        return jsonify(peak_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/analytics/daily_distribution")
def api_daily_distribution():
    """Get sales distribution by day of week (for inventory planning)."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()

            # Get stats by day
            c.execute('''
                SELECT 
                    date,
                    total_customers,
                    ROUND(cash_sales, 2) as cash_sales,
                    ROUND(upi_sales, 2) as upi_sales,
                    ROUND(total_sales, 2) as total_sales
                FROM daily_reports
                ORDER BY date DESC
                LIMIT 365
            ''')

            daily_data = [dict(row) for row in c.fetchall()]
            conn.close()

        return jsonify(daily_data), 200
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

        writer.writerow(['Date', 'Time', 'Amount', 'Mode', 'Full Timestamp'])

        for row in rows:
            writer.writerow([row["date"], row["time"], row["amount"], row["mode"], row["timestamp"]])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=bakery_sales.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/export_reports")
def export_reports():
    """Export all daily reports as CSV file."""
    try:
        with lock:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('SELECT * FROM daily_reports ORDER BY date DESC')
            rows = c.fetchall()
            conn.close()

        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(['Date', 'Total Customers', 'Cash Sales', 'UPI Sales', 'Total Sales', 'Report Generated At'])

        for row in rows:
            writer.writerow([row["date"], row["total_customers"], row["cash_sales"], row["upi_sales"], row["total_sales"], row["report_generated_at"]])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=bakery_daily_reports.csv"}
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