import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  RotateCcw,
  Home,
  FileText,
  Square,
  History,
  X,
  ChevronLeft,
  ChevronRight,
  GripVertical,
} from "lucide-react";
import { chat, clearMemory, ChatMessage, SourceInfo } from "../services/llmApi";

interface Message extends ChatMessage {
  timestamp: Date;
  sources?: SourceInfo[];
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

// 마크다운 처리 함수
const formatMessage = (text: string | undefined | null) => {
  // undefined나 null인 경우 빈 문자열 반환
  if (!text) {
    return "";
  }

  return (
    text
      // 헤더 처리 (## 헤더) - 섹션 간 간격을 크게, 제목-내용 간격은 작게
      .replace(
        /^##\s+(.+)$/gm,
        '<h2 class="text-2xl font-bold text-gray-900 mb-0 mt-4 leading-tight">$1</h2>'
      )
      .replace(
        /^###\s+(.+)$/gm,
        '<h3 class="text-xl font-bold text-gray-900 mb-0 mt-4 leading-tight">$1</h3>'
      )
      // 번호 리스트 형식 처리 (섹션 간 간격을 크게 설정, 제목-내용 간격은 매우 작게)
      .replace(
        /\*\*(\d+)\.\s+(.+?)\*\*/g,
        '<h3 class="text-xl font-bold text-gray-900 mb-0 mt-5 leading-tight">$1. $2</h3>'
      )
      .replace(
        /\*\*(\d+)\.\s+\[(.+?)\]\*\*/g,
        '<h3 class="text-xl font-bold text-gray-900 mb-0 mt-5 leading-tight">$1. [$2]</h3>'
      )
      // 테이블 형식 처리
      .replace(
        /\| \*\*(.*?)\*\* \|/g,
        '<div class="font-bold text-gray-800 mt-4 mb-2 text-lg leading-relaxed">| $1 |</div>'
      )
      // 볼드 처리
      .replace(/\*\*(.*?)\*\*/g, "<strong class='font-semibold'>$1</strong>")
      // 줄바꿈
      .replace(/\n/g, "<br />")
  );
};

const CONVERSATIONS_STORAGE_KEY = "chat_conversations";
const CURRENT_CONVERSATION_ID_KEY = "current_conversation_id";
const SIDEBAR_WIDTH_KEY = "sidebar_width";
const SIDEBAR_COLLAPSED_KEY = "sidebar_collapsed";

const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 600;
const DEFAULT_SIDEBAR_WIDTH = 320;

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [abortController, setAbortController] =
    useState<AbortController | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<
    string | null
  >(null);
  const [conversationTitle, setConversationTitle] = useState<string | null>(
    null
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem(SIDEBAR_WIDTH_KEY);
    return saved ? parseInt(saved, 10) : DEFAULT_SIDEBAR_WIDTH;
  });
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
    return saved === "true";
  });
  const [isResizing, setIsResizing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const sidebarRef = useRef<HTMLDivElement>(null);
  const isInitialLoadRef = useRef(true);
  const isSelectingConversationRef = useRef(false);
  const savedConversationIdRef = useRef<string | null>(null);

  // 사이드바 너비 저장
  useEffect(() => {
    localStorage.setItem(SIDEBAR_WIDTH_KEY, sidebarWidth.toString());
  }, [sidebarWidth]);

  // 사이드바 접힘 상태 저장
  useEffect(() => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, sidebarCollapsed.toString());
  }, [sidebarCollapsed]);

  // 리사이즈 핸들러
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;

      const newWidth = e.clientX;
      const clampedWidth = Math.max(
        MIN_SIDEBAR_WIDTH,
        Math.min(MAX_SIDEBAR_WIDTH, newWidth)
      );
      setSidebarWidth(clampedWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";

      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };
    }
  }, [isResizing]);

  // 대화 기록 로드
  useEffect(() => {
    const savedConversations = localStorage.getItem(CONVERSATIONS_STORAGE_KEY);
    const savedCurrentId = localStorage.getItem(CURRENT_CONVERSATION_ID_KEY);

    if (savedConversations) {
      const parsed = JSON.parse(savedConversations).map((conv: any) => ({
        ...conv,
        createdAt: new Date(conv.createdAt),
        updatedAt: new Date(conv.updatedAt),
        messages: conv.messages.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        })),
      }));
      setConversations(parsed);

      if (savedCurrentId) {
        const conv = parsed.find((c: Conversation) => c.id === savedCurrentId);
        if (conv) {
          setMessages(conv.messages);
          setCurrentConversationId(savedCurrentId);
          savedConversationIdRef.current = savedCurrentId;
        }
      }
    }

    isInitialLoadRef.current = false;
  }, []);

  // 대화 기록 저장 (conversationTitle 변경 시에도 재실행)
  useEffect(() => {
    // 초기 로드 중이거나 대화 선택 중이면 저장하지 않음
    if (isInitialLoadRef.current || isSelectingConversationRef.current) {
      return;
    }

    if (messages.length > 0) {
      setConversations((prevConversations) => {
        // 현재 대화 ID 결정 (기존 ID가 없으면 생성, 단 중복 방지)
        let conversationId = currentConversationId;

        if (!conversationId) {
          // 새 대화인 경우 고유 ID 생성 (타임스탬프 + 랜덤 문자열)
          conversationId = `${Date.now()}-${Math.random()
            .toString(36)
            .substr(2, 9)}`;
          savedConversationIdRef.current = conversationId;
        }

        // 기존 대화 찾기
        const existingConv = prevConversations.find(
          (c) => c.id === conversationId
        );

        // 동일한 ID의 대화가 이미 있고 메시지가 같으면 업데이트하지 않음
        if (
          existingConv &&
          JSON.stringify(existingConv.messages) === JSON.stringify(messages)
        ) {
          return prevConversations;
        }

        // 제목 생성: 백엔드에서 제공한 title 사용 (mT5 요약) 또는 fallback
        const generateTitle = (msgs: Message[]): string => {
          // 백엔드에서 제공한 제목 우선 사용
          if (conversationTitle) {
            return conversationTitle;
          }

          // Fallback: 첫 번째 사용자 메시지 사용 (25자로 제한)
          const firstUserMessage = msgs.find((m) => m.role === "user");
          if (firstUserMessage) {
            const userContent = firstUserMessage.content.slice(0, 25);
            // 자연스러운 끊김 지점 찾기
            if (userContent.length >= 25) {
              const lastSpace = userContent.lastIndexOf(" ");
              if (lastSpace > 10) {
                return userContent.substring(0, lastSpace).trim();
              }
            }
            return userContent;
          }
          return "새 대화";
        };

        // 답변이 완료된 경우에만 대화 기록 생성/업데이트
        const hasAssistantResponse = messages.some(
          (m) => m.role === "assistant"
        );

        // assistant 응답이 없으면 대화 기록을 생성하지 않음 (질문만 있고 답변이 없는 경우)
        if (!hasAssistantResponse && !existingConv) {
          return prevConversations;
        }

        const conversation: Conversation = existingConv
          ? {
              ...existingConv,
              messages,
              updatedAt: new Date(),
              title: hasAssistantResponse
                ? generateTitle(messages)
                : existingConv.title || "새 대화",
            }
          : {
              id: conversationId,
              title: hasAssistantResponse ? generateTitle(messages) : "새 대화",
              messages,
              createdAt: new Date(),
              updatedAt: new Date(),
            };

        // 대화 목록 업데이트 (중복 제거 포함)
        let updatedConversations: Conversation[];
        if (existingConv) {
          // 기존 대화 업데이트
          updatedConversations = prevConversations.map((c) =>
            c.id === conversationId ? conversation : c
          );
        } else {
          // 새 대화 추가 (중복 체크)
          const exists = prevConversations.some((c) => c.id === conversationId);
          if (!exists) {
            updatedConversations = [
              conversation,
              ...prevConversations.filter((c) => c.id !== conversationId),
            ];
          } else {
            // 이미 존재하면 업데이트만
            updatedConversations = prevConversations.map((c) =>
              c.id === conversationId ? conversation : c
            );
          }
        }

        localStorage.setItem(
          CONVERSATIONS_STORAGE_KEY,
          JSON.stringify(updatedConversations)
        );
        localStorage.setItem(CURRENT_CONVERSATION_ID_KEY, conversation.id);

        // currentConversationId 업데이트 (한 번만)
        if (!currentConversationId) {
          setTimeout(() => {
            setCurrentConversationId(conversation.id);
          }, 0);
        }

        return updatedConversations;
      });
    }
  }, [messages, currentConversationId, conversationTitle]); // conversationTitle 변경 시에도 재실행

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

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInput("");
    setIsLoading(true);

    // AbortController 생성
    const controller = new AbortController();
    setAbortController(controller);

    try {
      // 대화 기록을 백엔드로 전송 (메시지 배열 형태)
      const chatMessages: ChatMessage[] = updatedMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await chat(chatMessages, "ollama", controller.signal);

      const aiMessage: Message = {
        role: "assistant",
        content: response.message,
        sources:
          response.sources && response.sources.length > 0
            ? [response.sources[0]]
            : [],
        timestamp: new Date(),
      };

      setMessages((prev) => {
        const updated = [...prev, aiMessage];

        // 백엔드에서 제공한 제목이 있고, 첫 번째 응답인 경우에만 제목 저장
        if (response.title && prev.length === 1) {
          // 첫 질문(prev) + 답변(aiMessage) = 2개
          // 제목을 상태에 저장 (대화 기록 저장 시 사용)
          console.log("✅ 백엔드에서 받은 제목:", response.title);
          setConversationTitle(response.title);
        } else if (prev.length === 1) {
          // 첫 응답인데 제목이 없는 경우 경고
          console.warn("⚠️ 첫 번째 응답이지만 백엔드에서 제목을 받지 못했습니다.", {
            hasTitle: !!response.title,
            responseKeys: Object.keys(response),
            messageLength: prev.length
          });
        }

        return updated;
      });
    } catch (error: any) {
      console.error("Chat error:", error);

      // AbortError는 사용자가 중단한 것이므로 에러 메시지 표시 안 함
      if (error.name === "AbortError") {
        return;
      }

      // 상세한 에러 메시지 생성
      let errorMessageText = "죄송합니다. 응답 중 오류가 발생했습니다.";
      if (error instanceof Error) {
        if (
          error.message.includes("Failed to fetch") ||
          error.message.includes("NetworkError")
        ) {
          errorMessageText =
            "서버에 연결할 수 없습니다. API 서버가 실행 중인지 확인해주세요.\n(API 서버: http://localhost:8000)";
        } else if (error.message.includes("HTTP error")) {
          errorMessageText = `서버 오류가 발생했습니다: ${error.message}`;
        } else {
          errorMessageText = `오류: ${error.message}`;
        }
      }

      const errorMessage: Message = {
        role: "assistant",
        content: errorMessageText,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  };

  const handleStop = () => {
    if (abortController) {
      abortController.abort();
      setIsLoading(false);
      setAbortController(null);
    }
  };

  const handleClearChat = async () => {
    if (window.confirm("대화 내역을 모두 삭제하시겠습니까?")) {
      try {
        await clearMemory("ollama");
        setMessages([]);
        setCurrentConversationId(null);
        localStorage.removeItem(CURRENT_CONVERSATION_ID_KEY);
      } catch (error) {
        console.error("Failed to clear chat:", error);
        setMessages([]);
        setCurrentConversationId(null);
        localStorage.removeItem(CURRENT_CONVERSATION_ID_KEY);
      }
    }
  };

  const handleNewConversation = () => {
    isSelectingConversationRef.current = true;
    setMessages([]);
    setCurrentConversationId(null);
    setConversationTitle(null); // 제목 초기화
    savedConversationIdRef.current = null;
    localStorage.removeItem(CURRENT_CONVERSATION_ID_KEY);
    setSidebarOpen(false);
    // 다음 렌더링 사이클에서 플래그 해제
    setTimeout(() => {
      isSelectingConversationRef.current = false;
    }, 100);
  };

  const handleSelectConversation = (conversation: Conversation) => {
    isSelectingConversationRef.current = true;
    // 메시지를 깊은 복사하여 참조 문제 방지
    setMessages([
      ...conversation.messages.map((msg) => ({
        ...msg,
        timestamp: new Date(msg.timestamp),
      })),
    ]);
    setCurrentConversationId(conversation.id);
    savedConversationIdRef.current = conversation.id;
    localStorage.setItem(CURRENT_CONVERSATION_ID_KEY, conversation.id);
    setSidebarOpen(false);
    // 다음 렌더링 사이클에서 플래그 해제
    setTimeout(() => {
      isSelectingConversationRef.current = false;
    }, 100);
  };

  const handleDeleteConversation = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm("이 대화를 삭제하시겠습니까?")) {
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);
      localStorage.setItem(CONVERSATIONS_STORAGE_KEY, JSON.stringify(updated));

      if (currentConversationId === id) {
        handleNewConversation();
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleToggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  };

  return (
    <div className="flex h-screen bg-gray-50" style={{ fontSize: "1.1em" }}>
      {/* Sidebar */}
      {!sidebarCollapsed && (
        <div
          ref={sidebarRef}
          className={`${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          } fixed md:relative md:translate-x-0 z-30 bg-white border-r border-gray-200 flex flex-col h-full transition-transform duration-300 ease-in-out shadow-lg md:shadow-none relative`}
          style={{ width: `${sidebarWidth}px` }}
        >
          {/* 리사이즈 핸들 */}
          <div
            onMouseDown={handleResizeStart}
            className="absolute right-0 top-0 w-1 h-full cursor-col-resize hover:bg-blue-300 transition-colors z-10 group"
          >
            <div className="absolute right-0 top-1/2 -translate-y-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
              <GripVertical className="w-4 h-4 text-gray-400" />
            </div>
          </div>

          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
              <History className="w-5 h-5" />
              대화 기록
            </h2>
            <div className="flex items-center gap-2">
              <button
                onClick={handleToggleSidebar}
                className="hidden md:flex text-gray-500 hover:text-gray-700 transition-colors"
                title="사이드바 접기"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => setSidebarOpen(false)}
                className="md:hidden text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            <button
              onClick={handleNewConversation}
              className="w-full mb-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium flex items-center justify-center gap-2"
            >
              <Send className="w-4 h-4" />새 대화 시작
            </button>
            <div className="space-y-2">
              {conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  onClick={() => handleSelectConversation(conversation)}
                  className={`p-3 rounded-lg cursor-pointer transition-colors relative group ${
                    currentConversationId === conversation.id
                      ? "bg-blue-50 border border-blue-200"
                      : "bg-gray-50 hover:bg-gray-100 border border-transparent"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">
                        {conversation.title}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {conversation.messages.length}개 메시지
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {conversation.updatedAt.toLocaleDateString("ko-KR", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                    <button
                      onClick={(e) =>
                        handleDeleteConversation(conversation.id, e)
                      }
                      className="ml-2 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-opacity"
                      title="삭제"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
              {conversations.length === 0 && (
                <div className="text-center py-8 text-gray-500 text-sm">
                  대화 기록이 없습니다
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 접힌 사이드바 토글 버튼 */}
      {sidebarCollapsed && (
        <button
          onClick={handleToggleSidebar}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-30 bg-white border-r border-t border-b border-gray-200 rounded-r-lg p-2 shadow-lg hover:bg-gray-50 transition-colors hidden md:flex items-center justify-center"
          title="사이드바 펼치기"
        >
          <ChevronRight className="w-5 h-5 text-gray-600" />
        </button>
      )}

      {/* Sidebar Overlay (모바일) */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
          <div className="px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
              <button
                onClick={() => setSidebarOpen(true)}
                className="md:hidden text-gray-600 hover:text-gray-800"
              >
                <History className="w-6 h-6" />
              </button>
              {sidebarCollapsed && (
                <button
                  onClick={handleToggleSidebar}
                  className="hidden md:flex text-gray-600 hover:text-gray-800"
                  title="사이드바 펼치기"
                >
                  <ChevronRight className="w-6 h-6" />
                </button>
              )}
              <Home className="w-6 h-6 text-blue-600 hidden md:block" />
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
              <span className="hidden md:inline">대화 초기화</span>
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
                      <li>• 청년 월세 지원금을 알고 싶어</li>
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
                    <div
                      className="text-sm leading-relaxed text-left"
                      dangerouslySetInnerHTML={{
                        __html: formatMessage(message.content),
                      }}
                    />

                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-200">
                        <div className="flex items-center gap-1 mb-2 text-left">
                          <FileText className="w-3 h-3 text-gray-500" />
                          <p className="text-xs font-semibold text-gray-600">
                            참고 문서:
                          </p>
                        </div>
                        {/* 상위 1개 source만 표시 */}
                        {message.sources[0] && (
                          <div className="text-xs text-gray-600 bg-gray-50 rounded px-2 py-1 text-left">
                              • {message.sources[0].title}
                              {message.sources[0].district && (
                                <span> ({message.sources[0].district})</span>
                              )}
                            {message.sources[0].address && (
                              <div className="text-xs text-gray-500 mt-1 text-left">
                                {message.sources[0].address}
                              </div>
                            )}
                          </div>
                        )}
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
              {isLoading ? (
                <button
                  onClick={handleStop}
                  className="px-6 py-3 bg-orange-500 text-white rounded-xl hover:bg-orange-600 transition-colors flex items-center gap-2 font-medium shadow-sm"
                >
                  <Square className="w-4 h-4" />
                  중지
                </button>
              ) : (
            <button
              onClick={handleSend}
                  disabled={!input.trim()}
              className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center gap-2 font-medium shadow-sm"
            >
              <Send className="w-4 h-4" />
              전송
            </button>
              )}
          </div>
          <p className="text-xs text-gray-500 mt-2 text-center">
            Enter로 전송 • Shift+Enter로 줄바꿈
          </p>
          </div>
        </div>
      </div>
    </div>
  );
}
