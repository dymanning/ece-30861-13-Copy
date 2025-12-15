import { Pool } from 'pg';
import crypto from 'crypto';
import { AuthToken, User, Permission } from '../types/user.types';
import { logger } from '../utils/logger';

export class AuthService {
  private pool: Pool;

  constructor(pool: Pool) {
    this.pool = pool;
  }

  /**
   * Generate a secure random token
   */
  private generateSecureToken(): string {
    return crypto.randomBytes(32).toString('base64url');
  }

  /**
   * Create a new authentication token
   * Token valid for 1000 API interactions or 10 hours (whichever comes first)
   */
  async createToken(username: string): Promise<string> {
    const token = this.generateSecureToken();
    const expiresAt = new Date(Date.now() + 10 * 60 * 60 * 1000); // 10 hours

    const query = `
      INSERT INTO auth_tokens (token, username, usage_count, max_usage, expires_at, created_at)
      VALUES ($1, $2, 0, 1000, $3, NOW())
      RETURNING token
    `;

    const result = await this.pool.query(query, [token, username, expiresAt]);
    logger.info(`Token created for user: ${username}`);
    
    return result.rows[0].token;
  }

  /**
   * Validate token and check if it's still valid
   * Returns the username if valid, null otherwise
   */
  async validateToken(token: string): Promise<string | null> {
    const query = `
      SELECT username, usage_count, max_usage, expires_at
      FROM auth_tokens
      WHERE token = $1
    `;

    const result = await this.pool.query(query, [token]);
    
    if (result.rows.length === 0) {
      return null;
    }

    const tokenData = result.rows[0];
    const now = new Date();

    // Check if token has expired (time-based)
    if (new Date(tokenData.expires_at) < now) {
      await this.deleteToken(token);
      logger.warn(`Token expired (time): ${token.substring(0, 8)}...`);
      return null;
    }

    // Check if token has exceeded usage limit
    if (tokenData.usage_count >= tokenData.max_usage) {
      await this.deleteToken(token);
      logger.warn(`Token expired (usage): ${token.substring(0, 8)}...`);
      return null;
    }

    return tokenData.username;
  }

  /**
   * Increment token usage count
   * Called on each API request
   */
  async incrementTokenUsage(token: string): Promise<void> {
    const query = `
      UPDATE auth_tokens
      SET usage_count = usage_count + 1
      WHERE token = $1
    `;

    await this.pool.query(query, [token]);
  }

  /**
   * Delete a token (logout)
   */
  async deleteToken(token: string): Promise<void> {
    const query = `DELETE FROM auth_tokens WHERE token = $1`;
    await this.pool.query(query, [token]);
  }

  /**
   * Delete all tokens for a user
   */
  async deleteAllUserTokens(username: string): Promise<void> {
    const query = `DELETE FROM auth_tokens WHERE username = $1`;
    const result = await this.pool.query(query, [username]);
    logger.info(`Deleted ${result.rowCount} tokens for user: ${username}`);
  }

  /**
   * Get all active tokens for a user
   */
  async getUserTokens(username: string): Promise<AuthToken[]> {
    const query = `
      SELECT token, username, usage_count as "usageCount", 
             max_usage as "maxUsage", expires_at as "expiresAt",
             created_at as "createdAt"
      FROM auth_tokens
      WHERE username = $1 AND expires_at > NOW()
      ORDER BY created_at DESC
    `;

    const result = await this.pool.query(query, [username]);
    return result.rows;
  }

  /**
   * Clean up expired tokens (maintenance task)
   */
  async cleanupExpiredTokens(): Promise<number> {
    const query = `
      DELETE FROM auth_tokens
      WHERE expires_at < NOW() OR usage_count >= max_usage
    `;

    const result = await this.pool.query(query);
    const deletedCount = result.rowCount || 0;
    
    if (deletedCount > 0) {
      logger.info(`Cleaned up ${deletedCount} expired tokens`);
    }
    
    return deletedCount;
  }

  /**
   * Get token info (for debugging/admin purposes)
   */
  async getTokenInfo(token: string): Promise<AuthToken | null> {
    const query = `
      SELECT token, username, usage_count as "usageCount",
             max_usage as "maxUsage", expires_at as "expiresAt",
             created_at as "createdAt"
      FROM auth_tokens
      WHERE token = $1
    `;

    const result = await this.pool.query(query, [token]);
    return result.rows[0] || null;
  }
}
