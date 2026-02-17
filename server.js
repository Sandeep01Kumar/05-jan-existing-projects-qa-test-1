// server.js — Express.js tutorial server
// A minimal Node.js server demonstrating basic routing with Express.js

const express = require('express');

// ---------------------------------------------------------------------------
// Server configuration
// ---------------------------------------------------------------------------
const HOSTNAME = '127.0.0.1'; // Bind to localhost only for security
const PORT = 3000;            // Default listening port

// Initialize the Express application
const app = express();

// ---------------------------------------------------------------------------
// Route definitions
// ---------------------------------------------------------------------------

// GET / — Returns a Hello World greeting in plain text
app.get('/', (req, res) => {
  res.type('text/plain').send('Hello, World!\n');
});

// GET /evening — Returns a Good Evening greeting in plain text
app.get('/evening', (req, res) => {
  res.type('text/plain').send('Good evening');
});

// ---------------------------------------------------------------------------
// Start the server
// ---------------------------------------------------------------------------
app.listen(PORT, HOSTNAME, () => {
  console.log(`Server running at http://${HOSTNAME}:${PORT}/`);
});
