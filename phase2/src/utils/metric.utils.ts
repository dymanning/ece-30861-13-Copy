import { Artifact } from '../types/artifacts.types';

// STRIDE mitigations: integrity, availability
export async function computeQualityScore(artifact: Artifact): Promise<number> {
  // Deterministic heuristic quality score (Phase 1 style):
  // - Start at base 0.5
  // - Reward modest dependency footprint
  // - Reward presence of documentation/readme-like metadata
  // - Clamp to [0,1]
  let score = 0.5;

  try {
    const deps = Array.isArray(artifact.metadata.dependencies)
      ? artifact.metadata.dependencies.length
      : Array.isArray((artifact as any).dependencies)
        ? ((artifact as any).dependencies as any[]).length
        : 0;

    if (deps <= 3) {
      score += 0.2;
    } else if (deps <= 8) {
      score += 0.1;
    }

    const meta = (artifact.metadata?.metadata ?? artifact.metadata) as any;
    const docFlags = [
      'documentation',
      'readme_url',
      'homepage',
      'examples',
      'tutorials',
    ];
    const hasDocs = docFlags.some((k) => Boolean(meta && meta[k]));
    const readmeLen = typeof meta?.readme_length === 'number' ? meta.readme_length : 0;
    if (hasDocs || readmeLen >= 500) {
      score += 0.2;
    }
  } catch {
    // keep base score on unexpected shapes
  }

  if (Number.isNaN(score)) score = 0.5;
  return Math.max(0, Math.min(1, parseFloat(score.toFixed(3))));
}

export async function computeDependencyScore(artifact: Artifact): Promise<number> {
  // Phase 1–style dependency/bus-factor heuristic:
  // Fewer direct dependencies → higher score. Clamp [0,1].
  const depsCount = Array.isArray(artifact.metadata.dependencies)
    ? artifact.metadata.dependencies.length
    : Array.isArray((artifact as any).dependencies)
      ? ((artifact as any).dependencies as any[]).length
      : 0;

  let score: number;
  if (depsCount <= 2) score = 0.9;
  else if (depsCount <= 5) score = 0.7;
  else if (depsCount <= 10) score = 0.5;
  else if (depsCount <= 20) score = 0.3;
  else score = 0.1;

  return Math.max(0, Math.min(1, parseFloat(score.toFixed(3))));
}

export async function computeCodeReviewScore(artifact: Artifact): Promise<number> {
  // Deterministic code quality heuristic using metadata doc signals.
  // Presence of docs/examples/homepage and longer README yields higher score.
  const meta = (artifact.metadata?.metadata ?? artifact.metadata) as any;
  const docFlags = ['documentation', 'readme_url', 'homepage', 'examples', 'tutorials'];
  const hasDocs = docFlags.some((k) => Boolean(meta && meta[k]));
  const readmeLen = typeof meta?.readme_length === 'number' ? meta.readme_length : 0;

  let score = 0.4;
  if (hasDocs) score += 0.3;
  if (readmeLen >= 500) score += 0.2;
  if (readmeLen >= 2000) score += 0.1;

  return Math.max(0, Math.min(1, parseFloat(score.toFixed(3))));
}

// Integrity: Verify file hash metadata (SHA256) and size
// For URL-based ingestion, we validate hash format and presence; when file streams are added,
// this function should compute the SHA256 of the uploaded bytes and compare against provided hash.
export async function verifyFileHashMetadata(hash?: string, sizeBytes?: number): Promise<boolean> {
  if (!hash || typeof hash !== 'string') {
    return false;
  }
  // Must be 64 hex characters
  const isHex64 = /^[a-fA-F0-9]{64}$/.test(hash);
  if (!isHex64) {
    return false;
  }
  // Size must be a positive integer if provided
  if (sizeBytes !== undefined) {
    if (!Number.isInteger(sizeBytes) || sizeBytes <= 0) {
      return false;
    }
  }
  return true;
}

// Integrity: Validate model schema
export async function validateModelSchema(artifact: Artifact): Promise<boolean> {
  // Minimal schema validation for ArtifactMetadata presence and required fields.
  try {
    const m = artifact?.metadata as any;
    if (!m) return false;
    const required = ['id', 'name', 'type'];
    for (const key of required) {
      if (!(key in m)) return false;
    }
    // type must be one of model/dataset/code
    if (!['model', 'dataset', 'code'].includes(String(m.type))) return false;
    // size must be a non-negative number if present
    if (m.size !== undefined && (typeof m.size !== 'number' || m.size < 0)) return false;
    // rating object should exist with size_score keys
    const r = m.rating;
    if (!r || typeof r !== 'object') return false;
    const ss = r.size_score;
    if (!ss || typeof ss !== 'object') return false;
    if (!('raspberry_pi' in ss) || !('jetson_nano' in ss)) return false;
    return true;
  } catch {
    return false;
  }
}

// Size metric computation aligned with Phase 1 approach
// Given a total size in bytes, compute per-device size suitability scores
// and a latency placeholder. Devices: raspberry_pi, jetson_nano (spec-compliant).
export function computeSizeScoreFromBytes(totalSizeBytes: number): {
  size_score: { raspberry_pi: number; jetson_nano: number };
  size_score_latency: number;
} {
  // Phase 1–style piecewise scoring mirrored for bytes (deployability thresholds)
  // Thresholds roughly align to device practicality bands.
  const MB = 1024 * 1024;

  const scorePi = (bytes: number): number => {
    if (bytes <= 64 * MB) return 1.0;          // very small
    if (bytes <= 128 * MB) return 0.8;         // small
    if (bytes <= 256 * MB) return 0.5;         // moderate
    if (bytes <= 512 * MB) return 0.2;         // large
    return 0.0;                                 // too large
  };

  const scoreNano = (bytes: number): number => {
    if (bytes <= 128 * MB) return 1.0;
    if (bytes <= 300 * MB) return 0.8;
    if (bytes <= 500 * MB) return 0.5;
    if (bytes <= 1024 * MB) return 0.2;        // 1GB
    return 0.0;
  };

  const size_score = {
    raspberry_pi: parseFloat(scorePi(totalSizeBytes).toFixed(3)),
    jetson_nano: parseFloat(scoreNano(totalSizeBytes).toFixed(3)),
  };

  return { size_score, size_score_latency: 0 };
}
