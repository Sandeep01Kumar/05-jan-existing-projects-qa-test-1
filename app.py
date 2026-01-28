"""
Flask application that serves as the Python equivalent of the Node.js server.js.

This module implements an HTTP server bound to 127.0.0.1:3000 that responds to all
requests with status 200, Content-Type text/plain, and body 'Hello, World!\n'.

This is a complete rewrite of the original Node.js implementation with 100%
behavioral equivalence, migrating from JavaScript to Python 3 Flask.

Original Node.js implementation: server.js
"""

from flask import Flask, Response

# Configuration constants matching the original Node.js server.js (lines 3-4)
# Explicitly using 127.0.0.1 to match localhost-only binding behavior
HOST = '127.0.0.1'
# Using port 3000 to match original Node.js implementation (NOT Flask default 5000)
PORT = 3000

# Create Flask application instance
# This replaces: const server = http.createServer((req, res) => {...});
app = Flask(__name__)


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def hello(path):
    """
    Catch-all route handler that responds to all HTTP requests identically.
    
    This matches the Node.js behavior where http.createServer callback handles
    all incoming requests regardless of URL path or HTTP method.
    
    The original Node.js implementation (server.js lines 6-10):
        const server = http.createServer((req, res) => {
          res.statusCode = 200;
          res.setHeader('Content-Type', 'text/plain');
          res.end('Hello, World!\\n');
        });
    
    Args:
        path: The URL path (captured but unused, as all paths return the same response)
    
    Returns:
        Response: HTTP response with:
            - status: 200 OK
            - content_type: text/plain
            - body: 'Hello, World!\\n' (including newline character)
    """
    return Response(
        'Hello, World!\n',
        status=200,
        content_type='text/plain'
    )


if __name__ == '__main__':
    # Print startup message before starting the server
    # This matches the original Node.js console.log (server.js line 13):
    #   console.log(`Server running at http://${hostname}:${port}/`);
    print(f'Server running at http://{HOST}:{PORT}/')
    
    # Start the Flask development server
    # This replaces: server.listen(port, hostname, () => {...});
    # Note: debug=False to match production-like behavior of original Node.js server
    app.run(host=HOST, port=PORT)
