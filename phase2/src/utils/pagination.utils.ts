import { config } from '../config/config';
import { PaginationParams, PaginationResult } from '../types/artifacts.types';

/**
 * Parse offset from query string
 * @param offsetStr - Offset string from request
 * @returns Parsed offset number
 */
export function parseOffset(offsetStr: string | undefined): number {
  if (!offsetStr) {
    return 0;
  }

  const offset = parseInt(offsetStr, 10);

  // Validate offset
  if (isNaN(offset) || offset < 0) {
    throw new Error('Invalid offset: must be a non-negative integer');
  }

  return offset;
}

/**
 * Get pagination parameters with validation
 * @param offsetStr - Offset string from request
 * @param customLimit - Optional custom limit (must not exceed max)
 * @returns Pagination parameters
 */
export function getPaginationParams(
  offsetStr: string | undefined,
  customLimit?: number
): PaginationParams {
  const offset = parseOffset(offsetStr);
  
  let limit = config.pagination.defaultPageSize;
  
  if (customLimit !== undefined) {
    if (customLimit <= 0) {
      throw new Error('Invalid limit: must be positive');
    }
    limit = Math.min(customLimit, config.pagination.maxPageSize);
  }

  return { offset, limit };
}

/**
 * Process query results into paginated response
 * Fetches limit + 1 items to determine if there are more pages
 * 
 * @param results - Array of results (length should be limit + 1)
 * @param offset - Current offset
 * @param limit - Items per page
 * @returns Pagination result with items and next offset
 */
export function processPaginatedResults<T>(
  results: T[],
  offset: number,
  limit: number
): PaginationResult<T> {
  const hasMore = results.length > limit;
  const items = results.slice(0, limit); // Remove the extra item
  const nextOffset = hasMore ? offset + limit : null;

  return {
    items,
    nextOffset: nextOffset !== null ? String(nextOffset) : null,
    hasMore,
  };
}

/**
 * Calculate SQL LIMIT value
 * Adds 1 to detect if more results exist
 * 
 * @param limit - Requested limit
 * @returns SQL LIMIT value (limit + 1)
 */
export function getSqlLimit(limit: number): number {
  return limit + 1;
}

/**
 * Validate total result count for DoS prevention
 * Throws error if total would exceed maximum allowed
 * 
 * @param estimatedTotal - Estimated total results
 * @throws Error if total exceeds maximum
 */
export function validateTotalResults(estimatedTotal: number): void {
  if (estimatedTotal > config.pagination.maxTotalResults) {
    throw new Error(
      `Query would return too many results (>${config.pagination.maxTotalResults}). ` +
      'Please refine your query with more specific filters.'
    );
  }
}

/**
 * Check if offset is beyond reasonable bounds
 * Prevents inefficient deep pagination
 * 
 * @param offset - Current offset
 * @returns True if offset is too large
 */
export function isDeepPagination(offset: number): boolean {
  return offset > config.pagination.maxTotalResults;
}

/**
 * Create pagination metadata for logging/debugging
 * 
 * @param offset - Current offset
 * @param limit - Items per page
 * @param totalFetched - Number of items fetched
 * @param hasMore - Whether more pages exist
 * @returns Pagination metadata object
 */
export function createPaginationMetadata(
  offset: number,
  limit: number,
  totalFetched: number,
  hasMore: boolean
) {
  return {
    offset,
    limit,
    returned: Math.min(totalFetched, limit),
    hasMore,
    nextOffset: hasMore ? offset + limit : null,
  };
}
