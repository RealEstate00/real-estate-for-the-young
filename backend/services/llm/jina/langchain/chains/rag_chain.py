"""
RAG Chain Implementation
검색 증강 생성 체인
"""

from langchain.chains import RetrievalQA
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from typing import Dict, Optional, List
import logging

from backend.services.llm.langchain.retrievers.housing_retriever import HousingRetriever
from backend.services.llm.models.model_factory import ModelFactory, ModelType
from backend.services.llm.prompts.prompt_manager import get_prompt_manager

logger = logging.getLogger(__name__)


class HousingRAGChain:
    """
    주택 정보 RAG 체인
    검색된 주택 정보를 기반으로 답변 생성
    """
    
    def __init__(
        self,
        model_type: ModelType = "ollama",
        model_name: Optional[str] = None,
        retriever: Optional[HousingRetriever] = None,
        with_memory: bool = False
    ):
        """
        Initialize RAG Chain
        
        Args:
            model_type: "ollama" or "openai"
            model_name: Specific model name
            retriever: Custom retriever (None for default)
            with_memory: Enable conversation memory
        """
        # Initialize components
        self.llm = ModelFactory.create_llm(
            model_type=model_type,
            model_name=model_name
        )
        
        self.retriever = retriever or HousingRetriever(k=3)
        self.prompt_manager = get_prompt_manager()
        self.with_memory = with_memory
        
        # Create chain
        if with_memory:
            self.chain = self._create_conversational_chain()
        else:
            self.chain = self._create_qa_chain()
        
        logger.info(f"RAG Chain initialized with {model_type}")
    
    def _create_qa_chain(self) -> RetrievalQA:
        """Create simple Q&A chain without memory"""
        qa_prompt = self.prompt_manager.get_qa_prompt()
        
        return RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.retriever.as_langchain_retriever(),
            chain_type="stuff",
            chain_type_kwargs={"prompt": qa_prompt},
            return_source_documents=True
        )
    
    def _create_conversational_chain(self) -> ConversationalRetrievalChain:
        """Create conversational chain with memory"""
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
        
        qa_prompt = self.prompt_manager.get_qa_prompt()
        
        return ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            retriever=self.retriever.as_langchain_retriever(),
            memory=memory,
            return_source_documents=True,
            combine_docs_chain_kwargs={"prompt": qa_prompt}
        )
    
    def ask(self, question: str) -> Dict:
        """
        Ask a question
        
        Args:
            question: User question
            
        Returns:
            {
                "answer": str,
                "sources": List[Dict]
            }
        """
        try:
            if self.with_memory:
                result = self.chain({"question": question})
            else:
                result = self.chain({"query": question})
            
            # Format sources
            sources = []
            if "source_documents" in result:
                for doc in result["source_documents"]:
                    sources.append({
                        "title": doc.metadata.get("주택명", "N/A"),
                        "address": doc.metadata.get("지번주소", "N/A"),
                        "district": doc.metadata.get("시군구", "N/A")
                    })
            
            answer_key = "answer" if self.with_memory else "result"
            
            return {
                "answer": result[answer_key],
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "sources": []
            }
    
    def recommend(
        self,
        location: str,
        budget: str,
        preferences: str
    ) -> Dict:
        """
        Recommend housing based on criteria
        
        Args:
            location: Desired location
            budget: Budget range
            preferences: User preferences
            
        Returns:
            Recommendation response
        """
        # Search for relevant housing
        query = f"{location} 주택 {budget} {preferences}"
        docs = self.retriever.retrieve(query, k=5)
        
        # Format context
        context = "\n\n".join([
            f"주택명: {doc.metadata.get('주택명')}\n"
            f"주소: {doc.metadata.get('지번주소')}\n"
            f"태그: {doc.metadata.get('태그', 'N/A')}"
            for doc in docs
        ])
        
        # Get recommendation prompt
        rec_prompt = self.prompt_manager.get_recommendation_prompt()
        
        # Generate recommendation
        prompt_text = rec_prompt.format(
            context=context,
            location=location,
            budget=budget,
            preferences=preferences
        )
        
        try:
            answer = self.llm.invoke(prompt_text)
            
            # Handle different response types
            if hasattr(answer, 'content'):
                answer_text = answer.content
            else:
                answer_text = str(answer)
            
            return {
                "recommendation": answer_text,
                "candidates": [
                    {
                        "title": doc.metadata.get("주택명"),
                        "address": doc.metadata.get("지번주소"),
                        "district": doc.metadata.get("시군구")
                    }
                    for doc in docs
                ]
            }
            
        except Exception as e:
            logger.error(f"Recommendation failed: {e}")
            return {
                "recommendation": "추천 생성 중 오류가 발생했습니다.",
                "candidates": []
            }


# =============================================================================
# Convenience Functions
# =============================================================================

def create_rag_chain(
    model_type: ModelType = "ollama",
    with_memory: bool = False
) -> HousingRAGChain:
    """
    Create RAG chain with default settings
    
    Args:
        model_type: "ollama" or "openai"
        with_memory: Enable conversation memory
        
    Returns:
        HousingRAGChain instance
    """
    return HousingRAGChain(
        model_type=model_type,
        with_memory=with_memory
    )