import rateLimit from 'express-rate-limit';
import { Request, Response, NextFunction } from 'express';
import { config } from '../config/config';

/**
 * Global rate limiter middleware (per-IP)
 * Used to mitigate DoS from repeated requests, including uploads.
 */
export const globalRateLimiter = rateLimit({
  windowMs: config.upload.rateLimit.windowMs,
  max: config.upload.rateLimit.max,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    error: 'Too many requests',
    message: 'Rate limit exceeded. Please try again later.',
  },
});

/**
 * Upload payload size guard.
 * Rejects requests whose Content-Length exceeds configured max bytes.
 * Applies to endpoints that may accept large bodies.
 */
export function enforceUploadSize(req: Request, res: Response, next: NextFunction) {
  const contentLength = req.headers['content-length'];
  if (contentLength) {
    const len = parseInt(Array.isArray(contentLength) ? contentLength[0] : contentLength, 10);
    if (!Number.isNaN(len) && len > config.upload.maxBytes) {
      return res.status(413).json({
        error: 'Payload Too Large',
        message: `Upload exceeds limit of ${config.upload.maxBytes} bytes`,
      });
    }
  }
  next();
}

/**
 * Targeted rate limiter for upload-like endpoints.
 * Can be applied specifically to routes that mutate server state.
 */
export const uploadRateLimiter = rateLimit({
  windowMs: config.upload.rateLimit.windowMs,
  max: Math.max(5, Math.floor(config.upload.rateLimit.max / 3)), // stricter for uploads
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    error: 'Too many upload attempts',
    message: 'Upload rate limit exceeded. Please slow down.',
  },
});
