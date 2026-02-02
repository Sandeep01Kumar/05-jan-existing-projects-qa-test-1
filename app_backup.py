"""
Backup Flask HTTP server application.

This file replaces the Node.js 'server - Copy.js' file, serving as a duplicate
variant for Backprop's duplicate detection testing. The implementation is
identical to app.py, providing a catch-all route that responds to all HTTP
methods and paths with 'Hello, World!\n'.

Configuration:
    - Host: 127.0.0.1 (localhost only)
    - Port: 3000
    - Response: 'Hello, World!\n' with status 200 and Content-Type: text/plain
"""

from flask import Flask, Response

# Create Flask application instance
# Equivalent to: const server = http.createServer((req, res) => {...})
app = Flask(__name__)


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])
def hello(path):
    """
    Catch-all request handler that responds to all HTTP methods and paths.
    
    This function mirrors the Node.js http.createServer callback behavior,
    returning an identical response regardless of the request method, path,
    headers, query parameters, or body content.
    
    Args:
        path: The URL path captured by the route (unused, for catch-all behavior)
    
    Returns:
        Response: Flask Response object with:
            - Body: 'Hello, World!\n'
            - Status: 200
            - Content-Type: text/plain
    
    Original Node.js implementation:
        res.statusCode = 200;
        res.setHeader('Content-Type', 'text/plain');
        res.end('Hello, World!\\n');
    """
    return Response(
        'Hello, World!\n',
        status=200,
        mimetype='text/plain'
    )


if __name__ == '__main__':
    # Start the Flask development server
    # Equivalent to: server.listen(port, hostname, () => {...})
    # Flask auto-logs startup to stderr, matching Node.js console.log behavior:
    # Original: console.log(`Server running at http://${hostname}:${port}/`)
    # Flask: * Running on http://127.0.0.1:3000
    app.run(host='127.0.0.1', port=3000)
