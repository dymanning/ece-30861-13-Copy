import { Artifact, MetricScores } from '../types/artifacts.types';
import { computeQualityScore, computeDependencyScore, computeCodeReviewScore, verifyFileHash, validateModelSchema } from '../utils/metric.utils';
import { saveArtifactWithMetrics } from '../packages_api/database';
import { logger } from '../utils/logger';

// STRIDE mitigations: authentication, integrity, non-repudiation, confidentiality, availability, authorization
export async function ingestPublicPackage(artifact: Artifact, user: { id: string; role: string }): Promise<{ status: string; metadata?: MetricScores }> {
  // Authentication: Require valid user
  if (!user || !user.id) {
    logger.warn('Authentication failed: Missing user');
    return { status: 'Rejected: Authentication required' };
  }

  // Integrity: Verify file hash and schema
  if (!(await verifyFileHash(artifact))) {
    logger.warn('Integrity check failed: Hash mismatch');
    return { status: 'Rejected: File integrity check failed' };
  }
  if (!(await validateModelSchema(artifact))) {
    logger.warn('Integrity check failed: Invalid model schema');
    return { status: 'Rejected: Model schema validation failed' };
  }

  // Metric calculation (server-side only)
  const qualityScore = await computeQualityScore(artifact);
  if (qualityScore < 0.5) {
    logger.info('Quality score too low, rejecting package');
    return { status: 'Rejected: Quality score too low' };
  }
  const dependencyScore = await computeDependencyScore(artifact);
  const codeReviewScore = await computeCodeReviewScore(artifact);

  // Non-repudiation: Log upload event
  logger.info('Artifact upload', {
    userId: user.id,
    artifactId: artifact.metadata.id,
    timestamp: new Date().toISOString(),
  });

  // Confidentiality: Do not log sensitive fields
  // Availability: Enforce file size limit (example: 200MB)
  if (artifact.data && artifact.data.url && artifact.data.url.length > 0) {
    // Placeholder for file size check
    // if (getFileSize(artifact.data.url) > 200 * 1024 * 1024) {
    //   logger.warn('File size exceeds limit');
    //   return { status: 'Rejected: File size exceeds limit' };
    // }
  }

  // Authorization: Only allow upload if user is authenticated
  if (user.role !== 'admin' && artifact.metadata.type === 'reset') {
    logger.warn('Authorization failed: Non-admin attempted reset');
    return { status: 'Rejected: Admin privileges required' };
  }

  // Store metrics in metadata
  const metadata: MetricScores = {
    qualityScore,
    dependencyScore,
    codeReviewScore,
  };

  await saveArtifactWithMetrics(artifact, metadata);
  return { status: 'Ingested', metadata };
}