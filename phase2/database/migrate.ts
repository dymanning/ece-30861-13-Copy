// Load environment variables FIRST (before any other imports)
import dotenv from 'dotenv';
dotenv.config();

import * as fs from 'fs';
import * as path from 'path';
import { db } from '../src/config/database';
import { logger } from '../src/utils/logger';

/**
 * Run database migrations
 * Executes the schema.sql file to set up the database
 */
async function runMigrations() {
  try {
    logger.info('Starting database migrations...');

    // Read schema file
    const schemaPath = path.join(__dirname, 'schema.sql');
    const schemaSql = fs.readFileSync(schemaPath, 'utf-8');

    // Test connection first
    const connected = await db.testConnection();
    if (!connected) {
      throw new Error('Database connection failed');
    }

    // Execute schema
    logger.info('Executing schema.sql...');
    await db.query(schemaSql);

    logger.info('Database migrations completed successfully');

    // Verify tables were created
    const verifyQuery = `
      SELECT table_name 
      FROM information_schema.tables 
      WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
      ORDER BY table_name;
    `;

    const result = await db.query(verifyQuery);
    logger.info('Created tables:', {
      tables: result.rows.map((r: any) => r.table_name),
    });

    // Close database connection
    await db.close();
    process.exit(0);
  } catch (error) {
    logger.error('Migration failed:', error);
    await db.close();
    process.exit(1);
  }
}

// Run migrations
runMigrations();