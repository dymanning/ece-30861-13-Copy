import safeRegex from 'safe-regex';
import { config } from '../config/config';

/**
 * Validate regex pattern for safety and correctness
 * Prevents ReDoS (Regular Expression Denial of Service) attacks
 * 
 * @param pattern - Regex pattern to validate
 * @throws Error if pattern is invalid or unsafe
 */
export function validateRegexPattern(pattern: string): void {
  // Check if pattern is empty
  if (!pattern || pattern.trim().length === 0) {
    throw new Error('Regex pattern cannot be empty');
  }

  // Check pattern length
  if (pattern.length > config.regex.maxPatternLength) {
    throw new Error(
      `Regex pattern too long (max ${config.regex.maxPatternLength} characters)`
    );
  }

  // Test if pattern is valid regex syntax
  try {
    new RegExp(pattern);
  } catch (error) {
    throw new Error(
      `Invalid regex syntax: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }

  // Check for catastrophic backtracking patterns (ReDoS protection)
  if (!safeRegex(pattern)) {
    throw new Error(
      'Unsafe regex pattern detected. Pattern may cause performance issues (ReDoS).'
    );
  }

  // Additional ReDoS protection for patterns safe-regex might miss
  // Check for quantified alternations: (a|b)+, (a|b)*, (a|b){1,}, etc.
  // This catches patterns like (a|aa)+ which cause exponential backtracking
  // We use a conservative heuristic: any group containing an alternation that is quantified
  if (/\([^)]*\|[^)]*\)(?:[*+]|\{\d+(?:,\d*)?\})/.test(pattern)) {
    throw new Error(
      'Unsafe regex pattern detected. Quantified alternations are not allowed.'
    );
  }
}

/**
 * Sanitize regex pattern for safe PostgreSQL execution
 * Escapes special characters that could cause SQL injection
 * 
 * @param pattern - Raw regex pattern
 * @returns Sanitized pattern safe for parameterized queries
 */
export function sanitizeRegexForPostgres(pattern: string): string {
  // PostgreSQL uses parameterized queries, so we don't need to escape
  // But we validate the pattern first
  validateRegexPattern(pattern);
  return pattern;
}

/**
 * Extract keywords from regex pattern for full-text search optimization
 * Converts simple regex patterns to keywords for faster initial filtering
 * 
 * @param pattern - Regex pattern
 * @returns Array of keywords or null if extraction not applicable
 */
export function extractKeywordsFromRegex(pattern: string): string[] | null {
  // Remove regex special characters for keyword extraction
  const cleaned = pattern
    .replace(/[.*+?^${}()|[\]\\]/g, ' ')
    .toLowerCase()
    .trim();

  if (!cleaned) {
    return null;
  }

  // Split into words and filter out short ones
  const keywords = cleaned
    .split(/\s+/)
    .filter((word) => word.length >= 3) // Minimum 3 chars
    .slice(0, 5); // Max 5 keywords

  return keywords.length > 0 ? keywords : null;
}

/**
 * Check if regex pattern is simple enough for optimization
 * Simple patterns can use indexes more effectively
 * 
 * @param pattern - Regex pattern
 * @returns True if pattern is simple (e.g., contains only alphanumeric and *)
 */
export function isSimpleRegexPattern(pattern: string): boolean {
  // Simple pattern: alphanumeric, spaces, and basic wildcards
  const simplePattern = /^[a-zA-Z0-9\s*._-]+$/;
  return simplePattern.test(pattern);
}

/**
 * Convert simple regex to PostgreSQL ILIKE pattern for better performance
 * Only applicable for very simple patterns
 * 
 * @param pattern - Regex pattern
 * @returns PostgreSQL ILIKE pattern or null if not applicable
 */
export function convertToIlikePattern(pattern: string): string | null {
  // Only convert if pattern uses simple wildcards
  if (!/^[a-zA-Z0-9\s*._-]+$/.test(pattern)) {
    return null;
  }

  // Convert regex wildcards to SQL wildcards
  // .* -> %
  // . -> _
  let ilikePattern = pattern
    .replace(/\.\*/g, '%')
    .replace(/\./g, '_')
    .replace(/\*/g, '%');

  return ilikePattern;
}

/**
 * Estimate complexity of regex pattern
 * Returns a score from 0-10 (10 being most complex)
 * 
 * @param pattern - Regex pattern
 * @returns Complexity score
 */
export function estimateRegexComplexity(pattern: string): number {
  let complexity = 0;

  // Count special characters
  const specialChars = pattern.match(/[.*+?^${}()|[\]\\]/g);
  if (specialChars) {
    complexity += specialChars.length;
  }

  // Penalize nested groups
  const nestedGroups = pattern.match(/\([^)]*\([^)]*\)/g);
  if (nestedGroups) {
    complexity += nestedGroups.length * 2;
  }

  // Penalize quantifiers
  const quantifiers = pattern.match(/[*+?{]/g);
  if (quantifiers) {
    complexity += quantifiers.length;
  }

  return Math.min(complexity, 10);
}

/**
 * Create PostgreSQL regex operator based on case sensitivity
 * 
 * @param caseSensitive - Whether to use case-sensitive matching
 * @returns PostgreSQL regex operator (~* or ~)
 */
export function getPostgresRegexOperator(caseSensitive: boolean = false): string {
  return caseSensitive ? '~' : '~*';
}

/**
 * Validate and prepare regex for PostgreSQL execution
 * Main function to call before executing regex query
 * 
 * @param pattern - Raw regex pattern from user
 * @returns Validated and sanitized pattern
 * @throws Error if pattern is invalid or unsafe
 */
export function prepareRegexForQuery(pattern: string): string {
  // Validate first
  validateRegexPattern(pattern);

  // Log complexity for monitoring
  const complexity = estimateRegexComplexity(pattern);
  if (complexity > 7) {
    // High complexity - might want to log this
    console.warn(`High complexity regex pattern detected: ${complexity}/10`);
  }

  return pattern;
}
