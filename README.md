# hao-backprop-test

Test project for Backprop integration. Do not touch!

## Overview

This repository serves as a "Hello World" test server for Backprop integration testing and validation purposes.

## Python/Flask Setup (Current)

### Requirements
- Python 3.9+ (developed with Python 3.12)
- pip

### Installation

```bash
# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
python app.py
```

The server will start on http://127.0.0.1:3000/

### Verification

```bash
curl http://127.0.0.1:3000/
```

Expected output: `Hello, World!`

## Node.js Setup (Legacy)

### Requirements
- Node.js v20.20.0+

### Running the Server

```bash
node server.js
```

The server will start on http://127.0.0.1:3000/

## Notes

- Both Python/Flask and Node.js implementations produce identical HTTP responses
- The server responds with "Hello, World!\n" (status 200, Content-Type: text/plain) for all HTTP methods and paths
- Network binding is restricted to localhost (127.0.0.1) for security
