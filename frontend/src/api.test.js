import assert from 'node:assert/strict';
import test from 'node:test';

import { normalizeVisionUpload } from './api.js';

test('normalizes the Vision API upload contract for the UI', () => {
  const image = normalizeVisionUpload({
    image_id: 'figure-123',
    filename: 'chart.png',
    file_size: 1024,
    dimensions: [600, 400],
    mime_type: 'image/png',
    preview_url: '/api/vision/figure-123/file',
  });

  assert.deepEqual(image, {
    id: 'figure-123',
    filename: 'chart.png',
    width: 600,
    height: 400,
    aspectRatio: 1.5,
    mimeType: 'image/png',
    previewUrl: '/api/vision/figure-123/file',
    documentId: null,
  });
});

test('preserves the linked paper id on vision uploads', () => {
  const image = normalizeVisionUpload({
    image_id: 'figure-456',
    filename: 'roc.png',
    file_size: 2048,
    dimensions: [800, 600],
    mime_type: 'image/png',
    preview_url: '/api/vision/figure-456/file',
    document_id: 'doc-abc',
  });

  assert.equal(image.documentId, 'doc-abc');
});
