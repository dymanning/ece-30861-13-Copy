import { Router } from 'express';
import { register, login, logout, deleteUser, getAllUsers } from '../controllers/auth.controller';
import { authenticate, requireAdmin } from '../middleware/auth.middleware';

const router = Router();

/**
 * PUT /authenticate
 * Login endpoint - returns bearer token
 * Per spec: "The system should permit authentication using a combination of 
 * username + secure password and yield a token"
 */
router.put('/authenticate', login);

/**
 * POST /register  
 * Register new user (admin only)
 * Per spec: "Only administrators can register users"
 */
router.post('/register', authenticate, requireAdmin, register);

/**
 * DELETE /user/:username
 * Delete user account
 * Per spec: "Users can delete their own accounts. Administrators can delete any account."
 */
router.delete('/user/:username', authenticate, deleteUser);

/**
 * POST /logout
 * Logout user (invalidate token)
 */
router.post('/logout', authenticate, logout);

/**
 * GET /users
 * Get all users (admin only)
 */
router.get('/users', authenticate, requireAdmin, getAllUsers);

export default router;