import { Artifact } from '../types/artifacts.types';

// STRIDE mitigations: integrity, availability
export async function computeQualityScore(artifact: Artifact): Promise<number> {
  // TODO: Integrate with actual metric logic (e.g., DatasetAndCodeMetric)
  // Placeholder: return a random score for now
  return Math.random();
}

export async function computeDependencyScore(artifact: Artifact): Promise<number> {
  // TODO: Integrate with BusFactorMetric
  return Math.random();
}

export async function computeCodeReviewScore(artifact: Artifact): Promise<number> {
  // TODO: Integrate with CodeQualityMetric
  return Math.random();
}

// Integrity: Verify file hash
export async function verifyFileHash(artifact: Artifact): Promise<boolean> {
  // TODO: Implement hash verification (e.g., SHA256)
  return true;
}

// Integrity: Validate model schema
export async function validateModelSchema(artifact: Artifact): Promise<boolean> {
  // TODO: Implement schema validation
  return true;
}

// Size metric computation aligned with Phase 1 approach
// Given a total size in bytes, compute per-device size suitability scores
// and a latency placeholder. Devices: raspberry_pi, jetson_nano, desktop_pc, aws_server.
export function computeSizeScoreFromBytes(totalSizeBytes: number): {
  size_score: { raspberry_pi: number; jetson_nano: number; desktop_pc: number; aws_server: number };
  size_score_latency: number;
  size_metric: number;
} {
  if (!totalSizeBytes || totalSizeBytes <= 0) {
    return {
      size_score: { raspberry_pi: 0, jetson_nano: 0, desktop_pc: 0, aws_server: 0 },
      size_score_latency: 0,
      size_metric: 0,
    };
  }

  const CAPACITY = {
    raspberry_pi: 1 * 1024 ** 3, // 1 GB
    jetson_nano: 4 * 1024 ** 3,  // 4 GB
    desktop_pc: 16 * 1024 ** 3,  // 16 GB
    aws_server: 32 * 1024 ** 3,  // 32 GB
  } as const;

  const scoreFor = (capacity: number) => {
    const ratio = totalSizeBytes / capacity;
    return ratio <= 1 ? Math.max(0, 1 - ratio) : 0;
  };

  const size_score = {
    raspberry_pi: parseFloat(scoreFor(CAPACITY.raspberry_pi).toFixed(3)),
    jetson_nano: parseFloat(scoreFor(CAPACITY.jetson_nano).toFixed(3)),
    desktop_pc: parseFloat(scoreFor(CAPACITY.desktop_pc).toFixed(3)),
    aws_server: parseFloat(scoreFor(CAPACITY.aws_server).toFixed(3)),
  };

  const size_metric = Math.max(
    size_score.raspberry_pi,
    size_score.jetson_nano,
    size_score.desktop_pc,
    size_score.aws_server,
  );

  return { size_score, size_score_latency: 0, size_metric: parseFloat(size_metric.toFixed(3)) };
}
