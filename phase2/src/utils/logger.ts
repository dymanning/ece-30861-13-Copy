import winston from 'winston';
import { config } from '../config/config';
import * as fs from 'fs';
import * as path from 'path';

// Ensure logs directory exists
const logDir = path.dirname(config.logging.file);
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

/**
 * Custom log format
 */
const logFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.printf(({ timestamp, level, message, ...meta }) => {
    let log = `${timestamp} [${level.toUpperCase()}]: ${message}`;
    
    // Add metadata if present
    if (Object.keys(meta).length > 0) {
      log += ` ${JSON.stringify(meta)}`;
    }
    
    return log;
  })
);

/**
 * Winston logger instance
 */
export const logger = winston.createLogger({
  level: config.logging.level,
  format: logFormat,
  transports: [
    // Console transport
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        logFormat
      ),
    }),
    // File transport
    new winston.transports.File({
      filename: config.logging.file,
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    }),
    // Error file transport
    new winston.transports.File({
      filename: path.join(logDir, 'error.log'),
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    }),
  ],
});

/**
 * Log request details
 */
export function logRequest(
  method: string,
  url: string,
  statusCode: number,
  duration: number
): void {
  const level = statusCode >= 500 ? 'error' : statusCode >= 400 ? 'warn' : 'info';
  
  logger.log(level, 'HTTP Request', {
    method,
    url,
    statusCode,
    duration: `${duration}ms`,
  });
}

/**
 * Log database query
 */
export function logQuery(query: string, duration: number, rowCount: number): void {
  logger.debug('Database Query', {
    query: query.substring(0, 100),
    duration: `${duration}ms`,
    rowCount,
  });
}

/**
 * Log error with context
 */
export function logError(
  error: Error,
  context?: Record<string, any>
): void {
  logger.error(error.message, {
    stack: error.stack,
    ...context,
  });
}

// Export default logger
export default logger;
