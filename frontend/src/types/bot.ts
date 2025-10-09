export interface Bot {
  id: string;
  name: string;
  description: string;
  embedding_model: string;
  ocr_lang: string;
  created_at: string;
  updated_at: string;
  vectorstore_path: string;
  is_active: boolean;
  chunk_size: number;
  chunk_overlap: number;
}

export interface BotStats {
  num_chunks: number;
  vectorstore_exists: boolean;
  vectorstore_size_mb: number;
  num_files: number;
}

export interface BotWithStats extends Bot {
  stats?: BotStats;
}