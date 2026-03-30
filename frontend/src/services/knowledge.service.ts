
/**
 * Knowledge Base Service - Real API Integration
 * 
 * Connects to the backend RAG knowledge base endpoints.
 */

import { api } from './api';

const KNOWLEDGE_ENDPOINT = '/api/v1/knowledge';

export interface KnowledgeMetadata {
  source?: string;
  stage?: string;
  version?: string;
  [key: string]: any;
}

export interface KnowledgeEntry {
  id: string;
  title: string;
  content: string;
  metadata: KnowledgeMetadata;
  created_at: string;
}

export interface KnowledgeListParams {
  page?: number;
  page_size?: number;
  search?: string;
  source?: string;
  stage?: string;
}

export interface KnowledgeStats {
  total_documents: number;
  vector_count: number;
  total_size_bytes: number;
  by_source: Record<string, number>;
  by_stage: Record<string, number>;
  recent_uploads: Array<{ date: string; count: number }>;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percent: number;
}

export const knowledgeService = {
  /**
   * Get knowledge base statistics
   */
  async getStats(): Promise<KnowledgeStats> {
    try {
      const { items, total } = await this.listKnowledge({ page_size: 1000 });
      const bySource: Record<string, number> = {};
      const byStage: Record<string, number> = {};
      items.forEach((item) => {
        const src = item.metadata?.source || 'unknown';
        bySource[src] = (bySource[src] || 0) + 1;
        const stage = item.metadata?.stage || 'general';
        byStage[stage] = (byStage[stage] || 0) + 1;
      });
      return {
        total_documents: total,
        vector_count: total,
        total_size_bytes: 0,
        by_source: bySource,
        by_stage: byStage,
        recent_uploads: [],
      };
    } catch {
      return {
        total_documents: 0,
        vector_count: 0,
        total_size_bytes: 0,
        by_source: {},
        by_stage: {},
        recent_uploads: [],
      };
    }
  },

  validateFile(file: File): { valid: boolean; error?: string } {
    const maxSize = 50 * 1024 * 1024; // 50MB
    const allowed = ['.pdf', '.doc', '.docx', '.txt', '.md'];
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
    if (!allowed.includes(ext)) {
      return { valid: false, error: `File type not allowed. Use: ${allowed.join(', ')}` };
    }
    if (file.size > maxSize) {
      return { valid: false, error: 'File too large (max 50MB)' };
    }
    return { valid: true };
  },

  /**
   * List knowledge entries with pagination and filtering
   */
  async listKnowledge(params: KnowledgeListParams = {}): Promise<{ items: KnowledgeEntry[]; total: number }> {
    try {
        // Map frontend params to backend query params
        const queryParams = {
            limit: params.page_size || 10,
            offset: ((params.page || 1) - 1) * (params.page_size || 10),
        };
        const response = await api.get<any>(`${KNOWLEDGE_ENDPOINT}/list`, { params: queryParams });
        
        // Backend returns: { items: [...], next_offset: ... }
        const rawItems = response.items || [];
        
        const mappedItems = Array.isArray(rawItems) ? rawItems.map((item: any) => ({
            id: item.id,
            title: item.payload?.source || item.payload?.title || 'Untitled',
            content: item.payload?.text || '',
            metadata: item.payload || {},
            created_at: new Date().toISOString() // Vector store might not have created_at
        })) : [];

        return {
            items: mappedItems,
            total: mappedItems.length // Qdrant scroll doesn't give total easily
        };
    } catch (error) {
        console.error('[KnowledgeService] Failed to fetch knowledge:', error);
        return { items: [], total: 0 };
    }
  },

  /**
   * Upload text content
   */
  async uploadText(
    content: string,
    metadata: KnowledgeMetadata = {}
  ): Promise<{ success: boolean; id: string; message: string }> {
    try {
        const response = await api.post<{ status: string; ids: string[] }>(`${KNOWLEDGE_ENDPOINT}/text`, {
            content,
            source: metadata.source || 'admin-upload',
            stage: metadata.stage || 'general',
            type: 'text',
            collection_name: 'sales_knowledge'
        });
        return {
            success: true,
            id: response.ids?.[0] ?? 'unknown',
            message: 'Uploaded successfully'
        };
    } catch (error) {
        console.error('[KnowledgeService] Upload failed:', error);
        throw error;
    }
  },

  /**
   * Upload file
   */
  async uploadFile(
    file: File,
    _metadata?: KnowledgeMetadata,
    _onProgress?: (p: UploadProgress) => void
  ): Promise<{ success: boolean; id: string; message: string }> {
      try {
          const formData = new FormData();
          formData.append('file', file);
          
          // api.post handles FormData correctly if we don't force Content-Type json
          // But our api client forces application/json in default headers?
          // Axios usually overrides if data is FormData.
          // However, our api client sets 'Content-Type': 'application/json' in create().
          // We need to override it.
          
          const response = await api.post<{ status: string; ids: string[] }>(
              `${KNOWLEDGE_ENDPOINT}/upload`, 
              formData, 
              { headers: { 'Content-Type': 'multipart/form-data' } }
          );
          
          return {
              success: true,
              id: response.ids?.[0] ?? 'unknown',
              message: 'File uploaded successfully'
          };
      } catch (error) {
          console.error('[KnowledgeService] File upload failed:', error);
          throw error;
      }
  },

  async deleteKnowledge(id: string): Promise<boolean> {
      try {
          await api.delete(`${KNOWLEDGE_ENDPOINT}/${id}`);
          return true;
      } catch (error) {
          console.error('[KnowledgeService] Delete failed:', error);
          return false;
      }
  }
};
