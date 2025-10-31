from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import os

app = Flask(__name__)
CORS(app)

# Track count and total amount
counter = {
    'cash_count': 0,
    'cash_total': 0.0,
    'upi_count': 0,
    'upi_total': 0.0
}

def parse_upi_sms(sms_text):
    """Extract UPI amount and details from SMS"""
    # Pattern: "INR 100.00 credited/debited"
    amount_match = re.search(r'(?:INR|Rs\.?)\s*(\d+(?:\.\d{2})?)', sms_text, re.IGNORECASE)
    if amount_match and any(word in sms_text.lower() for word in ['credited', 'debited', 'upi']):
        return {
            'success': True,
            'amount': float(amount_match.group(1)),
            'type': 'UPI'
        }
    return None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/transaction/cash', methods=['POST'])
def cash():
    """Record cash transaction"""
    try:
        data = request.get_json() or {}
        amount = float(data.get('amount', 0))
        
        counter['cash_count'] += 1
        counter['cash_total'] += amount
        
        return jsonify({
            'success': True,
            'today_counts': get_counts()
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/transaction/sms', methods=['POST'])
def sms():
    """Receive SMS and auto-increment UPI count"""
    try:
        data = request.get_json() or {}
        sms_text = data.get('sms_text', '')
        
        parsed = parse_upi_sms(sms_text)
        if parsed:
            counter['upi_count'] += 1
            counter['upi_total'] += parsed['amount']
            return jsonify({
                'success': True,
                'message': 'UPI transaction detected',
                'parsed': parsed,
                'today_counts': get_counts()
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Not a UPI transaction'
            }), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/transaction/upi', methods=['POST'])
def upi():
    """Manual UPI button (for testing)"""
    try:
        data = request.get_json() or {}
        amount = float(data.get('amount', 100))  # Default 100 if not specified
        
        counter['upi_count'] += 1
        counter['upi_total'] += amount
        
        return jsonify({
            'success': True,
            'today_counts': get_counts()
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/dashboard/today', methods=['GET'])
def dashboard():
    return jsonify(get_counts()), 200

def get_counts():
    total_sales = counter['cash_total'] + counter['upi_total']
    total_customers = counter['cash_count'] + counter['upi_count']
    
    return {
        'Total': total_customers,
        'Cash': counter['cash_count'],
        'UPI': counter['upi_count'],
        'Cash_total': round(counter['cash_total'], 2),
        'UPI_total': round(counter['upi_total'], 2),
        'Total_sales': round(total_sales, 2)
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
