import { Router } from 'express';
import { artifactsController } from '../controllers/artifacts.controller';
import { authenticate } from '../middleware/auth.middleware';
import { asyncHandler } from '../middleware/error.middleware';

/**
 * Artifacts routes
 * Defines all artifact search and enumeration endpoints
 */
const router = Router();

/**
 * POST /artifacts
 * Enumerate artifacts with pagination
 * 
 * BASELINE requirement
 * 
 * Request:
 * - Header: X-Authorization (required)
 * - Query: ?offset=<number> (optional)
 * - Body: ArtifactQuery[] (array of queries)
 * 
 * Response:
 * - 200: ArtifactMetadata[] + offset header
 * - 400: Invalid request
 * - 403: Authentication failed
 * - 413: Too many results (DoS prevention)
 */
router.post(
  '/artifacts',
  authenticate,
  asyncHandler(async (req, res) => {
    await artifactsController.enumerateArtifacts(req, res);
  })
);

/**
 * POST /artifact/byRegEx
 * Search artifacts using regular expression
 * 
 * BASELINE requirement
 * 
 * Searches both artifact names and README content
 * 
 * Request:
 * - Header: X-Authorization (required)
 * - Body: { regex: string }
 * 
 * Response:
 * - 200: ArtifactMetadata[]
 * - 400: Invalid regex
 * - 403: Authentication failed
 * - 404: No matches found
 */
router.post(
  '/artifact/byRegEx',
  authenticate,
  asyncHandler(async (req, res) => {
    await artifactsController.searchByRegex(req, res);
  })
);

/**
 * GET /artifact/byName/:name
 * Search artifacts by exact name
 * 
 * NON-BASELINE requirement (stretch goal)
 * 
 * Request:
 * - Header: X-Authorization (required)
 * - Path: name (artifact name)
 * 
 * Response:
 * - 200: ArtifactMetadata[] (all artifacts with matching name)
 * - 400: Invalid name
 * - 403: Authentication failed
 * - 404: No matches found
 */
router.get(
  '/artifact/byName/:name',
  authenticate,
  asyncHandler(async (req, res) => {
    await artifactsController.searchByName(req, res);
  })
);

/**
 * GET /health
 * Health check endpoint (no authentication required)
 * 
 * Response:
 * - 200: System healthy
 * - 503: System unhealthy
 */
router.get(
  '/health',
  asyncHandler(async (req, res) => {
    await artifactsController.healthCheck(req, res);
  })
);

export default router;
