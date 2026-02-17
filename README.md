# hello_world

A simple Node.js tutorial server powered by [Express.js](https://expressjs.com/), hosting two endpoints that return plain-text responses. This project serves as a Backprop test fixture.

## Prerequisites

- [Node.js](https://nodejs.org/) >= 18
- npm (included with Node.js)

## Installation

Clone the repository, then install dependencies:

```bash
npm install
```

This installs Express.js and all required dependencies into `node_modules/`.

## Startup

Start the server with:

```bash
node server.js
```

Or use the npm start script:

```bash
npm start
```

The server will start and listen at **http://127.0.0.1:3000/**.

## Endpoints

| Method | Path       | Response            | Content-Type | Status |
|--------|------------|---------------------|--------------|--------|
| GET    | `/`        | `Hello, World!\n`   | text/plain   | 200    |
| GET    | `/evening` | `Good evening`      | text/plain   | 200    |

### Examples

```bash
# Hello World endpoint
curl http://127.0.0.1:3000/
# => Hello, World!

# Good Evening endpoint
curl http://127.0.0.1:3000/evening
# => Good evening
```

## Dependencies

| Package   | Version | Purpose                          |
|-----------|---------|----------------------------------|
| express   | ^5.2.1  | Web framework for routing and HTTP server |

## License

[MIT](https://opensource.org/licenses/MIT)
