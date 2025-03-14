import dotenv from 'dotenv';
import fetch from 'isomorphic-fetch';

dotenv.config();

if (!process.env.PERPLEXITY_API_KEY) {
  throw new Error('PERPLEXITY_API_KEY environment variable is required');
}

type ToolHandler<T> = (args: T) => Promise<unknown>;

export interface Tool<T = any> {
  name: string;
  description: string;
  inputSchema: {
    type: string;
    properties: Record<string, unknown>;
    required?: string[];
  };
  handler: ToolHandler<T>;
}

const PERPLEXITY_API_URL = 'https://api.perplexity.ai/chat/completions';

export const tools: Tool[] = [
  {
    name: 'perplexity_chat',
    description: 'Generate a chat completion using Perplexity AI',
    inputSchema: {
      type: 'object',
      properties: {
        model: {
          type: 'string',
          enum: ['mixtral-8x7b-instruct', 'codellama-34b-instruct', 'sonar-small-chat', 'sonar-small-online'],
          description: 'The model to use for completion'
        },
        messages: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              role: {
                type: 'string',
                enum: ['system', 'user', 'assistant']
              },
              content: {
                type: 'string'
              }
            },
            required: ['role', 'content']
          },
          description: 'Array of messages in the conversation'
        },
        temperature: {
          type: 'number',
          description: 'Sampling temperature (0-2)',
          minimum: 0,
          maximum: 2
        }
      },
      required: ['messages']
    },
    handler: async (args: {
      model?: string;
      messages: Array<{ role: string; content: string }>;
      temperature?: number;
    }) => {
      const response = await fetch(PERPLEXITY_API_URL, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.PERPLEXITY_API_KEY}`
        },
        body: JSON.stringify({
          model: args.model || 'mixtral-8x7b-instruct',
          messages: args.messages,
          temperature: args.temperature || 0.7
        })
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Perplexity API error: ${error}`);
      }

      const data = await response.json();
      return data;
    }
  },
  {
    name: 'perplexity_ask',
    description: 'Send a simple query to Perplexity AI',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'The question or prompt to send'
        },
        model: {
          type: 'string',
          enum: ['llama-3.1-sonar-small-128k-online', 'llama-3.1-sonar-large-128k-online', 'llama-3.1-sonar-huge-128k-online'],
          description: 'The model to use for completion'
        }
      },
      required: ['query']
    },
    handler: async (args: { query: string; model?: string }) => {
      const messages = [{ role: 'user', content: args.query }];
      const response = await fetch(PERPLEXITY_API_URL, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${process.env.PERPLEXITY_API_KEY}`
        },
        body: JSON.stringify({
          model: args.model || 'llama-3.1-sonar-small-128k-online',
          messages
        })
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Perplexity API error: ${error}`);
      }

      const data = await response.json();
      return data.choices[0].message.content;
    }
  }
];