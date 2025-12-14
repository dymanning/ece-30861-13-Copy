import { Request, Response } from 'express';
import { artifactsService } from '../services/artifacts.service';
import { ArtifactQuery } from '../types/artifacts.types';
import {
  getPaginationParams,
  processPaginatedResults,
  getSqlLimit,
  isDeepPagination,
} from '../utils/pagination.utils';
import { prepareRegexForQuery } from '../utils/regex.utils';
import { logger } from '../utils/logger';
import {
  BadRequestError,
  PayloadTooLargeError,
  handleRegexError,
} from '../middleware/error.middleware';
import { config } from '../config/config';

/**
 * Artifacts Controller
 * Handles HTTP requests for artifact enumeration and search
 */
export class ArtifactsController {
  /**
   * POST /artifacts
   * Enumerate artifacts with pagination
   */
  async enumerateArtifacts(req: Request, res: Response): Promise<void> {
    const startTime = Date.now();

    try {
      // Parse request body
      const queries: ArtifactQuery[] = req.body;

      // Validate queries array
      if (!Array.isArray(queries) || queries.length === 0) {
        throw new BadRequestError(
          'Request body must be a non-empty array of ArtifactQuery objects'
        );
      }

      // Validate each query
      for (const query of queries) {
        if (!query.name) {
          throw new BadRequestError('Each query must have a name field');
        }

        if (query.types) {
          if (!Array.isArray(query.types)) {
            throw new BadRequestError('types field must be an array');
          }

          const validTypes = ['model', 'dataset', 'code'];
          for (const type of query.types) {
            if (!validTypes.includes(type)) {
              throw new BadRequestError(
                `Invalid type: ${type}. Must be one of: ${validTypes.join(', ')}`
              );
            }
          }
        }
      }

      // Parse pagination parameters
      const offsetStr = req.query.offset as string | undefined;
      const pagination = getPaginationParams(offsetStr);

      // Check for deep pagination
      if (isDeepPagination(pagination.offset)) {
        throw new PayloadTooLargeError(
          'Offset too large. Please refine your query or use earlier pages.'
        );
      }

      // DoS prevention: Estimate result count
      const estimatedCount = await artifactsService.estimateResultCount(queries);
      if (estimatedCount > config.pagination.maxTotalResults) {
        throw new PayloadTooLargeError(
          `Query would return too many results (estimated: ${estimatedCount}, ` +
            `max: ${config.pagination.maxTotalResults}). ` +
            'Please refine your query with more specific filters.'
        );
      }

      // Fetch artifacts with pagination
      const sqlLimit = getSqlLimit(pagination.limit);
      const results = await artifactsService.enumerateArtifacts(queries, {
        offset: pagination.offset,
        limit: sqlLimit,
      });

      // Process pagination
      const paginatedResults = processPaginatedResults(
        results,
        pagination.offset,
        pagination.limit
      );

      // Set pagination header (must be string)
      if (paginatedResults.nextOffset !== null) {
        res.set('offset', String(paginatedResults.nextOffset));
      }

      // Log performance
      const duration = Date.now() - startTime;
      logger.info('Enumerate artifacts completed', {
        queriesCount: queries.length,
        offset: pagination.offset,
        returned: paginatedResults.items.length,
        hasMore: paginatedResults.hasMore,
        duration: `${duration}ms`,
      });

      // Send response
      res.status(200).json(paginatedResults.items);
    } catch (error) {
      logger.error('Error in enumerateArtifacts controller:', error);
      throw error; // Will be caught by error middleware
    }
  }

  /**
   * POST /artifact/byRegEx
   * Search artifacts by regular expression
   */
  async searchByRegex(req: Request, res: Response): Promise<void> {
    const startTime = Date.now();

    try {
      // Parse request body
      const { regex } = req.body;

      // Validate regex field
      if (!regex) {
        throw new BadRequestError('regex field is required');
      }

      if (typeof regex !== 'string') {
        throw new BadRequestError('regex must be a string');
      }

      // Validate and prepare regex pattern
      let validatedPattern: string;
      try {
        validatedPattern = prepareRegexForQuery(regex);
      } catch (error) {
        handleRegexError(error as Error);
      }

      // Execute regex search
      const results = await artifactsService.searchByRegex(validatedPattern);

      // Log performance
      const duration = Date.now() - startTime;
      logger.info('Regex search completed', {
        pattern: regex.substring(0, 50),
        resultsCount: results.length,
        duration: `${duration}ms`,
      });

      // Send response
      res.status(200).json(results);
    } catch (error) {
      logger.error('Error in searchByRegex controller:', error);
      throw error;
    }
  }

