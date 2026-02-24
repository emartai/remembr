export class RemembrError extends Error {
  code?: string;
  statusCode?: number;
  details?: Record<string, unknown>;
  requestId?: string;

  constructor(
    message: string,
    options: {
      code?: string;
      statusCode?: number;
      details?: Record<string, unknown>;
      requestId?: string;
    } = {}
  ) {
    super(message);
    this.name = 'RemembrError';
    this.code = options.code;
    this.statusCode = options.statusCode;
    this.details = options.details;
    this.requestId = options.requestId;
  }
}

export class AuthenticationError extends RemembrError {
  constructor(message: string, options: ConstructorParameters<typeof RemembrError>[1] = {}) {
    super(message, options);
    this.name = 'AuthenticationError';
  }
}

export class NotFoundError extends RemembrError {
  constructor(message: string, options: ConstructorParameters<typeof RemembrError>[1] = {}) {
    super(message, options);
    this.name = 'NotFoundError';
  }
}

export class RateLimitError extends RemembrError {
  constructor(message: string, options: ConstructorParameters<typeof RemembrError>[1] = {}) {
    super(message, options);
    this.name = 'RateLimitError';
  }
}

export class ServerError extends RemembrError {
  constructor(message: string, options: ConstructorParameters<typeof RemembrError>[1] = {}) {
    super(message, options);
    this.name = 'ServerError';
  }
}
