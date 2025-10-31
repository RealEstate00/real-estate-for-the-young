import React, { useState, useRef, useEffect } from "react";
import { Send, RotateCcw, Home, FileText } from "lucide-react";
import {
  askWithAgent,
  clearMemory,
  ChatMessage,
  SourceInfo,
} from "../services/llmApi";

interface Message extends ChatMessage {
  timestamp: Date;
  sources?: SourceInfo[];
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Agent API 사용 (inha 브랜치 기능)
      const response = await askWithAgent(input, "ollama");

      const aiMessage: Message = {
        role: "assistant",
        content: response.message,
        sources: response.sources,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: Message = {
        role: "assistant",
        content:
          "죄송합니다. 응답 중 오류가 발생했습니다. 서버 연결을 확인해주세요.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = async () => {
    if (window.confirm("대화 내역을 모두 삭제하시겠습니까?")) {
      try {
        await clearMemory("ollama");
        setMessages([]);
      } catch (error) {
        console.error("Failed to clear chat:", error);
        // API 호출 실패해도 로컬 메시지는 초기화
        setMessages([]);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Home className="w-6 h-6 text-blue-600" />
            <h1 className="text-xl font-bold text-gray-800">
              청년을 위한 서울 주택 안내
            </h1>
          </div>
          <button
            onClick={handleClearChat}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
            title="대화 초기화"
          >
            <RotateCcw className="w-4 h-4" />
            대화 초기화
          </button>
        </div>
      </header>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 max-w-md">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Home className="w-8 h-8 text-blue-600" />
                </div>
                <h2 className="text-xl font-semibold text-gray-800 mb-2">
                  무엇을 도와드릴까요?
                </h2>
                <p className="text-sm text-gray-600 mb-4">
                  서울시 청년 주택에 대해 궁금한 점을 물어보세요
                </p>
                <div className="bg-gray-50 rounded-lg p-3 text-left">
                  <p className="text-xs font-semibold text-gray-700 mb-2">
                    예시 질문:
                  </p>
                  <ul className="text-xs text-gray-600 space-y-1">
                    <li>• 강남역 근처 청년주택 알려줘</li>
                    <li>• 대학가 근처의 집을 찾고 있어</li>
                    <li>• 홍대 근처에 있는 주택은?</li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-sm ${
                      message.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-white text-gray-800 border border-gray-200"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap leading-relaxed text-left">
                      {message.content}
                    </p>

                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <div className="flex items-center gap-1 mb-2 text-left">
                          <FileText className="w-3 h-3 text-gray-500" />
                          <p className="text-xs font-semibold text-gray-600">
                            참고 문서:
                          </p>
                        </div>
                        <div className="space-y-1">
                          {message.sources.map((source, idx) => (
                            <div
                              key={idx}
                              className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1 text-left"
                            >
                              • {source.title} ({source.district})
                              {source.address && (
                                <div className="text-xs text-gray-500 mt-1 text-left">
                                  {source.address}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <p
                      className={`text-xs mt-2 text-left ${
                        message.role === "user"
                          ? "text-blue-200"
                          : "text-gray-500"
                      }`}
                    >
                      {message.timestamp.toLocaleTimeString("ko-KR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </p>
                  </div>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-500 text-left">
                        답변 생성 중...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="메시지를 입력하세요..."
                className="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                rows={2}
                disabled={isLoading}
                maxLength={1000}
              />
              <div className="absolute bottom-2 right-2 text-xs text-gray-400">
                {input.length}/1000
              </div>
            </div>
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2 font-medium shadow-sm"
            >
              <Send className="w-4 h-4" />
              전송
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Enter로 전송 • Shift+Enter로 줄바꿈
          </p>
        </div>
      </div>
    </div>
  );
}
