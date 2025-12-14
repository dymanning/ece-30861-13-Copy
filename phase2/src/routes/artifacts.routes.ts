import { Router } from 'express';
import { artifactsController } from '../controllers/artifacts.controller';
import { authenticate, requirePermission } from '../middleware/auth.middleware';
import { asyncHandler } from '../middleware/error.middleware';

/**
 * Artifacts routes
 * Defines all artifact search and enumeration endpoints
 */
const router = Router();

/**
 * POST /artifact/:type
 * Create/upload a new artifact
 * 
 * BASELINE requirement
 * 
 * Request:
 * - Header: X-Authorization (required)
 * - Path: type (model|dataset|code)
 * - Body: { data: { url: string } }
 * 
 * Response:
 * - 201: Artifact created
 * - 400: Invalid request
 * - 403: Authentication failed
 * - 409: Artifact already exists
 */
router.post(
  '/artifact/:type',
  authenticate,
  requirePermission('upload'),
  asyncHandler(async (req, res) => {
    await artifactsController.createArtifact(req, res);
  })
);

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
  requirePermission('search'),
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
  requirePermission('search'),
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
  requirePermission('search'),
  asyncHandler(async (req, res) => {
    await artifactsController.searchByName(req, res);
  })
);

/**
 * GET /artifacts/:type/:id
 * Retrieve artifact by ID and type
 * 
 * BASELINE requirement
 * 
 * Request:
 * - Header: X-Authorization (required)
 * - Path: type (model|dataset|code), id (artifact ID)
 * 
 * Response:
 * - 200: Artifact with full metadata and data
 * - 400: Invalid artifact type
 * - 403: Authentication failed
 * - 404: Artifact not found
 */
router.get(
  '/artifacts/:type/:id',
  authenticate,
  requirePermission('download'),
  asyncHandler(async (req, res) => {
    await artifactsController.getArtifact(req, res);
  })
);

/**
 * DELETE /artifacts/:type/:id
 * Delete artifact by ID and type
 * 
 * BASELINE requirement
 * 
 * Request:
 * - Header: X-Authorization (required)
 * - Path: type (model|dataset|code), id (artifact ID)
 * 
 * Response:
 * - 200: Deletion successful
 * - 400: Invalid artifact type
 * - 403: Authentication failed
 * - 404: Artifact not found
 */
router.delete(
  '/artifacts/:type/:id',
  authenticate,
  requirePermission('admin'),
  asyncHandler(async (req, res) => {
    await artifactsController.deleteArtifact(req, res);
  })
);

/**
 * GET /artifact/model/:id/lineage
 * Get lineage graph for a model
 * 
 * BASELINE requirement
 * 
 * Request:
 * - Header: X-Authorization (required)
 * - Path: id (model ID)
 * 
 * Response:
 * - 200: ArtifactLineageGraph with nodes and edges
 * - 403: Authentication failed
 * - 404: Model not found
 */
router.get(
  '/artifact/model/:id/lineage',
  authenticate,
  requirePermission('search'),
  asyncHandler(async (req, res) => {
    await artifactsController.getLineage(req, res);
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
