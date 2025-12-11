import { db } from '../config/database';
import {
  ArtifactMetadata,
  ArtifactQuery,
  ArtifactEntity,
  PaginationParams,
  RatingMetrics,
  SizeScore,
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
 * Model rating shape for GET /artifact/model/{id}/rate
 */
interface ModelRating {
  name: string;
  category: 'model';
  net_score: number;
  net_score_latency: number;
  ramp_up_time: number;
  ramp_up_time_latency: number;
  bus_factor: number;
  bus_factor_latency: number;
  performance_claims: number;
  performance_claims_latency: number;
  license: number;
  license_latency: number;
  dataset_and_code_score: number;
  dataset_and_code_score_latency: number;
  dataset_quality: number;
  dataset_quality_latency: number;
  code_quality: number;
  code_quality_latency: number;
  reproducibility: number;
  reproducibility_latency: number;
  reviewedness: number;
  reviewedness_latency: number;
  tree_score: number;
  tree_score_latency: number;
  size_score: SizeScore;
  size_score_latency: number;
  ratings: RatingMetrics;
}

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
<<<<<<< HEAD
=======
   * Create new artifact (spec: POST /artifact/{artifact_type})
   */
  async createArtifact(artifact_type: string, data: { url: string }): Promise<Artifact> {
    if (!data || !data.url) {
      throw new BadRequestError('artifact_data must include url');
    }
    // Derive name from URL segment
    const urlParts = data.url.split('/').filter(Boolean);
    const derivedName = urlParts[urlParts.length - 1] || 'unknown-artifact';
    const id = this.generateId();
    const type = artifact_type as 'model' | 'dataset' | 'code';
    // Spec-related ingestion validation: compute quality and reject if < 0.5
    // For model type only here; extend as needed
    try {
      const artifactPreview: Artifact = { metadata: { name: derivedName, id, type }, data: { url: data.url } };
      // Lazy import to avoid cycles
      const { computeQualityScore } = await import('../utils/metric.utils');
      const quality = await computeQualityScore(artifactPreview);
      if (quality < 0.5) {
        throw new FailedDependencyError('Artifact is not registered due to the disqualified rating');
      }
    } catch (err) {
      if (err instanceof BadRequestError || err instanceof FailedDependencyError) {
        throw err;
      }
      // If metric evaluation fails, return 202 (deferred) per spec could be implemented in controller
      // For now, propagate error as 500
      handleDatabaseError(err);
    }
    const insertSql = `INSERT INTO artifacts (id, name, type, url, readme, metadata) VALUES ($1,$2,$3,$4,$5,$6)`;
    const params = [id, derivedName, type, data.url, '', JSON.stringify({})];
    try {
      await db.query(insertSql, params);
    } catch (error: any) {
      if (error.code === '23505') { // unique violation
        throw new ConflictError('Artifact exists already');
      }
      handleDatabaseError(error);
    }
    return {
      metadata: { name: derivedName, id, type },
      data: { url: data.url },
    };
  }

  /**
   * Retrieve artifact (GET /artifacts/{artifact_type}/{id})
   */
  async getArtifact(artifact_type: string, id: string): Promise<Artifact> {
    const sql = `SELECT id, name, type, url, readme, metadata FROM artifacts WHERE id = $1 AND type = $2`;
    const result = await db.query<ArtifactEntity>(sql, [id, artifact_type]);
    if (result.rowCount === 0) {
      throw new NotFoundError('Artifact does not exist');
    }
    const row = result.rows[0];
    return {
      metadata: { name: row.name, id: row.id, type: row.type },
      data: { url: row.url },
    };
  }

  /**
   * Update artifact (PUT /artifacts/{artifact_type}/{id})
   */
  async updateArtifact(artifact_type: string, id: string, artifact: Artifact): Promise<void> {
    if (artifact.metadata.id !== id || artifact.metadata.type !== artifact_type) {
      throw new BadRequestError('Name/id/type mismatch');
    }
    const sql = `UPDATE artifacts SET url = $1, updated_at = NOW() WHERE id = $2 AND type = $3`;
    const result = await db.query(sql, [artifact.data.url, id, artifact_type]);
    if (result.rowCount === 0) {
      throw new NotFoundError('Artifact does not exist');
    }
  }

  /**
   * Delete artifact (DELETE /artifacts/{artifact_type}/{id})
   */
  async deleteArtifact(artifact_type: string, id: string): Promise<void> {
    const sql = `DELETE FROM artifacts WHERE id = $1 AND type = $2`;
    const result = await db.query(sql, [id, artifact_type]);
    if (result.rowCount === 0) {
      throw new NotFoundError('Artifact does not exist');
    }
  }

  /**
   * Get model rating (GET /artifact/model/{id}/rate) — stub implementation
   */
  async getModelRating(id: string): Promise<ModelRating> {
    const artifact = await this.getArtifact('model', id); // will throw 404 if missing

    // Wire up every metric that currently has an implementation (even if stubbed):
    // - quality_score, dependency_score, code_review_score: metric.utils (random/stub)
    // - size_score: metric.utils (deterministic from bytes)
    const {
      computeQualityScore,
      computeDependencyScore,
      computeCodeReviewScore,
      computeSizeScoreFromBytes,
    } = await import('../utils/metric.utils');

    // Get size from DB if present; otherwise fall back to 256MB to avoid zero scores.
    const DEFAULT_TOTAL_SIZE_BYTES = 256 * 1024 * 1024;
    const sizeResult = await db.query<{ size: number }>(
      'SELECT size FROM artifacts WHERE id = $1 LIMIT 1',
      [id]
    );
    const totalSizeBytes = sizeResult.rows?.[0]?.size ?? DEFAULT_TOTAL_SIZE_BYTES;

    const [qualityScore, dependencyScore, codeReviewScore] = await Promise.all([
      computeQualityScore(artifact),
      computeDependencyScore(artifact),
      computeCodeReviewScore(artifact),
    ]);

    const sizeScores = computeSizeScoreFromBytes(totalSizeBytes);

    // Build ratings object using all currently available metrics (Phase 1 placeholders + local stubs)
    const ratings: RatingMetrics = {
      quality: qualityScore,
      size_score: sizeScores.size_score,
      code_quality: 0,
      dataset_quality: 0,
      performance_claims: 0,
      bus_factor: dependencyScore,
      ramp_up_time: 0,
      dataset_and_code_score: 0,
    };

    // Optionally enrich with Bedrock insights (blended conservatively)
    let performance_claims = 0;
    let code_quality = 0;
    let dataset_quality = 0;
    let reviewedness = 0;
    if (config.features?.enableBedrock) {
      try {
        const { summarizePerformanceClaims, assessCodeQuality, assessDatasetQuality } = await import('./bedrock.service');
        const [perf, code, data] = await Promise.allSettled([
          summarizePerformanceClaims({ name: artifact.metadata.name }),
          assessCodeQuality({ name: artifact.metadata.name }),
          assessDatasetQuality({ name: artifact.metadata.name }),
        ]);
        const alpha = 0.7; // favor deterministic (currently 0) but prepare for future calibration
        if (perf.status === 'fulfilled' && typeof perf.value.performance_claims === 'number') {
          performance_claims = Math.max(0, Math.min(1, (alpha * performance_claims) + ((1 - alpha) * perf.value.performance_claims)));
        }
        if (code.status === 'fulfilled') {
          if (typeof code.value.code_quality === 'number') {
            code_quality = Math.max(0, Math.min(1, (alpha * code_quality) + ((1 - alpha) * code.value.code_quality)));
          }
          if (typeof code.value.reviewedness === 'number') {
            reviewedness = Math.max(0, Math.min(1, (alpha * reviewedness) + ((1 - alpha) * code.value.reviewedness)));
          }
        }
        if (data.status === 'fulfilled' && typeof data.value.dataset_quality === 'number') {
          dataset_quality = Math.max(0, Math.min(1, (alpha * dataset_quality) + ((1 - alpha) * data.value.dataset_quality)));
        }

        // Update ratings from Bedrock responses when present
        ratings.performance_claims = performance_claims || ratings.performance_claims;
        ratings.code_quality = code_quality || ratings.code_quality;
        ratings.dataset_quality = dataset_quality || ratings.dataset_quality;
        ratings.dataset_and_code_score = dataset_quality || ratings.dataset_and_code_score;
      } catch (e) {
        // soft-fail; keep deterministic values
      }
    }

    // Merge deterministic values into ratings for fields still unset
    ratings.code_quality = ratings.code_quality || code_quality || codeReviewScore;
    ratings.dataset_quality = ratings.dataset_quality || dataset_quality;
    ratings.performance_claims = ratings.performance_claims || performance_claims;
    ratings.dataset_and_code_score = ratings.dataset_and_code_score || ratings.dataset_quality;
      } catch (e) {
        // soft-fail; keep deterministic values
      }
    }
    return {
      name: artifact.metadata.name,
      category: 'model',
      net_score: ratings.quality,
      net_score_latency: 0,
      ramp_up_time: ratings.ramp_up_time,
      ramp_up_time_latency: 0,
      bus_factor: ratings.bus_factor,
      bus_factor_latency: 0,
      performance_claims: ratings.performance_claims,
      performance_claims_latency: 0,
      license: codeReviewScore, // placeholder connection until real license metric is wired
      license_latency: 0,
      dataset_and_code_score: ratings.dataset_and_code_score,
      dataset_and_code_score_latency: 0,
      dataset_quality: ratings.dataset_quality,
      dataset_quality_latency: 0,
      code_quality: ratings.code_quality,
      code_quality_latency: 0,
      reproducibility: dependencyScore,
      reproducibility_latency: 0,
      reviewedness,
      reviewedness_latency: 0,
      tree_score: 0,
      tree_score_latency: 0,
      size_score: ratings.size_score,
      size_score_latency: sizeScores.size_score_latency,
      ratings,
    };
  }

  /**
   * Get artifact cost (GET /artifact/{artifact_type}/{id}/cost) — stub
   */
  async getArtifactCost(artifact_type: string, id: string, includeDependencies: boolean): Promise<ArtifactCost> {
    await this.getArtifact(artifact_type, id); // ensure exists
    // Placeholder: deterministic pseudo cost
    const base = id.split('').reduce((acc, c) => acc + (c.charCodeAt(0) % 10), 0) * 1.5;
    const total = includeDependencies ? base * 3 : base;
    const entry: any = { total_cost: parseFloat(total.toFixed(2)) };
    if (includeDependencies) {
      entry.standalone_cost = parseFloat(base.toFixed(2));
    }
    return { [id]: entry };
  }

  /**
   * Get lineage graph (GET /artifact/model/{id}/lineage) — stub
   */
  async getLineage(id: string): Promise<ArtifactLineageGraph> {
    await this.getArtifact('model', id);
    return {
      nodes: [
        { artifact_id: id, name: 'root-model', source: 'config_json' },
      ],
      edges: [],
    };
  }

  /**
   * License check (POST /artifact/model/{id}/license-check) — stub
   */
  async licenseCheck(id: string, github_url: string): Promise<boolean> {
    await this.getArtifact('model', id);
    // Placeholder: approve if URL contains 'github'
    return /github\.com/.test(github_url);
  }

  private generateId(): string {
    return Array.from({ length: 10 }, () => Math.floor(Math.random() * 10)).join('');
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

