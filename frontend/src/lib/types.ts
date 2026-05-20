export type Routing = "auto_approve" | "needs_review" | "reject";

export interface Dataset {
  id: string;
  name: string;
  description: string | null;
  image_count: number;
  status: string;
  created_at: string;
}

export interface Job {
  id: string;
  dataset_id: string;
  type: string;
  status: string;
  total: number;
  processed: number;
  failed: number;
  created_at: string;
  finished_at: string | null;
}

export interface Detection {
  label: string;
  bbox: [number, number, number, number];
  score: number;
  clip_score: number | null;
  mask_quality: number | null;
  confidence: number | null;
}

export interface Annotation {
  id: string;
  image_id: string;
  version: number;
  status: string;
  detections: Detection[];
  caption: string | null;
  tags: string[];
  confidence: Record<string, unknown>;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
