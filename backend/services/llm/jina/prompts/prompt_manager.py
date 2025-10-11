"""
Prompt Template Manager
프롬프트 템플릿 관리 모듈
"""

from langchain.prompts import PromptTemplate, ChatPromptTemplate
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """프롬프트 템플릿 관리 클래스"""
    
    def __init__(self):
        self.templates_dir = Path(__file__).parent / "templates"
        self._templates: Dict[str, str] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load all prompt templates from files"""
        template_files = {
            "system": "system_prompt.txt",
            "qa": "qa_prompt.txt",
            "recommendation": "recommendation_prompt.txt"
        }
        
        for name, filename in template_files.items():
            file_path = self.templates_dir / filename
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._templates[name] = f.read()
                logger.info(f"Loaded template: {name}")
            else:
                logger.warning(f"Template file not found: {filename}")
    
    def get_template(self, name: str) -> Optional[str]:
        """
        Get template by name
        
        Args:
            name: Template name (system, qa, recommendation)
            
        Returns:
            Template string or None
        """
        return self._templates.get(name)
    
    def get_qa_prompt(self) -> PromptTemplate:
        """
        Get Q&A prompt template
        
        Returns:
            LangChain PromptTemplate for Q&A
        """
        template = self.get_template("qa")
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def get_recommendation_prompt(self) -> PromptTemplate:
        """
        Get recommendation prompt template
        
        Returns:
            LangChain PromptTemplate for recommendations
        """
        template = self.get_template("recommendation")
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "location", "budget", "preferences"]
        )
    
    def get_chat_prompt(self) -> ChatPromptTemplate:
        """
        Get chat prompt template with system message
        
        Returns:
            ChatPromptTemplate with system and user messages
        """
        system_template = self.get_template("system")
        qa_template = self.get_template("qa")
        
        return ChatPromptTemplate.from_messages([
            ("system", system_template),
            ("human", qa_template)
        ])


# =============================================================================
# Convenience Functions
# =============================================================================

_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """Get singleton PromptManager instance"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager