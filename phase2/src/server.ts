import { createApp } from './app';
import { db } from './config/database';
import { config } from './config/config';
import { logger } from './utils/logger';
import { initializeAuthServices } from './middleware/auth.middleware';
import { initializeAuthController } from './controllers/auth.controller';
import { UserService } from './services/user.service';

/**
 * Start the server
 */
async function startServer() {
  try {
    // Test database connection
    logger.info('Testing database connection...');
    const dbConnected = await db.testConnection();

    if (!dbConnected) {
      logger.error('Failed to connect to database');
      process.exit(1);
    }

    logger.info('Database connection successful');

    // Initialize auth services with database pool
    const pool = db.getPool();
    initializeAuthServices(pool);
    initializeAuthController(pool);

    // Ensure default admin user exists
    const userService = new UserService(pool);
    await userService.ensureDefaultAdmin();
    logger.info('Default admin user verified');

    // Create Express app
    const app = createApp();

    // Start listening
    const server = app.listen(config.port, () => {
      logger.info(`Server started successfully`, {
        port: config.port,
        environment: config.nodeEnv,
        endpoints: {
          health: `http://localhost:${config.port}/health`,
          enumerate: `http://localhost:${config.port}/artifacts`,
          searchRegex: `http://localhost:${config.port}/artifact/byRegEx`,
          searchByName: `http://localhost:${config.port}/artifact/byName/:name`,
        },
      });
    });

    // Graceful shutdown handlers
    const gracefulShutdown = async (signal: string) => {
      logger.info(`${signal} received, starting graceful shutdown`);

      // Stop accepting new connections
      server.close(async () => {
        logger.info('HTTP server closed');

        try {
          // Close database connections
          await db.close();
          logger.info('Database connections closed');

          logger.info('Graceful shutdown completed');
          process.exit(0);
        } catch (error) {
          logger.error('Error during graceful shutdown:', error);
          process.exit(1);
        }
      });

      // Force shutdown after 10 seconds
      setTimeout(() => {
        logger.error('Forced shutdown after timeout');
        process.exit(1);
      }, 10000);
    };

    // Handle shutdown signals
    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));

    // Handle uncaught errors
    process.on('uncaughtException', (error) => {
      logger.error('Uncaught exception:', error);
      gracefulShutdown('uncaughtException');
    });

    process.on('unhandledRejection', (reason, promise) => {
      logger.error('Unhandled rejection at:', { promise, reason });
      gracefulShutdown('unhandledRejection');
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Start the server
startServer();
