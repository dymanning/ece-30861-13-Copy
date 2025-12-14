import express, { Application, Request, Response } from 'express';
import cors from 'cors';
import helmet from 'helmet';
import artifactsRoutes from './routes/artifacts.routes';
import { globalRateLimiter, enforceUploadSize } from './middleware/rate.middleware';
import {
  errorHandler,
  notFoundHandler,
} from './middleware/error.middleware';
import { logger, logRequest } from './utils/logger';

/**
 * Create and configure Express application
 */
export function createApp(): Application {
  const app = express();

  // ============================================
  // Security Middleware
  // ============================================

  // Helmet: Sets various HTTP headers for security
  app.use(
    helmet({
      contentSecurityPolicy: false, // Disable CSP for API
      crossOriginEmbedderPolicy: false,
    })
  );

  // ============================================
  // DoS Mitigations (Rate Limit & Size Guard)
  // ============================================

  // Global per-IP rate limiter
  app.use(globalRateLimiter);

  // Upload payload size guard (uses Content-Length)
  app.use(enforceUploadSize);

  // CORS: Enable Cross-Origin Resource Sharing
  app.use(
    cors({
      origin: '*', // For development; restrict in production
      methods: ['GET', 'POST', 'PUT', 'DELETE'],
      allowedHeaders: ['Content-Type', 'X-Authorization'],
      exposedHeaders: ['offset'], // Expose pagination header
    })
  );

  // ============================================
  // Body Parsing Middleware
  // ============================================

  // Parse JSON bodies (limit: 10MB for large artifact metadata)
  app.use(express.json({ limit: '10mb' }));

  // Parse URL-encoded bodies
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));

  // ============================================
  // Request Logging Middleware
  // ============================================

  app.use((req: Request, res: Response, next) => {
    const startTime = Date.now();

    // Log when response finishes
    res.on('finish', () => {
      const duration = Date.now() - startTime;
      logRequest(req.method, req.url, res.statusCode, duration);
    });

    next();
  });

  // ============================================
  // Health Check (Root)
  // ============================================

  app.get('/', (req: Request, res: Response) => {
    res.status(200).json({
      service: 'ECE 461 Trustworthy Artifact Registry',
      version: '1.0.0',
      status: 'running',
      endpoints: {
        health: '/health',
        enumerate: 'POST /artifacts',
        searchRegex: 'POST /artifact/byRegEx',
        searchByName: 'GET /artifact/byName/:name',
      },
    });
  });

  // ============================================
  // API Routes
  // ============================================

  // Mount artifact routes
  app.use('/', artifactsRoutes);

  // ============================================
  // Error Handling
  // ============================================

  // 404 handler (must be after all routes)
  app.use(notFoundHandler);

  // Global error handler (must be last)
  app.use(errorHandler);

  logger.info('Express application configured successfully');

  return app;
}
