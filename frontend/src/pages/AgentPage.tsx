import React, { useState, useRef, useEffect } from 'react';
import { AgentMessage, ToolCallRecord } from '../types';
import { apiClient } from '../api/client';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ErrorState } from '../components/ui/ErrorState';
import {
  Send,
  Globe,
  User,
  Wrench,
  CheckCircle2,
  Sparkles,
  AlertCircle,
  HelpCircle,
  Clock,
  Check,
} from 'lucide-react';

const SUGGESTED_QUESTIONS = [
  'Has rainfall changed in Gujarat over the last 20 years?',
  'Compare precipitation trends between Amazon Basin and Sahel',
  'What is the precipitation trend in California since 2000?',
  'Show me the trend analysis for monsoon Asia',
];

export const AgentPage: React.FC = () => {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [input, setInput] = useState<string>('');
  const [isSending, setIsSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const handleSend = async (messageText?: string) => {
    const textToSend = (messageText ?? input).trim();
    if (!textToSend || isSending) return;

    const userMessage: AgentMessage = {
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString(),
    };

    const newHistory = [...messages, userMessage];
    setMessages(newHistory);
    setInput('');
    setIsSending(true);
    setError(null);

    try {
      const response = await apiClient.chatWithAgent({
        message: textToSend,
        conversation_history: newHistory,
      });

      const assistantMessage: AgentMessage = {
        role: 'assistant',
        content: response.response,
        tool_calls: response.tool_calls_made,
        timestamp: response.timestamp || new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(
        err?.message ||
          'Failed to reach Ask BHIMA agent. Verify the backend and GEMINI_API_KEY configuration.'
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] min-h-[500px] bg-white border border-bhima-border rounded-lg overflow-hidden shadow-xs">
      {/* Agent Chat Header */}
      <div className="h-14 border-b border-bhima-border px-5 flex items-center justify-between bg-bhima-subtle/30 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-bhima-primary flex items-center justify-center text-white">
            <Globe className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-bhima-text flex items-center gap-1.5">
              Ask BHIMA Copilot
              <Badge variant="primary" size="sm">
                Earth System Agent
              </Badge>
            </h3>
            <p className="text-[10px] text-bhima-secondary font-mono">
              Tool Calling Enabled • Mann-Kendall & GPM / MODIS
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setMessages([]);
              setError(null);
            }}
          >
            Clear History
          </Button>
        )}
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-8">
            <div className="w-12 h-12 rounded-full bg-bhima-subtle border border-bhima-border flex items-center justify-center text-bhima-primary mb-3">
              <Globe className="w-6 h-6" />
            </div>

            <h3 className="text-base font-semibold text-bhima-text mb-1">
              Ask Earth Science Inquiries
            </h3>
            <p className="text-xs text-bhima-muted mb-6 leading-relaxed">
              Ask questions regarding precipitation patterns, multi-decadal trends, or regional
              comparisons. The agent calls verified data extraction and trend calculation routines.
            </p>

            <div className="w-full space-y-2 text-left">
              <span className="text-[11px] font-semibold text-bhima-secondary uppercase tracking-wider block mb-1">
                Suggested Prompts
              </span>
              {SUGGESTED_QUESTIONS.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(question)}
                  className="w-full p-2.5 text-xs text-left bg-bhima-subtle/70 hover:bg-bhima-subtle border border-bhima-border rounded-md text-bhima-text transition-colors flex items-center justify-between group"
                >
                  <span>{question}</span>
                  <Send className="w-3.5 h-3.5 text-bhima-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 max-w-3xl ${
                msg.role === 'user' ? 'ml-auto justify-end' : 'mr-auto justify-start'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-full bg-bhima-primary flex items-center justify-center text-white shrink-0 mt-0.5">
                  <Globe className="w-4 h-4" />
                </div>
              )}

              <div className="space-y-2">
                {/* Tool calls indicator */}
                {msg.tool_calls && msg.tool_calls.length > 0 && (
                  <div className="space-y-1">
                    {msg.tool_calls.map((toolCall, tIdx) => (
                      <div
                        key={tIdx}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-bhima-subtle border border-bhima-border text-[11px] font-mono text-bhima-muted"
                      >
                        <Wrench className="w-3 h-3 text-bhima-secondary" />
                        <span>Tool Executed: <strong>{toolCall.tool}</strong></span>
                        <CheckCircle2 className="w-3 h-3 text-emerald-600 ml-1" />
                      </div>
                    ))}
                  </div>
                )}

                <div
                  className={`p-3.5 rounded-lg text-xs leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-bhima-primary text-white rounded-br-none shadow-xs'
                      : 'bg-bhima-subtle text-bhima-text rounded-bl-none border border-bhima-border'
                  }`}
                >
                  {msg.content}
                </div>

                {msg.timestamp && (
                  <div
                    className={`text-[10px] text-bhima-muted flex items-center gap-1 ${
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    }`}
                  >
                    <Clock className="w-2.5 h-2.5" />
                    <span>{new Date(msg.timestamp).toLocaleTimeString()}</span>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-[#E4E8E4] flex items-center justify-center text-bhima-text shrink-0 mt-0.5">
                  <User className="w-4 h-4 text-bhima-muted" />
                </div>
              )}
            </div>
          ))
        )}

        {/* Live tool execution indicator during query */}
        {isSending && (
          <div className="flex gap-3 max-w-2xl mr-auto items-start animate-fade-in">
            <div className="w-7 h-7 rounded-full bg-bhima-primary flex items-center justify-center text-white shrink-0 mt-0.5">
              <Globe className="w-4 h-4" />
            </div>
            <div className="p-3 bg-bhima-subtle rounded-lg border border-bhima-border flex items-center gap-2.5 text-xs text-bhima-text shadow-xs">
              <LoadingSpinner size="sm" variant="accent" />
              <span>Analyzing NASA observation records & running non-parametric test...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-xs text-bhima-danger flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <strong className="font-semibold">Backend Communication Error: </strong>
              {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box Area */}
      <div className="p-3 sm:p-4 border-t border-bhima-border bg-white shrink-0">
        <div className="flex items-center gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about Earth observations, trends, or regions... (Shift+Enter for newline)"
            className="flex-1 resize-none bg-bhima-subtle/50 border border-bhima-border rounded-md px-3.5 py-2 text-xs text-bhima-text placeholder-bhima-muted focus:outline-none focus:ring-1 focus:ring-bhima-primary"
            disabled={isSending}
          />
          <Button
            size="md"
            onClick={() => handleSend()}
            disabled={!input.trim() || isSending}
            isLoading={isSending}
            aria-label="Send message"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
        <div className="text-[10px] text-bhima-secondary mt-1.5 flex items-center justify-between px-1">
          <span>Responses cite exact statistical confidence & Sen's slopes.</span>
          <span>Shift+Enter for newline</span>
        </div>
      </div>
    </div>
  );
};
