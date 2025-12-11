import dotenv from 'dotenv';
import { AppConfig } from '../types/artifacts.types';

// Load environment variables
dotenv.config();

/**
 * Application configuration loaded from environment variables
 * with sensible defaults
 */
export const config: AppConfig = {
  port: parseInt(process.env.PORT || '3000', 10),
  nodeEnv: process.env.NODE_ENV || 'development',

  database: {
    connectionString: process.env.DATABASE_URL,
    host: process.env.DATABASE_HOST || process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DATABASE_PORT || process.env.DB_PORT || '5432', 10),
    database: process.env.DATABASE_NAME || process.env.DB_NAME || 'artifact_registry',
    user: process.env.DATABASE_USER || process.env.DB_USER || 'postgres',
    password: process.env.DATABASE_PASSWORD || process.env.DB_PASSWORD || '',
    ssl: process.env.DATABASE_SSL === 'true',
    max: 20, // Maximum pool size
    idleTimeoutMillis: 30000, // Close idle clients after 30s
    connectionTimeoutMillis: 5000, // Timeout connection attempts after 5s
  },

  pagination: {
    defaultPageSize: parseInt(process.env.DEFAULT_PAGE_SIZE || '100', 10),
    maxPageSize: parseInt(process.env.MAX_PAGE_SIZE || '100', 10),
    maxTotalResults: parseInt(process.env.MAX_TOTAL_RESULTS || '10000', 10),
  },

  regex: {
    maxPatternLength: parseInt(process.env.MAX_REGEX_LENGTH || '200', 10),
    timeoutMs: parseInt(process.env.REGEX_TIMEOUT_MS || '5000', 10),
    maxResults: parseInt(process.env.MAX_REGEX_RESULTS || '1000', 10),
  },

  logging: {
    level: process.env.LOG_LEVEL || 'info',
    file: process.env.LOG_FILE || './logs/app.log',
  },

  auth: {
    enabled: process.env.AUTH_ENABLED === 'true',
    jwtSecret: process.env.JWT_SECRET || 'change_this_in_production',
  },
  features: {
    enableBedrock: process.env.ENABLE_BEDROCK === 'true',
  },
};

/**
 * Validate required configuration
 */
export function validateConfig(): void {
  const required = [
    'DATABASE_HOST',
    'DATABASE_NAME',
    'DATABASE_USER',
    'DATABASE_PASSWORD',
  ];

  const missing = required.filter((key) => !process.env[key]);

  if (missing.length > 0) {
    console.warn(
      `Warning: Missing environment variables: ${missing.join(', ')}`
    );
    console.warn('Using default values. Set these in .env file for production.');
  }
}

// Validate on import
validateConfig();
