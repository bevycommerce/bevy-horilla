'use strict';

/** The computer could not reach the server (no internet, server down, timeout). */
class NetworkError extends Error {
  constructor(message) {
    super(message || 'No connection to the server.');
    this.name = 'NetworkError';
  }
}

/** The server answered with an error status. */
class ApiError extends Error {
  constructor(status, message, code, body) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code || null;
    this.body = body;
  }
}

/** The saved login no longer works. The user must sign in again. */
class AuthError extends Error {
  constructor(message) {
    super(message || 'Your session has ended. Please sign in again.');
    this.name = 'AuthError';
  }
}

module.exports = { NetworkError, ApiError, AuthError };
