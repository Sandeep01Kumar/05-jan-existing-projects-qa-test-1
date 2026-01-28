# hello_world

A simple "Hello, World!" HTTP server built with Python 3 and Flask.

> **Note:** This is a test project for backprop integration. Do not touch!

## Description

This project is a minimal HTTP server that responds with `Hello, World!` to all incoming requests. It serves as a demonstration of a basic Flask web application that binds to localhost on port 3000.

**Project Details:**
- **Name:** hello_world
- **Version:** 1.0.0
- **Author:** hxu
- **License:** MIT

## Features

- Returns `Hello, World!\n` response for all HTTP requests
- Responds with `Content-Type: text/plain` header
- Binds to `127.0.0.1:3000` (localhost only)
- Handles all URL paths with the same response

## Prerequisites

- **Python 3.9** or higher
- **pip** (Python package installer)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd hello_world
```

### 2. Set Up Virtual Environment (Recommended)

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running the Server

Start the Flask application:

```bash
python app.py
```

You should see the following output:
```
Server running at http://127.0.0.1:3000/
```

## API Endpoint

| Endpoint | Method | Response |
|----------|--------|----------|
| `http://127.0.0.1:3000/` | Any | `Hello, World!\n` |
| `http://127.0.0.1:3000/<any-path>` | Any | `Hello, World!\n` |

### Response Details

- **Status Code:** 200 OK
- **Content-Type:** `text/plain`
- **Body:** `Hello, World!\n`

### Example Request

```bash
curl -i http://127.0.0.1:3000/
```

### Example Response

```
HTTP/1.1 200 OK
Content-Type: text/plain; charset=utf-8
Content-Length: 14

Hello, World!
```

## Project Structure

```
hello_world/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
└── .gitignore          # Git ignore patterns
```

## Dependencies

- **Flask** >= 3.1.0 - Web application framework

## License

This project is licensed under the MIT License.

## Author

**hxu**
