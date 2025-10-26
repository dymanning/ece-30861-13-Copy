import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';

/**
 * Custom error class with status code
 */
export class AppError extends Error {
  statusCode: number;
  isOperational: boolean;

  constructor(message: string, statusCode: number = 500) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true; // Operational errors vs programming errors

    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Common error types
 */
export class BadRequestError extends AppError {
  constructor(message: string = 'Bad Request') {
    super(message, 400);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = 'Unauthorized') {
    super(message, 401);
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = 'Forbidden') {
    super(message, 403);
  }
}

export class NotFoundError extends AppError {
  constructor(message: string = 'Not Found') {
    super(message, 404);
  }
}

export class PayloadTooLargeError extends AppError {
  constructor(message: string = 'Payload Too Large') {
    super(message, 413);
  }
}

export class InternalServerError extends AppError {
  constructor(message: string = 'Internal Server Error') {
    super(message, 500);
  }
}

/**
 * Error response formatter
 */
function formatErrorResponse(error: AppError, includeStack: boolean = false) {
  const response: any = {
    error: error.name,
    message: error.message,
    statusCode: error.statusCode,
  };

  if (includeStack && error.stack) {
    response.stack = error.stack;
  }

  return response;
}

/**
 * Global error handling middleware
 * Must be registered after all routes
 */
export function errorHandler(
  err: Error | AppError,
  req: Request,
  res: Response,
  next: NextFunction
): void {
  // Default to 500 if status code not set
  const statusCode = (err as AppError).statusCode || 500;

  // Log error
  logger.error('Error handling request:', {
    method: req.method,
    url: req.url,
    statusCode,
    message: err.message,
    stack: err.stack,
  });

  // Determine if we should include stack trace
  const includeStack = process.env.NODE_ENV === 'development';

  // Send error response
  res.status(statusCode).json(
    formatErrorResponse(
      err as AppError,
      includeStack
    )
  );
}

/**
 * Async error wrapper
 * Wraps async route handlers to catch errors
 * 
 * Usage:
 *   router.get('/path', asyncHandler(async (req, res) => {
 *     // async code
 *   }));
 */
export function asyncHandler(
  fn: (req: Request, res: Response, next: NextFunction) => Promise<any>
) {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

/**
 * 404 Not Found handler
 * Catches all unmatched routes
 */
export function notFoundHandler(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const error = new NotFoundError(
    `Route not found: ${req.method} ${req.url}`
  );
  next(error);
}

/**
 * Validation error handler
 * Converts validation errors to 400 responses
 */
export function handleValidationError(message: string): never {
  throw new BadRequestError(message);
}

/**
 * Database error handler
 * Converts database errors to appropriate HTTP errors
 */
export function handleDatabaseError(error: any): never {
  logger.error('Database error:', error);

  // Check for specific PostgreSQL error codes
  if (error.code === '23505') {
    // Unique violation
    throw new BadRequestError('Resource already exists');
  } else if (error.code === '23503') {
    // Foreign key violation
    throw new BadRequestError('Referenced resource does not exist');
  } else if (error.code === '23502') {
    // Not null violation
    throw new BadRequestError('Required field is missing');
  } else if (error.code === '57014') {
    // Query canceled (timeout)
    throw new PayloadTooLargeError(
      'Query timeout: request is too complex or returns too many results'
    );
  }

  // Generic database error
  throw new InternalServerError('Database operation failed');
}

/**
 * Regex error handler
 * Converts regex validation errors to 400 responses
 */
export function handleRegexError(error: Error): never {
  throw new BadRequestError(`Invalid regex pattern: ${error.message}`);
}
