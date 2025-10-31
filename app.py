from flask import Flask, request, jsonify

app = Flask(__name__)

# Home route for debug/welcome message
@app.route('/', methods=['GET'])
def index():
    return 'Bakery POS Cloud is running!'

# Debug GET endpoint for browser check
@app.route('/api/transaction/sms', methods=['GET'])
def sms_transaction_get():
    return "API endpoint reachable", 200

# Main POST endpoint for your automation/integration
@app.route('/api/transaction/sms', methods=['POST'])
def sms_transaction_post():
    # Get the json payload from POST
    data = request.get_json()
    # (Do something with your POSTed data here)
    print("Received data:", data)
    # Respond with a confirmation
    return jsonify({'message': 'Received'}), 200

if __name__ == "__main__":
    app.run()
