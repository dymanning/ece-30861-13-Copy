import { Request, Response } from 'express';
import { Pool } from 'pg';
import { AuthService } from '../services/auth.service';
import { UserService } from '../services/user.service';
import { AuthenticatedRequest } from '../middleware/auth.middleware';
import { RegisterRequest, LoginRequest, Permission } from '../types/user.types';
import { logger } from '../utils/logger';

let authService: AuthService;
let userService: UserService;

export function initializeAuthController(pool: Pool) {
  authService = new AuthService(pool);
  userService = new UserService(pool);
}

/**
 * PUT /authenticate
 * Authenticate user and return bearer token
 * 
 * Request body (per spec):
 * {
 *   "User": {
 *     "name": "ece30861defaultadminuser",
 *     "isAdmin": true
 *   },
 *   "Secret": {
 *     "password": "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"
 *   }
 * }
 * 
 * Response:
 * "bearer <token>" - string bearer token valid for 1000 requests or 10 hours
 */
export async function login(req: Request, res: Response): Promise<void> {
  try {
    const { User, Secret } = req.body as LoginRequest;

    if (!User?.name || !Secret?.password) {
      res.status(400).json({
        error: 'There is missing field(s) in the AuthenticationRequest or it is formed improperly.',
      });
      return;
    }

    // Verify credentials
    const isValid = await userService.verifyPassword(User.name, Secret.password);
    
    if (!isValid) {
      res.status(401).json({
        error: 'The user or password is invalid.',
      });
      return;
    }

    // Generate token
    const token = await authService.createToken(User.name);

    // Return bearer token as plain string
    res.status(200).send(`bearer ${token}`);
    logger.info(`User authenticated: ${User.name}`);
  } catch (error) {
    logger.error('Login error:', error);
    res.status(500).json({
      error: 'The authentication failed due to internal server error.',
    });
  }
}

/**
 * POST /register
 * Register a new user (admin only)
 * 
 * Request body:
 * {
 *   "User": {
 *     "name": "username",
 *     "isAdmin": false
 *   },
 *   "Secret": {
 *     "password": "securepassword123"
 *   },
 *   "permissions": ["upload", "search", "download"]  // Optional, defaults based on isAdmin
 * }
 * 
 * Response: 200 OK on success
 */
export async function register(req: AuthenticatedRequest, res: Response): Promise<void> {
  try {
    const { User, Secret, permissions } = req.body as RegisterRequest;

    if (!User?.name || !Secret?.password) {
      res.status(400).json({
        error: 'There is missing field(s) in the request or it is formed improperly.',
      });
      return;
    }

    // Only admins can register users
    if (!req.user?.isAdmin && !req.user?.permissions.includes('admin')) {
      res.status(401).json({
        error: 'You do not have permission to register users.',
      });
      return;
    }

    // Check if user already exists
    const exists = await userService.userExists(User.name);
    if (exists) {
      res.status(409).json({
        error: 'User already exists.',
      });
      return;
    }

    // Determine permissions
    let userPermissions: Permission[];
    if (permissions) {
      userPermissions = permissions;
    } else if (User.isAdmin) {
      userPermissions = ['admin', 'upload', 'search', 'download'];
    } else {
      userPermissions = ['search', 'download']; // Default non-admin permissions
    }

    // Create user
    await userService.createUser(User.name, Secret.password, User.isAdmin, userPermissions);

    res.status(200).json({
      message: 'User registered successfully.',
    });
    logger.info(`User registered: ${User.name}`);
  } catch (error) {
    logger.error('Registration error:', error);
    res.status(500).json({
      error: 'The registration failed due to internal server error.',
    });
  }
}

/**
 * DELETE /user/:username
 * Delete a user account
 * Users can delete themselves, admins can delete anyone
 */
export async function deleteUser(req: AuthenticatedRequest, res: Response): Promise<void> {
  try {
    const { username } = req.params;

    if (!username) {
      res.status(400).json({
        error: 'Username is required.',
      });
      return;
    }

    // Check if user exists
    const userToDelete = await userService.findByUsername(username);
    if (!userToDelete) {
      res.status(404).json({
        error: 'User not found.',
      });
      return;
    }

    // Users can delete themselves, admins can delete anyone
    const isAdmin = req.user?.isAdmin || req.user?.permissions.includes('admin');
    const isSelf = req.user?.username === username;

    if (!isSelf && !isAdmin) {
      res.status(401).json({
        error: 'You do not have permission to delete this user.',
      });
      return;
    }

    // Delete all tokens for the user
    await authService.deleteAllUserTokens(username);

    // Delete user
    await userService.deleteUser(username);

    res.status(200).json({
      message: 'User deleted successfully.',
    });
    logger.info(`User deleted: ${username}`);
  } catch (error) {
    logger.error('Delete user error:', error);
    res.status(500).json({
      error: 'Failed to delete user due to internal server error.',
    });
  }
}

/**
 * POST /logout
 * Logout user (invalidate current token)
 */
export async function logout(req: AuthenticatedRequest, res: Response): Promise<void> {
  try {
    if (!req.token) {
      res.status(400).json({
        error: 'No token to logout.',
      });
      return;
    }

    await authService.deleteToken(req.token);

    res.status(200).json({
      message: 'Logged out successfully.',
    });
    logger.info(`User logged out: ${req.user?.username}`);
  } catch (error) {
    logger.error('Logout error:', error);
    res.status(500).json({
      error: 'Logout failed due to internal server error.',
    });
  }
}

/**
 * GET /users (admin only)
 * Get all users
 */
export async function getAllUsers(req: AuthenticatedRequest, res: Response): Promise<void> {
  try {
    const users = await userService.getAllUsers();
    res.status(200).json(users);
  } catch (error) {
    logger.error('Get users error:', error);
    res.status(500).json({
      error: 'Failed to retrieve users due to internal server error.',
    });
  }
}
