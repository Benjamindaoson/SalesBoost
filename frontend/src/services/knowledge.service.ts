/**
 * Knowledge Base Management Service (Client-Side RAG Version)
 * 
 * Replaces the mock API with a real client-side implementation:
 * - Stores knowledge items in LocalStorage.
 * - Uses DeepSeek V3 (via llm.service) for "Context-Stuffing RAG" search.
 */

import { llmService, ChatMessage } from './llm.service';

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

export interface KnowledgeStats {
  total_documents: number;
  total_chars: number;
  recent_uploads: Array<{ date: string; count: number }>;
}

const STORAGE_KEY = 'salesboost_knowledge_base';

class KnowledgeService {
  private getStorage(): KnowledgeEntry[] {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  }

  private setStorage(data: KnowledgeEntry[]) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }

  /**
   * Upload text content to the local knowledge base
   */
  async uploadText(
    title: string,
    content: string,
    metadata: KnowledgeMetadata = {}
  ): Promise<{ success: boolean; id: string }> {
    const entries = this.getStorage();
    const newEntry: KnowledgeEntry = {
      id: Date.now().toString(),
      title,
      content,
      metadata: { ...metadata, source: 'user-upload' },
      created_at: new Date().toISOString(),
    };
    
    this.setStorage([newEntry, ...entries]);
    return { success: true, id: newEntry.id };
  }

  /**
   * Upload a file to the knowledge base (Client-side read)
   */
  async uploadFile(
    file: File,
    metadata: KnowledgeMetadata,
    onProgress?: (progress: { loaded: number; total: number; percentage: number }) => void
  ): Promise<{ success: boolean; id: string; message: string }> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      
      reader.onload = async (e) => {
        try {
          const content = e.target?.result as string;
          const result = await this.uploadText(file.name, content, metadata);
          if (onProgress) onProgress({ loaded: file.size, total: file.size, percentage: 100 });
          resolve({ ...result, message: 'File uploaded successfully' });
        } catch (error) {
          reject(error);
        }
      };

      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsText(file);
    });
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File): { valid: boolean; error?: string } {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = [
      'text/plain',
      'text/markdown',
      'application/json',
      'application/pdf', // Note: PDF parsing in browser requires PDF.js, treating as text for now might fail if binary
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
    ];

    if (file.size > maxSize) {
      return {
        valid: false,
        error: `File size exceeds 10MB limit (${(file.size / 1024 / 1024).toFixed(2)}MB)`,
      };
    }

    // Relaxed type check for demo purposes
    // if (!allowedTypes.includes(file.type)) { ... }

    return { valid: true };
  }

  /**
   * List knowledge entries
   */
  async listKnowledge(): Promise<KnowledgeEntry[]> {
    return this.getStorage();
  }

  /**
   * Delete a knowledge entry
   */
  async deleteKnowledge(id: string): Promise<void> {
    const entries = this.getStorage();
    this.setStorage(entries.filter(e => e.id !== id));
  }

  /**
   * Get knowledge base statistics
   */
  async getStats(): Promise<KnowledgeStats> {
    const entries = this.getStorage();
    return {
      total_documents: entries.length,
      total_chars: entries.reduce((acc, curr) => acc + curr.content.length, 0),
      recent_uploads: [] // Simplified for now
    };
  }

  /**
   * Search knowledge base using DeepSeek V3 (Real RAG)
   */
  async search(query: string): Promise<string> {
    const entries = this.getStorage();
    
    if (entries.length === 0) {
      return "The knowledge base is empty. Please upload some documents first.";
    }

    // Context Stuffing: Combine all titles and content
    // Limit context size to avoid token limits (simple truncation for now)
    let context = "";
    for (const entry of entries) {
      const entryText = `Source: ${entry.title}\nContent: ${entry.content}\n---\n`;
      if ((context.length + entryText.length) < 50000) { // Safety limit for client-side
        context += entryText;
      }
    }

    try {
      const systemPrompt = llmService.createKnowledgeBasePrompt(context);
      const messages: ChatMessage[] = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: query }
      ];

      const response = await llmService.chatCompletion(messages);
      return response;
    } catch (error) {
      console.error("RAG Search Failed:", error);
      return "Sorry, I encountered an error while searching the knowledge base.";
    }
  }
  
  // Initialize with some default data if empty
  initDefaults() {
    if (this.getStorage().length === 0) {
      this.uploadText(
        "Sales Boost FAQ", 
        "Q: What is SalesBoost? A: SalesBoost is an AI-powered training platform.\nQ: How do I reset my password? A: Contact admin support.",
        { stage: 'onboarding' }
      );
    }
  }
}

export const knowledgeService = new KnowledgeService();
// Initialize defaults on load
knowledgeService.initDefaults();
export default knowledgeService;
