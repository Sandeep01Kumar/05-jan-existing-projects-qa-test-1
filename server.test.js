/**
 * server.test.js — HTTP Server Test Suite
 *
 * Unit and integration tests for the Hello World HTTP server.
 * Validates response status code (200), Content-Type header (text/plain),
 * and response body ("Hello, World!\n").
 *
 * Uses Node.js built-in test runner (node:test) and assertion module (node:assert)
 * with zero external dependencies, following the project's zero-dependency architecture.
 *
 * Run via: node --test server.test.js
 *          npm test
 */

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert');
const http = require('http');
const server = require('./server');

describe('Hello World HTTP Server', () => {
  // Use a different port than the default (3000) to avoid conflicts
  // if the main server is already running during development.
  const testPort = 3001;
  const testHostname = '127.0.0.1';

  // Start the server before all tests in this suite.
  // The server.js module exports the http.Server instance without auto-listening
  // when required as a module (require.main !== module guard).
  before((t, done) => {
    server.listen(testPort, testHostname, () => {
      done();
    });
  });

  // Shut down the server after all tests complete to release the port
  // and allow the process to exit cleanly.
  after((t, done) => {
    server.close(() => {
      done();
    });
  });

  it('should respond with status code 200', (t, done) => {
    http.get(`http://${testHostname}:${testPort}/`, (res) => {
      assert.strictEqual(res.statusCode, 200);
      // Consume the response data to allow the connection to close properly
      res.resume();
      res.on('end', () => {
        done();
      });
    }).on('error', (err) => {
      done(err);
    });
  });

  it('should respond with Content-Type text/plain', (t, done) => {
    http.get(`http://${testHostname}:${testPort}/`, (res) => {
      assert.strictEqual(res.headers['content-type'], 'text/plain');
      // Consume the response data to allow the connection to close properly
      res.resume();
      res.on('end', () => {
        done();
      });
    }).on('error', (err) => {
      done(err);
    });
  });

  it('should respond with Hello, World! body', (t, done) => {
    http.get(`http://${testHostname}:${testPort}/`, (res) => {
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        assert.strictEqual(data, 'Hello, World!\n');
        done();
      });
    }).on('error', (err) => {
      done(err);
    });
  });

  it('should respond consistently to multiple requests', (t, done) => {
    // First request
    http.get(`http://${testHostname}:${testPort}/`, (res1) => {
      let data1 = '';
      res1.on('data', (chunk) => {
        data1 += chunk;
      });
      res1.on('end', () => {
        // Second request to verify consistency
        http.get(`http://${testHostname}:${testPort}/`, (res2) => {
          let data2 = '';
          res2.on('data', (chunk) => {
            data2 += chunk;
          });
          res2.on('end', () => {
            assert.strictEqual(res1.statusCode, res2.statusCode);
            assert.strictEqual(res1.headers['content-type'], res2.headers['content-type']);
            assert.strictEqual(data1, data2);
            done();
          });
        }).on('error', (err) => {
          done(err);
        });
      });
    }).on('error', (err) => {
      done(err);
    });
  });

  it('should respond to requests on any path', (t, done) => {
    http.get(`http://${testHostname}:${testPort}/any/path`, (res) => {
      assert.strictEqual(res.statusCode, 200);
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      res.on('end', () => {
        assert.strictEqual(data, 'Hello, World!\n');
        done();
      });
    }).on('error', (err) => {
      done(err);
    });
  });
});
