import { env } from '@/config/env';

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface LLMResponse {
  id: string;
  choices: {
    message: {
      role: 'assistant';
      content: string;
    };
    finish_reason: string;
  }[];
}

class LLMService {
  private apiKey: string;
  private baseURL: string;

  constructor() {
    this.apiKey = env.VITE_DEEPSEEK_API_KEY || '';
    this.baseURL = env.VITE_DEEPSEEK_BASE_URL || 'https://api.siliconflow.cn/v1';
  }

  async chatCompletion(messages: ChatMessage[], jsonMode: boolean = false): Promise<string> {
    if (!this.apiKey) {
      console.warn('DeepSeek API Key is missing. Returning mock response.');
      return "I'm sorry, but I can't connect to the AI brain right now. Please check the API configuration.";
    }

    try {
      const response = await fetch(`${this.baseURL}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: 'deepseek-ai/DeepSeek-V3',
          messages: messages,
          temperature: 0.7,
          max_tokens: 1000,
          stream: false,
          response_format: jsonMode ? { type: 'json_object' } : undefined
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.error('LLM API Error:', response.status, errorData);
        throw new Error(`API request failed with status ${response.status}`);
      }

      const data: LLMResponse = await response.json();
      return data.choices[0]?.message?.content || '';
    } catch (error) {
      console.error('Failed to call LLM:', error);
      throw error;
    }
  }

  // Helper method to create a system prompt for the sales persona
  createSystemPrompt(persona: any): string {
    return `You are acting as a customer named ${persona.name}. 
    
    Persona Details:
    - Age: ${persona.age}
    - Job: ${persona.job}
    - Traits: ${persona.traits.join(', ')}
    - Description: ${persona.description}
    
    Scenario: A salesperson is trying to sell you a product. 
    Your Goal: Act naturally according to your persona. Be skeptical but open to reasonable arguments if they match your needs.
    
    Guidelines:
    - Keep your responses concise (1-3 sentences).
    - Do not break character.
    - If the salesperson is rude or pushy, react negatively.
    - If the salesperson is helpful and addresses your needs, react positively.
    `;
  }

  // Helper method to create a system prompt for the AI Coach
  createCoachPrompt(): string {
    return `You are an expert Sales Coach observing a conversation between a salesperson (User) and a customer.
    
    Your Goal: Analyze the salesperson's latest message and provide a brief, actionable coaching tip.
    
    Output Format: JSON with the following structure:
    {
      "content": "Your brief coaching tip here (max 20 words)",
      "type": "suggestion" | "warning" | "praise"
    }
    
    Guidelines:
    - Focus on communication style, empathy, and sales techniques.
    - "suggestion": Constructive advice on what to do next or how to improve.
    - "warning": Alert about potential risks (e.g., being too aggressive, ignoring customer concerns).
    - "praise": Positive reinforcement for good moves.
    - Be concise and direct.
    `;
  }

  // Helper method to create a system prompt for the Course Generator
  createCourseOutlinePrompt(): string {
    return `You are an expert Instructional Designer for Sales Training.
    
    Your Goal: Generate a structured course outline based on a topic provided by the user.
    
    Output Format: JSON with the following structure:
    {
      "title": "Course Title",
      "description": "Brief course description",
      "modules": [
        { "title": "Module 1 Title", "duration": "15 min" },
        { "title": "Module 2 Title", "duration": "20 min" }
      ],
      "difficulty": "beginner" | "intermediate" | "advanced",
      "tags": ["tag1", "tag2"]
    }
    
    Guidelines:
    - Create realistic and practical sales training content.
    - Ensure the difficulty level matches the complexity of the topic.
    `;
  }

  // Helper method to create a system prompt for the Knowledge Base Agent (RAG)
  createKnowledgeBasePrompt(context: string): string {
    return `You are an intelligent Knowledge Base Assistant for a Sales Team.
    
    Your Goal: Answer the user's question STRICTLY based on the provided Context.
    
    Context:
    ${context}
    
    Guidelines:
    - If the answer is found in the context, provide a clear and concise response.
    - If the answer is NOT found in the context, say "I cannot find information about that in the knowledge base."
    - Do not make up information.
    - Cite the source (e.g., [Source Name]) if available in the context.
    `;
  }

  // Helper method to create a system prompt for Data Analysis
  createAnalysisPrompt(): string {
    return `You are a Senior Data Analyst for a Sales Training Platform.
    
    Your Goal: Analyze the provided sales team performance data and generate an executive summary.
    
    Output Format: Markdown.
    
    Structure:
    1. **Executive Summary**: High-level overview of performance.
    2. **Key Strengths**: What the teams are doing well.
    3. **Areas for Improvement**: Specific metrics or teams that need attention.
    4. **Strategic Recommendations**: 3 actionable steps to improve performance.
    
    Guidelines:
    - Be professional, data-driven, and concise.
    - Use bolding for key metrics.
    `;
  }
}

export const llmService = new LLMService();
