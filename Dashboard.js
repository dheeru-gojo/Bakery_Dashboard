// Run: npm install express ws
const express = require('express');
const WebSocket = require('ws');
const app = express();
app.use(express.json());

let wsClient = null;

const wss = new WebSocket.Server({port: 40510});
wss.on('connection', ws => { wsClient = ws; });

// n8n HTTP Request should POST to: http://localhost:40509/add-upi-sale
app.post('/add-upi-sale', (req, res) => {
    const {amount, date, time} = req.body;
    // Send to browser dashboard via WebSocket
    if (wsClient) wsClient.send(JSON.stringify({amount, date, time}));
    res.json({ok: 1});
});

app.listen(40509, () => console.log("UPI bridge server running on port 40509"));
