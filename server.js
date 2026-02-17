/**
 * @module hao-backprop-test
 * @description A minimal Node.js HTTP server that responds to all incoming requests
 * with a plain-text 'Hello, World!' message. This module serves as a test fixture
 * for Backprop integration testing and is designed for local development use only.
 * @version 1.0.0
 * @author hxu
 * @license MIT
 * @see {@link https://nodejs.org/api/http.html} Node.js HTTP Module Documentation
 * @example
 * // Start the server:
 * // $ node server.js
 * // Server running at http://127.0.0.1:3000/
 */

// Import the built-in Node.js HTTP module for creating the server (no external dependencies needed)
const http = require('http');

/**
 * @const {string} hostname
 * @description The IP address the server binds to. Set to '127.0.0.1' (IPv4 loopback),
 * restricting access to the local machine only. External connections are not accepted.
 * @default '127.0.0.1'
 * @example
 * // The server will only be accessible at:
 * // http://127.0.0.1:3000/
 */
const hostname = '127.0.0.1';

/**
 * @const {number} port
 * @description The TCP port number the server listens on. Port 3000 is a conventional
 * choice for Node.js development servers.
 * @default 3000
 */
const port = 3000;

/**
 * @type {http.Server}
 * @description Creates an HTTP server instance with a request handler callback. The handler
 * responds to every incoming HTTP request with a 200 OK status, 'text/plain' content type,
 * and a 'Hello, World!' message body. No routing or request differentiation is performed —
 * all methods and paths receive the identical response.
 * @param {http.IncomingMessage} req - The incoming HTTP request object. Contains request
 * method, URL, headers, and body stream. Not used by this handler as all requests receive
 * the same response.
 * @param {http.ServerResponse} res - The server response object. Used to set the status
 * code, headers, and write the response body back to the client.
 * @see {@link https://nodejs.org/api/http.html#httpcreateserveroptions-requestlistener}
 */
const server = http.createServer((req, res) => {
  // Set HTTP status code to 200 (OK) indicating a successful request
  res.statusCode = 200;
  // Set the Content-Type response header to indicate plain text content
  res.setHeader('Content-Type', 'text/plain');
  // Write the response body and signal that the response is complete
  res.end('Hello, World!\n');
});

/**
 * @description Starts the HTTP server, binding it to the specified hostname and port.
 * Once the server is successfully bound and ready to accept connections, the callback
 * function executes and logs the server URL to the console.
 * @param {number} port - The port number to listen on (3000)
 * @param {string} hostname - The hostname to bind to ('127.0.0.1')
 * @param {Function} callback - Startup notification callback — logs the server URL to stdout
 * @example
 * // Expected console output after server starts:
 * // Server running at http://127.0.0.1:3000/
 */
server.listen(port, hostname, () => {
  // Log the server URL to stdout to confirm successful startup
  console.log(`Server running at http://${hostname}:${port}/`);
});
