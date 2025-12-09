import { db } from '../config/database';
import {
  ArtifactMetadata,
  ArtifactQuery,
  ArtifactEntity,
  PaginationParams,
} from '../types/artifacts.types';
import { config } from '../config/config';
import { logger } from '../utils/logger';
import {
  BadRequestError,
  NotFoundError,
  PayloadTooLargeError,
  handleDatabaseError,
} from '../middleware/error.middleware';

/**
 * Artifacts Service
 * Handles all database operations for artifact search and enumeration
 */
export class ArtifactsService {
  /**
   * Enumerate artifacts based on queries with pagination
   * Supports multiple queries in single request (UNION)
   * 
   * @param queries - Array of artifact queries
   * @param pagination - Pagination parameters
   * @returns Array of artifact metadata
   */
  async enumerateArtifacts(
    queries: ArtifactQuery[],
    pagination: PaginationParams
  ): Promise<ArtifactMetadata[]> {
    try {
      // Validate input
      if (!queries || queries.length === 0) {
        throw new BadRequestError('At least one query is required');
      }

      // Build SQL for each query
      const queryParts: string[] = [];
      const params: any[] = [];
      let paramIndex = 1;

      for (const query of queries) {
        if (!query.name) {
          throw new BadRequestError('Query name is required');
        }

        // Build WHERE clause for this query
        const conditions: string[] = [];

        // Handle name filter
        if (query.name === '*') {
          // Wildcard: match all artifacts
          // No name condition needed
        } else {
          // Exact name match
          conditions.push(`name = $${paramIndex}`);
          params.push(query.name);
          paramIndex++;
        }

        // Handle type filter
        if (query.types && query.types.length > 0) {
          conditions.push(`type = ANY($${paramIndex}::text[])`);
          params.push(query.types);
          paramIndex++;
        }

        // Build SELECT for this query
        const whereClause =
          conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

        queryParts.push(`
          SELECT DISTINCT id, name, type, uri, size, rating, cost, dependencies, metadata
          FROM artifacts
          ${whereClause}
        `);
      }

      // Combine queries with UNION if multiple
      let sql = queryParts.join(' UNION ');

      // Add ordering and pagination
      sql += `
        ORDER BY name, id
        LIMIT $${paramIndex}
        OFFSET $${paramIndex + 1}
      `;

      params.push(pagination.limit + 1); // Fetch one extra to detect more pages
      params.push(pagination.offset);

      logger.debug('Enumerate artifacts query', {
        queriesCount: queries.length,
        offset: pagination.offset,
        limit: pagination.limit,
      });

      // Execute query with timeout
      const result = await this.executeWithTimeout<ArtifactEntity>(sql, params);

      // Convert to metadata format
      return result.rows.map(this.entityToMetadata);
    } catch (error) {
      if (error instanceof BadRequestError) {
        throw error;
      }
      logger.error('Error enumerating artifacts:', error);
      handleDatabaseError(error);
    }
  }

  /**
   * Search artifacts by regular expression
   * Searches both name and README content
   * 
   * @param pattern - Regex pattern (already validated)
   * @returns Array of matching artifact metadata
   */
  async searchByRegex(pattern: string): Promise<ArtifactMetadata[]> {
    try {
      // SQL query with PostgreSQL regex operator
      // Search in both name and readme fields
      const sql = `
        SELECT DISTINCT id, name, type, uri, size, rating, cost, dependencies, metadata
        FROM artifacts
        WHERE 
          name ~* $1
          OR 
          readme ~* $1
        ORDER BY 
          name,
          id
        LIMIT $2
      `;

      const params = [pattern, config.regex.maxResults];

      logger.debug('Regex search query', {
        pattern: pattern.substring(0, 50),
        maxResults: config.regex.maxResults,
      });

      // Execute with timeout
      const result = await this.executeWithTimeout<ArtifactEntity>(
        sql,
        params,
        config.regex.timeoutMs
      );

      if (result.rowCount === 0) {
        throw new NotFoundError('No artifacts found matching the regex pattern');
      }

      return result.rows.map(this.entityToMetadata);
    } catch (error) {
      if (error instanceof NotFoundError) {
        throw error;
      }
      logger.error('Error in regex search:', error);
      handleDatabaseError(error);
    }
  }

