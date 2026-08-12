export interface MedicalSource { id: string; name: string; domain: string; description: string }
export interface SourceReference { name: string; domain: string; title: string; url: string }
export interface ResponseSection { title: string; content: string }
export interface ChatResponse { answer: string; sections: ResponseSection[]; sources: SourceReference[]; safety_notice: string | null; mode: 'demo' | 'connected'; disclaimer: string; research_trace?: ResearchTraceEvent[]; research_summary?: ResearchSummary }
export interface ChatMessage { id: string; role: 'user' | 'assistant'; content: string; response?: ChatResponse; createdAt: string }
export interface Conversation { id: string; title: string; updatedAt: string; messages: ChatMessage[] }
export interface HealthCheckResponse { summary: string; reported_symptoms: string[]; general_considerations: string[]; self_care: string[]; seek_medical_attention: string[]; sources: SourceReference[]; safety_notice: string | null; mode: string; research_trace?: ResearchTraceEvent[]; research_summary?: ResearchSummary }
export interface NewsArticle { id: string; title: string; summary: string; category: NewsCategory; publisher: string; published_at: string; url: string }
export type NewsCategory = 'research' | 'nutrition' | 'mental-health' | 'public-health' | 'medicine'
import type { ResearchSummary, ResearchTraceEvent } from './research'

export type { ResearchSummary, ResearchTraceEvent } from './research'
