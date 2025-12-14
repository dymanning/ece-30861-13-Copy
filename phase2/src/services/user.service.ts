import { Pool } from 'pg';
import bcrypt from 'bcryptjs';
import { User, Permission } from '../types/user.types';
import { logger } from '../utils/logger';

export class UserService {
  private pool: Pool;

  constructor(pool: Pool) {
    this.pool = pool;
  }

  /**
   * Create a new user
   * Only admins can register users per spec
   */
  async createUser(
    username: string,
    password: string,
    isAdmin: boolean,
    permissions: Permission[]
  ): Promise<User> {
    // Hash password securely using bcrypt
    const passwordHash = await bcrypt.hash(password, 12); // 12 rounds for security

    const query = `
      INSERT INTO users (username, password_hash, is_admin, permissions, created_at)
      VALUES ($1, $2, $3, $4, NOW())
      RETURNING username, password_hash as "passwordHash", is_admin as "isAdmin", 
                permissions, created_at as "createdAt"
    `;

    const result = await this.pool.query(query, [
      username,
      passwordHash,
      isAdmin,
      permissions,
    ]);

    logger.info(`User created: ${username}`);
    return result.rows[0];
  }

  /**
   * Find user by username
   */
  async findByUsername(username: string): Promise<User | null> {
    const query = `
      SELECT username, password_hash as "passwordHash", is_admin as "isAdmin",
             permissions, created_at as "createdAt"
      FROM users
      WHERE username = $1
    `;

    const result = await this.pool.query(query, [username]);
    return result.rows[0] || null;
  }

  /**
   * Verify user password
   */
  async verifyPassword(username: string, password: string): Promise<boolean> {
    const user = await this.findByUsername(username);
    if (!user) {
      return false;
    }

    return bcrypt.compare(password, user.passwordHash);
  }

  /**
   * Delete a user
   * Users can delete themselves, admins can delete anyone
   */
  async deleteUser(username: string): Promise<boolean> {
    const query = `DELETE FROM users WHERE username = $1`;
    const result = await this.pool.query(query, [username]);
    
    if (result.rowCount && result.rowCount > 0) {
      logger.info(`User deleted: ${username}`);
      return true;
    }
    
    return false;
  }

  /**
   * Check if user has specific permission
   */
  async hasPermission(username: string, permission: Permission): Promise<boolean> {
    const user = await this.findByUsername(username);
    if (!user) {
      return false;
    }

    // Admin permission grants all permissions
    if (user.permissions.includes('admin')) {
      return true;
    }

    return user.permissions.includes(permission);
  }

  /**
   * Get all users (admin only)
   */
  async getAllUsers(): Promise<Omit<User, 'passwordHash'>[]> {
    const query = `
      SELECT username, is_admin as "isAdmin", permissions, created_at as "createdAt"
      FROM users
      ORDER BY created_at DESC
    `;

    const result = await this.pool.query(query);
    return result.rows;
  }

  /**
   * Check if username exists
   */
  async userExists(username: string): Promise<boolean> {
    const query = `SELECT 1 FROM users WHERE username = $1`;
    const result = await this.pool.query(query, [username]);
    return result.rows.length > 0;
  }

  /**
   * Initialize default admin user if not exists
   */
  async ensureDefaultAdmin(): Promise<void> {
    const defaultUsername = 'ece30861defaultadminuser';
    const defaultPassword = 'correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages';

    const exists = await this.userExists(defaultUsername);
    if (!exists) {
      await this.createUser(
        defaultUsername,
        defaultPassword,
        true,
        ['admin', 'upload', 'search', 'download']
      );
      logger.info('Default admin user created');
    }
  }
}
