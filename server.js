/**
 * @file Hello World HTTP Server
 * @module server
 * @description A simple HTTP server using the Node.js built-in http module. The server
 * listens on a configurable hostname and port, responding to all incoming HTTP requests
 * with a plain-text "Hello, World!" message. This is the primary entry point for the
 * hello_world application.
 * @example
 * // Start the server:
 * // node server.js
 * // Then visit http://127.0.0.1:3000/ or run:
 * // curl http://127.0.0.1:3000/
 */
const http = require('http');

/**
 * @constant {string} hostname
 * @description The hostname on which the server will listen. Set to the loopback
 * address '127.0.0.1', restricting access to the local machine only.
 * @default '127.0.0.1'
 */
const hostname = '127.0.0.1';
/**
 * @constant {number} port
 * @description The port number on which the server will listen for incoming HTTP requests.
 * @default 3000
 */
const port = 3000;

/**
 * @description Creates an HTTP server that handles all incoming requests by responding
 * with a 200 OK status, Content-Type: text/plain header, and a "Hello, World!\n" body.
 * The server instance is created using {@link http.createServer}.
 * @param {http.IncomingMessage} req - The incoming HTTP request object.
 * @param {http.ServerResponse} res - The server response object used to send data back to the client.
 */
const server = http.createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain');
  res.end('Hello, World!\n');
});

/**
 * @description Starts the HTTP server, binding it to the specified hostname and port.
 * Once the server is ready and listening, the callback logs the server URL to stdout.
 */
server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});
