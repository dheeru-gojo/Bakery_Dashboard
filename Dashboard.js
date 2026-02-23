// Simple browser-side handler for live UPI updates over WebSocket

const UPI_WS_URL = "wss://bakery-dashboard-dw72.onrender.com/upi-stream";

function connectUpiStream() {
  const ws = new WebSocket(UPI_WS_URL);

  ws.onopen = () => {
    console.log("Connected to UPI stream");
  };

  ws.onmessage = event => {
    try {
      const { amount, date, time } = JSON.parse(event.data);
      console.log("New UPI sale:", amount, date, time);

      // TODO: update your dashboard DOM here
      // e.g. increment totals, add a row to a table, etc.
    } catch (e) {
      console.error("Bad UPI message", e);
    }
  };

  ws.onclose = () => {
    console.log("UPI stream closed, reconnecting in 5s");
    setTimeout(connectUpiStream, 5000);
  };

  ws.onerror = err => {
    console.error("UPI stream error", err);
    ws.close();
  };
}

// Start WebSocket connection when page loads
if (typeof window !== "undefined") {
  window.addEventListener("load", connectUpiStream);
}
