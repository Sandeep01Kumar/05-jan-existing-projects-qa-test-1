"""
Flask HTTP Server Application

This module implements a simple Hello World HTTP server using Flask,
replacing the original Node.js server.js implementation. It serves as
the primary entry point for the Backprop integration test fixture.

The server responds to ALL HTTP methods and ALL URL paths with an
identical response: "Hello, World!\n" (status 200, Content-Type: text/plain).

Network binding is restricted to localhost (127.0.0.1) on port 3000
for security purposes, matching the original Node.js implementation.

Original Node.js implementation (server.js):
    const http = require('http');
    const hostname = '127.0.0.1';
    const port = 3000;
    const server = http.createServer((req, res) => {
        res.statusCode = 200;
        res.setHeader('Content-Type', 'text/plain');
        res.end('Hello, World!\\n');
    });
    server.listen(port, hostname, () => {
        console.log(`Server running at http://${hostname}:${port}/`);
    });

Usage:
    python app.py

The server will start and listen on http://127.0.0.1:3000/
"""

from flask import Flask, Response

# Create Flask application instance
# Flask(__name__) uses the module name for resource location
app = Flask(__name__)


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def hello(path):
    """
    Catch-all request handler that responds to all HTTP methods and URL paths.
    
    This function mirrors the Node.js http.createServer() callback behavior,
    where all incoming requests receive the identical response regardless of:
    - HTTP method (GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS)
    - URL path (/, /api, /any/nested/path, etc.)
    - Query parameters
    - Request headers
    - Request body
    
    Args:
        path: The URL path captured by the route. This parameter is ignored
              as all paths receive the same response.
    
    Returns:
        Response: A Flask Response object with:
            - Body: "Hello, World!\\n" (with trailing newline)
            - Status: 200 OK
            - Content-Type: text/plain
    
    Example:
        curl http://127.0.0.1:3000/
        curl -X POST http://127.0.0.1:3000/api/endpoint
        curl http://127.0.0.1:3000/any/path?query=param
        
        All return: "Hello, World!\\n"
    """
    # Return response matching original Node.js implementation:
    # res.statusCode = 200;
    # res.setHeader('Content-Type', 'text/plain');
    # res.end('Hello, World!\n');
    return Response(
        'Hello, World!\n',
        status=200,
        mimetype='text/plain'
    )


if __name__ == '__main__':
    # Start the Flask development server
    # Matches original Node.js server.listen(port, hostname, callback) behavior:
    # - host='127.0.0.1': Bind to localhost only (security constraint)
    # - port=3000: Same port as original implementation
    # Flask automatically logs "* Running on http://127.0.0.1:3000" to stderr
    app.run(host='127.0.0.1', port=3000)
