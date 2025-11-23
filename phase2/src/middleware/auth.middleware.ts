import { Request, Response, NextFunction } from 'express';
import { config } from '../config/config';
import { logger } from '../utils/logger';

/**
 * Extended Request interface with user information
 */
export interface AuthenticatedRequest extends Request {
  user?: {
    username: string;
    isAdmin: boolean;
  };
}

/**
 * Authentication middleware
 * Validates X-Authorization header
 * 
 * For Deliverable #1: Stub implementation
 * - If auth is disabled, always proceed
 * - If auth is enabled but not implemented, return 501
 * - If token is missing, return 403
 * 
 * For future: Implement JWT validation
 */
export function authenticate(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  const authHeader = req.get('X-Authorization');

  // If authentication is not enabled, allow all requests
  if (!config.auth.enabled) {
    logger.debug('Authentication disabled, allowing request');
    next();
    return;
  }

  // Check if auth header is present
  if (!authHeader) {
    logger.warn('Authentication failed: Missing X-Authorization header');
    res.status(403).json({
      error: 'Authentication failed',
      message: 'Missing X-Authorization header',
    });
    return;
  }

  // Stub: For Deliverable #1, accept any token format
  // TODO: Implement JWT validation for future deliverables
  
  try {
    // Extract token (handle both "Bearer token" and "token" formats)
    const token = authHeader.startsWith('bearer ')
      ? authHeader.substring(7)
      : authHeader;

    if (!token) {
      throw new Error('Empty token');
    }

    // TODO: Validate JWT token here
    // For now, accept any non-empty token and set default user
    req.user = {
      username: 'ece30861defaultadminuser',
      isAdmin: true,
    };

    logger.debug('Authentication successful (stub)', {
      username: req.user.username,
    });

    next();
  } catch (error) {
    logger.warn('Authentication failed:', {
      error: error instanceof Error ? error.message : 'Unknown error',
    });

    res.status(403).json({
      error: 'Authentication failed',
      message: 'Invalid or malformed X-Authorization token',
    });
  }
}
import { verifyToken } from '../utils/auth.utils';

export function authenticateToken(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token provided' });
  try {
    const user = verifyToken(token);
    (req as any).user = user;
    next();
  } catch (err) {
    return res.status(403).json({ error: 'Invalid or expired token' });
  }
}

/**
 * Optional authentication middleware
 * Attempts to authenticate but allows request to proceed even if it fails
 * Useful for endpoints that have different behavior for authenticated users
 */
export function optionalAuthenticate(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  const authHeader = req.get('X-Authorization');

  if (!authHeader || !config.auth.enabled) {
    next();
    return;
  }

  try {
    const token = authHeader.startsWith('bearer ')
      ? authHeader.substring(7)
      : authHeader;

    if (token) {
      // TODO: Validate JWT token
      req.user = {
        username: 'ece30861defaultadminuser',
        isAdmin: true,
      };
    }
  } catch (error) {
    // Ignore authentication errors for optional auth
    logger.debug('Optional authentication failed, proceeding anyway');
  }

  next();
}

/**
 * Admin-only middleware
 * Requires authentication and admin privileges
 */
export function requireAdmin(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): void {
  if (!req.user) {
    res.status(403).json({
      error: 'Authentication required',
      message: 'This endpoint requires authentication',
    });
    return;
  }

  if (!req.user.isAdmin) {
    res.status(401).json({
      error: 'Unauthorized',
      message: 'This endpoint requires admin privileges',
    });
    return;
  }

  next();
}
