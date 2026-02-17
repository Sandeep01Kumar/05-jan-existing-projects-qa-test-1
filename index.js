// index.js — Canonical entry point for the hello_world package.
// Resolves the package.json "main": "index.js" field by importing,
// starting, and re-exporting the HTTP server from server.js.
//
// Usage:
//   node index.js          — starts the server on 127.0.0.1:3000
//   require('./index')     — returns the running server object
//
// Exports the server object (http.Server) with additional properties:
//   server.listen()   — bind and start listening (inherited from http.Server)
//   server.close()    — stop accepting new connections (inherited from http.Server)
//   server.hostname   — the hostname the server binds to ('127.0.0.1')
//   server.port       — the port the server listens on (3000)

const server = require('./server');

// Resolve hostname and port from the server module exports with
// backward-compatible defaults matching the original 127.0.0.1:3000 binding.
const hostname = server.hostname || '127.0.0.1';
const port = server.port || 3000;

// Start the HTTP server on localhost. This mirrors the original server.js
// behavior before the require.main guard was added, ensuring that running
// `node index.js` produces identical output to the original `node server.js`.
server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});

// Re-export the server object as the default module export, providing
// module consumers access to listen(), close(), hostname, and port.
module.exports = server;
