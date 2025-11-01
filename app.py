from flask import Flask, request, jsonify, send_from_directory
import os
from datetime import datetime

app = Flask(__name__)

# In-memory storage for demo (replace with DB in production)
sales = []

@app.route("/api/add_upi_sale", methods=["POST"])
def add_upi_sale():
    data = request.get_json()
    amount = data.get("amount")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sales.append({"amount": amount, "timestamp": timestamp})
    return jsonify({"status": "success", "amount": amount, "timestamp": timestamp})

@app.route("/api/dashboard_data")
def api_dashboard_data():
    total_sales = sum(float(s["amount"]) for s in sales if s["amount"])
    last_sale = sales[-1] if sales else {"amount": "N/A", "timestamp": "N/A"}
    return jsonify({
        "totalSales": total_sales,
        "lastSale": f"{last_sale['amount']} at {last_sale['timestamp']}"
    })

# NEW: Endpoint to return all sales as JSON for dashboard listing
@app.route("/api/all_sales")
def api_all_sales():
    return jsonify(sales)

# Serve dashboard page
@app.route('/')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

# Serve JS file if present
@app.route('/dashboard.js')
def dashboard_js():
    return send_from_directory('.', 'dashboard.js')

if __name__ == "__main__":
    app.run(debug=True)
