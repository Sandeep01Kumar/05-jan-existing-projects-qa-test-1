# hao-backprop-test

> **⚠️ Do not touch!** — This repository is a controlled test fixture for Backprop integration. All files are intentionally structured as test specimens. Any modifications documented below are controlled, intentional changes that do not invalidate the test baseline.

## Project Overview

This is a minimal Node.js "Hello World" HTTP server that serves as an integration test fixture for [Backprop](https://backprop.dev). The project is intentionally simple — a single-file, zero-external-dependency HTTP server using the Node.js built-in `http` module, bound exclusively to `127.0.0.1:3000`.

The repository's flat directory structure includes JavaScript source, Java stubs, CSV data, binary assets, empty placeholders, and deliberate "- Copy" duplicate files. This multi-format layout provides Backprop with a controlled environment to exercise code analysis, duplicate detection, refactoring, and AI-assisted development capabilities.

## Setup Instructions

### Prerequisites

- **Node.js** — Any version supporting CommonJS and the built-in `http` module (v18+ recommended for built-in test runner)
- **npm** — Version 7 or later (required for `lockfileVersion: 3`)

### Installation

```bash
npm install
```

> Note: This project has zero external dependencies. `npm install` confirms an empty dependency tree.

### Starting the Server

```bash
npm start
```

Or run directly:

```bash
node server.js
```

The server starts at `http://127.0.0.1:3000/` and responds to all requests with:

- **Status**: `200`
- **Content-Type**: `text/plain`
- **Body**: `Hello, World!\n`

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Starts the HTTP server on `127.0.0.1:3000` |
| `npm test` | Runs the server test suite via the Node.js built-in test runner |

## Project Structure

All files reside at the repository root in a flat directory layout. There are no subdirectories (by design).

### Application Files

| File | Purpose |
|------|---------|
| `index.js` | Canonical entry point (`main` field in `package.json`); imports and starts the server |
| `server.js` | HTTP server implementation using the built-in `http` module |
| `server.test.js` | Server test suite using Node.js built-in `node:test` and `node:assert` modules |

### Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | npm manifest — name `hello_world`, version `1.0.0`, MIT license, zero dependencies |
| `package-lock.json` | npm lockfile (`lockfileVersion: 3`) reflecting the empty dependency tree |
| `README.md` | This file — project documentation |

### Test Fixture Files (Do Not Modify)

These files are deliberately maintained as test specimens for Backprop's multi-format analysis capabilities. They must remain byte-for-byte identical to their current state.

| File | Type | Purpose |
|------|------|---------|
| `server - Copy.js` | JavaScript (duplicate) | Duplicate detection test specimen |
| `LoginTest.java` | Java (stub) | Multi-language detection test specimen; intentionally non-compiling |
| `LoginTest - Copy.java` | Java (duplicate stub) | Duplicate detection test specimen |
| `industry.csv` | CSV data | Data format handling test specimen (43 industry labels) |
| `industry - Copy.csv` | CSV (duplicate) | Duplicate detection test specimen |
| `test.py.txt` | Empty placeholder | Zero-content file handling test specimen |
| `test.py - Copy.txt` | Empty placeholder (duplicate) | Duplicate detection test specimen |
| `test.txt.txt` | Empty placeholder | Double-extension handling test specimen |
| `100Pages.pdf` | PDF binary | Binary format handling test specimen |
| `100Pages - Copy.pdf` | PDF (duplicate) | Duplicate detection test specimen |
| `demo.jpg` | JPEG image | Image format handling test specimen |
| `demo - Copy.jpg` | JPEG (duplicate) | Duplicate detection test specimen |
| `sample.doc` | Word document | Document format handling test specimen |
| `sample - Copy.doc` | Word document (duplicate) | Duplicate detection test specimen |

## Backprop Integration Notes

This repository is purpose-built as a Backprop integration test fixture. The multi-format file structure supports the following Backprop analysis capabilities:

- **Code Analysis**: JavaScript source (`server.js`) and Java stubs (`LoginTest.java`) provide language-specific analysis targets
- **Duplicate Detection**: The "- Copy" naming convention (7 duplicate file pairs) tests Backprop's ability to identify identical or near-identical files across formats
- **Multi-Language Detection**: JavaScript and Java files coexist, exercising cross-language scanning
- **Data Format Handling**: CSV, PDF, JPEG, and DOC files verify Backprop's non-code asset awareness
- **Edge Case Testing**: Zero-byte files (`test.py.txt`, `test.txt.txt`) and double-extension filenames test parser resilience
- **Non-Compiling Code**: The Java stubs contain intentionally invalid syntax (`Web` token) to test error tolerance

### Architecture Constraints

- **CommonJS modules** — All JavaScript uses `require()` / `module.exports`
- **Zero external dependencies** — Only Node.js built-in modules are used
- **Localhost-only networking** — Server binds to `127.0.0.1`; no external network exposure
- **Flat directory structure** — No subdirectories; all files at repository root
- **No build system** — Direct JavaScript interpretation with no transpilation or bundling

## Test Fixture Integrity Warning

The 14 test fixture files listed above under **Test Fixture Files (Do Not Modify)** must remain **byte-for-byte identical** to their current state. These files form the controlled baseline that Backprop uses for consistent integration testing. Modifying, renaming, or removing any of them will invalidate the test fixture and produce unreliable Backprop analysis results.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
