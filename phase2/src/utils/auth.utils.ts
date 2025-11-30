import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { User } from '../types/user.types';

const JWT_SECRET = process.env.JWT_SECRET || 'supersecret';
const JWT_EXPIRES_IN = 10 * 60 * 60 * 1000; // 10 hours in ms
const JWT_EXPIRES_IN_SEC = 10 * 60 * 60; // 10 hours in seconds for jwt.sign
const MAX_REQUESTS = 1000;

// In-memory token store: token -> usage metadata
const tokenStore: Map<string, { remaining: number; expiresAt: number; payload: any }> = new Map();

export function issueToken(user: { id: string; role: string }) {
  const token = jwt.sign({ id: user.id, role: user.role }, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN_SEC });
  const expiresAt = Date.now() + JWT_EXPIRES_IN;
  tokenStore.set(token, { remaining: MAX_REQUESTS, expiresAt, payload: { id: user.id, role: user.role } });
  return token;
}

export function verifyAndConsume(token: string) {
  // Verify signature first
  const payload = jwt.verify(token, JWT_SECRET) as any;

  const entry = tokenStore.get(token);
  if (!entry) {
    // Token unknown (not issued by this server)
    const err: any = new Error('Unknown token');
    err.name = 'TokenError';
    throw err;
  }

  if (Date.now() > entry.expiresAt) {
    tokenStore.delete(token);
    const err: any = new Error('Token expired');
    err.name = 'TokenExpiredError';
    throw err;
  }

  if (entry.remaining <= 0) {
    tokenStore.delete(token);
    const err: any = new Error('Token usage limit exceeded');
    err.name = 'TokenUsageExceeded';
    throw err;
  }

  // Consume one usage
  entry.remaining -= 1;
  tokenStore.set(token, entry);

  return { payload: entry.payload, remaining: entry.remaining, expiresAt: entry.expiresAt };
}

export function revokeToken(token: string) {
  tokenStore.delete(token);
}

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10);
}

export async function comparePassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}
