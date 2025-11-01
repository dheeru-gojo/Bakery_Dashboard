from flask import Flask, request, jsonify, send_from_directory, Response
import os
from datetime import datetime, date
import io
import csv

app = Flask(__name__)

# In-memory storage for demo (replace with DB in production)
sales = []

# ===== ENDPOINTS FOR N8N WEBHOOK =====
@app.route("/api/add_sale", methods=["POST"])
def add_sale():
    """Generic endpoint to add any sale (cash or UPI). Can be called by n8n or frontend."""
    data = request.get_json()
    amount = data.get("amount")
    mode = data.get("mode", "upi")  # Default to "upi" if not specified
    
    # Get current IST time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_only = datetime.now().strftime("%H:%M")
    
    sale_entry = {
        "amount": float(amount), 
        "mode": mode, 
        "timestamp": timestamp,
        "time": time_only,
        "date": date.today().isoformat()
    }
    sales.append(sale_entry)
    
    return jsonify({
        "status": "success", 
        "amount": amount, 
        "mode": mode, 
        "timestamp": timestamp
    })

@app.route("/api/add_cash", methods=["POST"])
def add_cash():
    """Specific endpoint for adding cash sales from the dashboard form."""
    data = request.get_json()
    amount = data.get("amount")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_only = datetime.now().strftime("%H:%M")
    
    sale_entry = {
        "amount": float(amount), 
        "mode": "cash", 
        "timestamp": timestamp,
        "time": time_only,
        "date": date.today().isoformat()
    }
    sales.append(sale_entry)
    
    return jsonify({
        "status": "success", 
        "amount": amount, 
        "mode": "cash", 
        "timestamp": timestamp
    })

@app.route("/api/add_upi", methods=["POST"])
def add_upi():
    """Specific endpoint for n8n to post UPI sales."""
    data = request.get_json()
    amount = data.get("amount")
    
    # n8n might send date and time separately or as timestamp
    upi_time = data.get("time", datetime.now().strftime("%H:%M"))
    upi_date = data.get("date", date.today().isoformat())
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    sale_entry = {
        "amount": float(amount), 
        "mode": "upi", 
        "timestamp": timestamp,
        "time": upi_time,
        "date": upi_date
    }
    sales.append(sale_entry)
    
    return jsonify({
        "status": "success", 
        "amount": amount, 
        "mode": "upi", 
        "timestamp": timestamp
    })

# ===== ENDPOINTS FOR DASHBOARD =====
@app.route("/api/sales/today")
def api_sales_today():
    """Returns today's sales broken down by cash and UPI with individual entries."""
    today = date.today().isoformat()
    
    cash_sales = [
        {"time": s.get("time", s["timestamp"].split()[1][:5]), "amount": s["amount"]} 
        for s in sales 
        if s.get("mode") == "cash" and s.get("date", s["timestamp"].split()[0]) == today
    ]
    
    upi_sales = [
        {"time": s.get("time", s["timestamp"].split()[1][:5]), "amount": s["amount"]} 
        for s in sales 
        if s.get("mode") == "upi" and s.get("date", s["timestamp"].split()[0]) == today
    ]
    
    return jsonify({
        "cashSales": cash_sales,
        "upiSales": upi_sales
    })

@app.route("/api/dashboard_data")
def api_dashboard_data():
    """Returns aggregated totals (legacy endpoint, kept for compatibility)."""
    today = date.today().isoformat()
    
    cash_sales = sum(
        float(s["amount"]) 
        for s in sales 
        if s.get("mode") == "cash" and s.get("date", s["timestamp"].split()[0]) == today
    )
    
    upi_sales = sum(
        float(s["amount"]) 
        for s in sales 
        if s.get("mode") == "upi" and s.get("date", s["timestamp"].split()[0]) == today
    )
    
    total_sales = cash_sales + upi_sales
    last_sale = sales[-1] if sales else {"amount": "N/A", "mode": "N/A", "timestamp": "N/A"}
    
    return jsonify({
        "cashSales": cash_sales,
        "upiSales": upi_sales,
        "totalSales": total_sales,
        "lastSale": f"{last_sale['amount']} ({last_sale['mode']}) at {last_sale['timestamp']}"
    })

@app.route("/api/all_sales")
def api_all_sales():
    """Returns all sales records."""
    return jsonify(sales)

@app.route("/export")
def export_csv():
    """Export all sales as CSV file."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Date', 'Time', 'Amount', 'Mode', 'Full Timestamp'])
    
    # Write sales data
    for sale in sales:
        writer.writerow([
            sale.get('date', sale['timestamp'].split()[0]),
            sale.get('time', sale['timestamp'].split()[1][:5]),
            sale['amount'],
            sale['mode'],
            sale['timestamp']
        ])
    
    # Prepare response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=bakery_sales.csv"}
    )

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
