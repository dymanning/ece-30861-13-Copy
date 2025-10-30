// Load environment variables FIRST (before any other imports)
import dotenv from 'dotenv';
dotenv.config();

// ... rest of the file
import { db } from '../src/config/database';
import { logger } from '../src/utils/logger';

/**
 * Sample artifacts for testing
 */
const sampleArtifacts = [
  {
    id: '3847247294',
    name: 'audience-classifier',
    type: 'model',
    url: 'https://huggingface.co/parvk11/audience_classifier_model',
    readme: `# Audience Classifier Model

This model classifies text into different audience categories based on writing style and content.

## Model Details
- Architecture: BERT-based
- Training Dataset: Custom audience dataset
- Performance: 92% accuracy on test set

## Usage
\`\`\`python
from transformers import AutoModel
model = AutoModel.from_pretrained("parvk11/audience_classifier_model")
\`\`\`

## License
MIT License`,
  },
  {
    id: '5738291045',
    name: 'bookcorpus',
    type: 'dataset',
    url: 'https://huggingface.co/datasets/bookcorpus',
    readme: `# BookCorpus Dataset

A large corpus of books for language model training.

## Dataset Description
The BookCorpus dataset contains text from thousands of published books.

## Statistics
- Total books: 11,038
- Total words: ~74M
- Average words per book: ~68,000

## License
Apache 2.0`,
  },
  {
    id: '9182736455',
    name: 'google-research-bert',
    type: 'code',
    url: 'https://github.com/google-research/bert',
    readme: `# BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding

Official implementation of BERT.

## Overview
BERT is a method of pre-training language representations.

## What is BERT?
BERT stands for Bidirectional Encoder Representations from Transformers.

## Requirements
- Python 3.x
- TensorFlow 1.15+

## Citation
If you use BERT, please cite our paper.

## License
Apache License 2.0`,
  },
  {
    id: '9078563412',
    name: 'bert-base-uncased',
    type: 'model',
    url: 'https://huggingface.co/google-bert/bert-base-uncased',
    readme: `# BERT Base Uncased

This is the uncased version of BERT base model.

## Model description
BERT base model (uncased) pretrained on BookCorpus and English Wikipedia.

## Intended uses & limitations
Can be used for masked language modeling or next sentence prediction tasks.

## Training data
- BookCorpus (800M words)
- English Wikipedia (2,500M words)

## License
Apache License 2.0`,
  },
  {
    id: '7364518290',
    name: 'openai-whisper',
    type: 'code',
    url: 'https://github.com/openai/whisper',
    readme: `# Whisper

Whisper is a general-purpose speech recognition model by OpenAI.

## Approach
Whisper is a simple end-to-end approach, implemented as an encoder-decoder Transformer.

## Available models
We are releasing multiple model sizes:
- tiny
- base
- small
- medium
- large

## Setup
\`\`\`bash
pip install -U openai-whisper
\`\`\`

## License
MIT License`,
  },
  {
    id: '1234567890',
    name: 'transformers',
    type: 'code',
    url: 'https://github.com/huggingface/transformers',
    readme: `# Transformers

State-of-the-art Machine Learning for PyTorch, TensorFlow, and JAX.

## Features
- Easy-to-use interface
- Thousands of pretrained models
- Support for 100+ languages

## Installation
\`\`\`bash
pip install transformers
\`\`\`

## Quick tour
\`\`\`python
from transformers import pipeline
classifier = pipeline("sentiment-analysis")
\`\`\`

## License
Apache License 2.0`,
  },
  {
    id: '2345678901',
    name: 'gpt2',
    type: 'model',
    url: 'https://huggingface.co/gpt2',
    readme: `# GPT-2

GPT-2 is a transformers model pretrained on a large corpus of English data.

## Model description
GPT-2 is a large transformer-based language model with 1.5B parameters.

## Training data
Trained on WebText, a dataset of millions of webpages.

## Risks and limitations
The model was trained on unfiltered internet data.

## License
MIT License`,
  },
  {
    id: '3456789012',
    name: 'yolo-v8',
    type: 'model',
    url: 'https://github.com/ultralytics/yolov8',
    readme: `# YOLOv8

The latest version of YOLO by Ultralytics.

## Features
- State-of-the-art accuracy
- Fast inference speed
- Easy to train on custom data

## Installation
\`\`\`bash
pip install ultralytics
\`\`\`

## Usage
\`\`\`python
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
\`\`\`

## License
GPL-3.0`,
  },
  {
    id: '4567890123',
    name: 'imagenet',
    type: 'dataset',
    url: 'https://www.image-net.org',
    readme: `# ImageNet Dataset

Large-scale image classification dataset.

## Statistics
- Total images: 14M+
- Classes: 20,000+
- Competition subset: 1.2M images, 1000 classes

## Usage
Used for training computer vision models.

## Citation
ImageNet Large Scale Visual Recognition Challenge

## Access
Requires registration on the website.`,
  },
  {
    id: '5678901234',
    name: 'llama-2',
    type: 'model',
    url: 'https://huggingface.co/meta-llama/Llama-2-7b',
    readme: `# Llama 2

Meta's open-source large language model.

## Model Details
- Parameters: 7B, 13B, 70B versions
- Context length: 4096 tokens
- Training: 2 trillion tokens

## Performance
Competitive with proprietary models on many benchmarks.

## Usage
Requires agreement to Meta's license terms.

## License
Llama 2 Community License`,
  },
];

/**
 * Insert sample data into database
 */
async function insertSampleData() {
  try {
    logger.info('Inserting sample artifacts...');

    // Test connection
    const connected = await db.testConnection();
    if (!connected) {
      throw new Error('Database connection failed');
    }

    // Insert each artifact
    for (const artifact of sampleArtifacts) {
      const sql = `
        INSERT INTO artifacts (id, name, type, url, readme)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (id) DO UPDATE
        SET name = EXCLUDED.name,
            type = EXCLUDED.type,
            url = EXCLUDED.url,
            readme = EXCLUDED.readme,
            updated_at = NOW()
      `;

      const params = [
        artifact.id,
        artifact.name,
        artifact.type,
        artifact.url,
        artifact.readme,
      ];

      await db.query(sql, params);
      logger.info(`Inserted: ${artifact.name} (${artifact.type})`);
    }

    // Verify insertion
    const countResult = await db.query('SELECT COUNT(*) as count FROM artifacts');
    const totalCount = countResult.rows[0].count;

    logger.info(`Sample data insertion completed. Total artifacts: ${totalCount}`);

    // Show summary by type
    const summaryResult = await db.query(`
      SELECT type, COUNT(*) as count
      FROM artifacts
      GROUP BY type
      ORDER BY type
    `);

    logger.info('Artifacts by type:', {
      breakdown: summaryResult.rows,
    });

    await db.close();
    process.exit(0);
  } catch (error) {
    logger.error('Failed to insert sample data:', error);
    await db.close();
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  insertSampleData();
}

export { sampleArtifacts, insertSampleData };
