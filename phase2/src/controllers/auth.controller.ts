import { Request, Response } from 'express';
import { config } from '../config/config';
import { issueToken, comparePassword, hashPassword } from '../utils/auth.utils';

/**
 * Register a new user (lightweight stub)
 * Note: Full user DB integration is out of scope for this change.
 */
export async function register(req: Request, res: Response) {
  const { username, password, role } = req.body;
  if (!username || !password) {
    res.status(400).json({ error: 'username and password required' });
    return;
  }

  // Hash password (would persist to DB in a real implementation)
  const passwordHash = await hashPassword(password);

  // Return created user (stub)
  res.status(201).json({ username, role: role || 'user', passwordHash });
}

/**
 * Login endpoint (deprecated in favor of /authenticate). Kept for compatibility.
 */
export async function login(_req: Request, res: Response) {
  res.status(501).json({ error: 'Use PUT /authenticate per OpenAPI spec' });
}

export async function logout(_req: Request, res: Response) {
  // Token revocation would be implemented here
  res.status(200).json({ message: 'User logged out (no-op)' });
}

export async function resetPassword(_req: Request, res: Response) {
  res.status(501).json({ error: 'Password reset not implemented' });
}

/**
 * PUT /authenticate
 * Authentication endpoint following OpenAPI spec.
 * Body: { user: { name, is_admin }, secret: { password } }
 */
export async function authenticate(req: Request, res: Response) {
  // If auth not supported, return 501 per spec
  if (!config.auth.enabled) {
    res.status(501).json({ error: 'Authentication not supported' });
    return;
  }

  const body = req.body;
  if (!body || !body.user || !body.secret) {
    res.status(400).json({ error: 'Malformed AuthenticationRequest' });
    return;
  }

  const username = body.user.name;
  const isAdmin = !!body.user.is_admin;
  const password = body.secret.password;

  if (!username || !password) {
    res.status(400).json({ error: 'Missing username or password' });
    return;
  }

  // For this implementation, support the default admin credentials
  const DEFAULT_ADMIN = process.env.DEFAULT_ADMIN_USER || 'ece30861defaultadminuser';
  const DEFAULT_ADMIN_PASSWORD =
    process.env.DEFAULT_ADMIN_PASSWORD || "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages";

  // In a full implementation, look up user in DB and verify hashed password
  if (username === DEFAULT_ADMIN && password === DEFAULT_ADMIN_PASSWORD) {
    const token = issueToken({ id: username, role: isAdmin ? 'admin' : 'user' });
    // Return token as a string per spec (AuthenticationToken)
    res.status(200).json(`bearer ${token}`);
    return;
  }

  // Unknown user or bad password
  res.status(401).json({ error: 'Invalid user or password' });
}
