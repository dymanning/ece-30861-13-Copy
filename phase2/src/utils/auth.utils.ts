/**
 * Authentication utilities
 * 
 * This module previously contained JWT-based authentication.
 * We now use a custom token system with usage tracking in the database.
 * 
 * See:
 * - services/auth.service.ts for token generation and validation
 * - services/user.service.ts for password hashing and user management
 * - middleware/auth.middleware.ts for request authentication
 */

export {}; // Make this a module