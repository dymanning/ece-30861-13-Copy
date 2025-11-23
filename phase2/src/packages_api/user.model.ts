import { User, UserRole } from '../types/user.types';

// Example User table definition (for ORM or raw SQL)
export interface UserEntity extends User {
  // Add DB-specific fields if needed
}

// Example: User table creation SQL
export const userTableSQL = `
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(10) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
`;