  /**
   * Search artifacts by exact name
   * Returns all artifacts with matching name
   * 
   * @param name - Exact artifact name
   * @returns Array of matching artifact metadata
   */
  async searchByName(name: string): Promise<ArtifactMetadata[]> {
    try {
      const sql = `
        SELECT id, name, type, uri, size, rating, cost, dependencies, metadata
        FROM artifacts
        WHERE name = $1
        ORDER BY created_at DESC, id
      `;

      const params = [name];

      logger.debug('Name search query', { name });

      const result = await this.executeWithTimeout<ArtifactEntity>(sql, params);

      if (result.rowCount === 0) {
        throw new NotFoundError(`No artifacts found with name: ${name}`);
      }

      return result.rows.map(this.entityToMetadata);
    } catch (error) {
      if (error instanceof NotFoundError) {
        throw error;
      }
      logger.error('Error in name search:', error);
      handleDatabaseError(error);
    }
  }

  /**
   * Get total artifact count (with safety limit)
   * Used for DoS prevention in enumerate endpoint
   * 
   * @returns Total count or max+1 if exceeds limit
   */
  async getTotalCount(): Promise<number> {
    try {
      const sql = `SELECT count_artifacts_safe($1) as total`;
      const params = [config.pagination.maxTotalResults];

      const result = await db.query<{ total: number }>(sql, params);

      return result.rows[0].total;
    } catch (error) {
      logger.error('Error getting total count:', error);
      handleDatabaseError(error);
    }
  }

  /**
   * Estimate result count for a query (without executing full query)
   * Used for DoS prevention checks
   * 
   * @param queries - Artifact queries
   * @returns Estimated count
   */
  async estimateResultCount(queries: ArtifactQuery[]): Promise<number> {
    try {
      // Simple estimation: if any query has wildcard, return total count
      const hasWildcard = queries.some((q) => q.name === '*');

      if (hasWildcard) {
        return await this.getTotalCount();
      }

      // For specific queries, estimate based on name matches
      // This is a rough estimate - actual implementation could be more sophisticated
      let estimatedTotal = 0;

      for (const query of queries) {
        const sql = `
          SELECT COUNT(*) as count
          FROM artifacts
          WHERE name = $1
          ${query.types && query.types.length > 0 ? 'AND type = ANY($2::text[])' : ''}
        `;

        const params: any[] = [query.name];
        if (query.types && query.types.length > 0) {
          params.push(query.types);
        }

        const result = await db.query<{ count: string }>(sql, params);
        estimatedTotal += parseInt(result.rows[0].count, 10);
      }

      return estimatedTotal;
    } catch (error) {
      logger.error('Error estimating result count:', error);
      // If estimation fails, be conservative and assume high count
      return config.pagination.maxTotalResults + 1;
    }
  }

  /**
   * Execute query with timeout protection
   * 
   * @param sql - SQL query
   * @param params - Query parameters
   * @param timeoutMs - Timeout in milliseconds
   * @returns Query result
   */
  private async executeWithTimeout<T>(
    sql: string,
    params: any[],
    timeoutMs: number = 5000
  ) {
    const client = await db.getClient();

    try {
      // Set statement timeout for this query
      await client.query(`SET statement_timeout = ${timeoutMs}`);

      // Execute main query
      const result = await client.query<T>(sql, params);

      return result;
    } catch (error: any) {
      if (error.code === '57014') {
        // Query timeout
        throw new PayloadTooLargeError(
          'Query timeout: request is too complex or returns too many results'
        );
      }
      throw error;
    } finally {
      // Reset timeout and release client
      await client.query('RESET statement_timeout');
      client.release();
    }
  }

  /**
   * Convert database entity to API metadata format
   * 
   * @param entity - Database artifact entity
   * @returns Artifact metadata
   */
  private entityToMetadata(entity: ArtifactEntity): ArtifactMetadata {
    return {
      id: entity.id,
      name: entity.name,
      type: entity.type,
      uri: entity.uri,
      size: entity.size,
      metadata: entity.metadata,
      rating: entity.rating,
      cost: entity.cost,
      dependencies: entity.dependencies,
    };
  }

  /**
   * Check if database is healthy
   * Used for health checks
   * 
   * @returns True if database is accessible
   */
  async healthCheck(): Promise<boolean> {
    try {
      const result = await db.query('SELECT 1');
      return result.rowCount === 1;
    } catch (error) {
      logger.error('Database health check failed:', error);
      return false;
    }
  }
}

// Export singleton instance
export const artifactsService = new ArtifactsService();

