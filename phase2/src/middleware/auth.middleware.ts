import { Request, Response, NextFunction } from 'express';
import { config } from '../config/config';
import { logger } from '../utils/logger';
import { AuthService } from '../services/auth.service';
import { UserService } from '../services/user.service';
import { Permission } from '../types/user.types';
import { Pool } from 'pg';

// Initialize services
let authService: AuthService;
let userService: UserService;

export function initializeAuthServices(pool: Pool) {
  authService = new AuthService(pool);
  userService = new UserService(pool);
}

/**
 * Extended Request interface with user information
 */
export interface AuthenticatedRequest extends Request {
  user?: {
    username: string;
    isAdmin: boolean;
    permissions: Permission[];
  };
  token?: string;
}

/**
 * Authentication middleware
 * Validates X-Authorization header and tracks token usage
 */
export async function authenticate(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> {
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
      error: 'Authentication failed due to invalid or missing AuthenticationToken.',
    });
    return;
  }

  try {
    // Extract token (handle both "Bearer token" and "token" formats)
    const token = authHeader.toLowerCase().startsWith('bearer ')
      ? authHeader.substring(7)
      : authHeader;

    if (!token) {
      throw new Error('Empty token');
    }

    // Validate token and get username
    const username = await authService.validateToken(token);
    
    if (!username) {
      res.status(403).json({
        error: 'Authentication failed due to invalid or missing AuthenticationToken.',
      });
      return;
    }

    // Increment token usage count
    await authService.incrementTokenUsage(token);

    // Get user info
    const user = await userService.findByUsername(username);
    
    if (!user) {
      res.status(403).json({
        error: 'Authentication failed due to invalid or missing AuthenticationToken.',
      });
      return;
    }

    // Attach user info to request
    req.user = {
      username: user.username,
      isAdmin: user.isAdmin,
      permissions: user.permissions,
    };
    req.token = token;

    logger.debug('Authentication successful', { username });
    next();
  } catch (error) {
    logger.warn('Authentication failed:', {
      error: error instanceof Error ? error.message : 'Unknown error',
    });

    res.status(403).json({
      error: 'Authentication failed due to invalid or missing AuthenticationToken.',
    });
  }
}

/**
 * Permission-based middleware factory
 * Checks if user has the required permission
 */
export function requirePermission(permission: Permission) {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.user) {
      res.status(403).json({
        error: 'Authentication failed due to invalid or missing AuthenticationToken.',
      });
      return;
    }

    // Admin permission grants all permissions
    if (req.user.permissions.includes('admin') || req.user.permissions.includes(permission)) {
      next();
      return;
    }

    res.status(401).json({
      error: 'You do not have permission to perform this action.',
    });
  };
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
      error: 'Authentication failed due to invalid or missing AuthenticationToken.',
    });
    return;
  }

  if (!req.user.isAdmin && !req.user.permissions.includes('admin')) {
    res.status(401).json({
      error: 'You do not have permission to perform this action.',
    });
    return;
  }

  next();
}