  /**
   * GET /artifact/byName/:name
   * Search artifacts by exact name
   */
  async searchByName(req: Request, res: Response): Promise<void> {
    const startTime = Date.now();

    try {
      // Parse path parameter
      const { name } = req.params;

      // Validate name
      if (!name || name.trim().length === 0) {
        throw new BadRequestError('name parameter is required');
      }

      // Decode URI component (handles special characters)
      const decodedName = decodeURIComponent(name);

      // Execute name search
      const results = await artifactsService.searchByName(decodedName);

      // Log performance
      const duration = Date.now() - startTime;
      logger.info('Name search completed', {
        name: decodedName,
        resultsCount: results.length,
        duration: `${duration}ms`,
      });

      // Send response
      res.status(200).json(results);
    } catch (error) {
      logger.error('Error in searchByName controller:', error);
      throw error;
    }
  }

  /**
   * GET /artifacts/:type/:id
   * Retrieve artifact by ID and type
   */
  async getArtifact(req: Request, res: Response): Promise<void> {
    const startTime = Date.now();

    try {
      // Parse path parameters
      const { type, id } = req.params;

      // Validate parameters
      if (!type || !id) {
        throw new BadRequestError('type and id parameters are required');
      }

      // Execute artifact retrieval
      const artifact = await artifactsService.getArtifact(type, id);

      // Log performance
      const duration = Date.now() - startTime;
      logger.info('Artifact retrieved', {
        type,
        id,
        duration: `${duration}ms`,
      });

      // Send response
      res.status(200).json(artifact);
    } catch (error) {
      logger.error('Error in getArtifact controller:', error);
      throw error;
    }
  }

  /**
   * DELETE /artifacts/:type/:id
   * Delete artifact by ID and type
   */
  async deleteArtifact(req: Request, res: Response): Promise<void> {
    const startTime = Date.now();

    try {
      // Parse path parameters
      const { type, id } = req.params;

      // Validate parameters
      if (!type || !id) {
        throw new BadRequestError('type and id parameters are required');
      }

      // Execute artifact deletion
      await artifactsService.deleteArtifact(type, id);

      // Log performance
      const duration = Date.now() - startTime;
      logger.info('Artifact deleted', {
        type,
        id,
        duration: `${duration}ms`,
      });

      // Send response (successful deletion)
      res.status(200).json({ message: 'Artifact deleted successfully' });
    } catch (error) {
      logger.error('Error in deleteArtifact controller:', error);
      throw error;
    }
  }

  /**
   * GET /artifact/model/:id/lineage
   * Get lineage graph for a model
   */
  async getLineage(req: Request, res: Response): Promise<void> {
    const startTime = Date.now();

    try {
      // Parse path parameter
      const { id } = req.params;

      // Validate parameter
      if (!id) {
        throw new BadRequestError('id parameter is required');
      }

      // Execute lineage retrieval
      const lineage = await artifactsService.getLineage(id);

      // Log performance
      const duration = Date.now() - startTime;
      logger.info('Lineage retrieved', {
        id,
        duration: `${duration}ms`,
      });

      // Send response
      res.status(200).json(lineage);
    } catch (error) {
      logger.error('Error in getLineage controller:', error);
      throw error;
    }
  }

  /**
   * GET /health
   * Health check endpoint
   */
  async healthCheck(req: Request, res: Response): Promise<void> {
    try {
      const dbHealthy = await artifactsService.healthCheck();

      if (dbHealthy) {
        res.status(200).json({
          status: 'healthy',
          database: 'connected',
          timestamp: new Date().toISOString(),
        });
      } else {
        res.status(503).json({
          status: 'unhealthy',
          database: 'disconnected',
          timestamp: new Date().toISOString(),
        });
      }
    } catch (error) {
      logger.error('Health check failed:', error);
      res.status(503).json({
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      });
    }
  }
}

// Export singleton instance
export const artifactsController = new ArtifactsController();
