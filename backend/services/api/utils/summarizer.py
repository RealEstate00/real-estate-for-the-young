"""
mT5-base를 사용한 텍스트 요약 유틸리티
"""
import logging
import os
from typing import Optional, List, Dict
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from dotenv import load_dotenv
import re

# .env 파일에서 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

# 싱글톤 패턴으로 모델 로드
_summarizer_model = None
_summarizer_tokenizer = None


def get_mt5_summarizer():
    """mT5-base 요약 모델을 싱글톤으로 로드"""
    global _summarizer_model, _summarizer_tokenizer
    
    if _summarizer_model is None or _summarizer_tokenizer is None:
        try:
            model_name = "google/mt5-base"
            device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"🔄 mT5-base 요약 모델 로딩 시작 (디바이스: {device})...")
            
            # HuggingFace 토큰 가져오기 (.env에서 로드)
            hf_token = (
                os.getenv('HF_API_TOKEN') or 
                os.getenv('HF_TOKEN') or 
                os.getenv('HUGGING_FACE_HUB_TOKEN')
            )
            
            if hf_token:
                logger.info("✅ HuggingFace API token 발견됨")
            else:
                logger.warning("⚠️ HuggingFace API token 없음. 일부 모델에 접근하지 못할 수 있습니다.")
            
            tokenizer_kwargs = {"token": hf_token} if hf_token else {}
            model_kwargs = {"token": hf_token} if hf_token else {}
            
            logger.info(f"📥 토크나이저 다운로드 중: {model_name}")
            # T5 계열 모델은 SentencePiece 토크나이저 사용, use_fast=False로 안정적으로 로드
            try:
                _summarizer_tokenizer = AutoTokenizer.from_pretrained(
                    model_name,
                    use_fast=False,  # fast tokenizer 변환 오류 방지
                    **tokenizer_kwargs
                )
            except Exception as e:
                logger.warning(f"Fast tokenizer 로드 실패, slow tokenizer 사용: {e}")
                # T5Tokenizer를 직접 사용하여 안정적으로 로드
                from transformers import T5Tokenizer
                _summarizer_tokenizer = T5Tokenizer.from_pretrained(
                    model_name,
                    **tokenizer_kwargs
                )
            
            logger.info(f"📥 모델 다운로드 중: {model_name}")
            _summarizer_model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                **model_kwargs
            ).to(device)
            
            _summarizer_model.eval()  # 평가 모드
            
            logger.info(f"✅ mT5-base 요약 모델 로딩 완료 (디바이스: {device})")
            
        except Exception as e:
            logger.error(f"❌ mT5-base 요약 모델 로딩 실패: {e}", exc_info=True)
            raise
    
    return _summarizer_model, _summarizer_tokenizer


def summarize_title(text: str, max_length: int = 25) -> str:
    """
    mT5-base를 사용하여 텍스트를 제목 형식으로 요약
    
    Args:
        text: 요약할 텍스트
        max_length: 최대 길이 (문자 수, 기본값 25자)
    
    Returns:
        요약된 제목 (25자 내외)
    """
    logger.info(f"📝 제목 요약 시작: 입력 텍스트 길이 {len(text)}자")
    try:
        if not text or len(text.strip()) == 0:
            logger.warning("⚠️ 요약할 텍스트가 비어있습니다.")
            return ""
        
        # HTML 태그 제거
        clean_text = re.sub(r'<[^>]*>', '', text).strip()
        if not clean_text:
            return ""
        
        # 마크다운 형식 제거
        clean_text = re.sub(r'\*\*', '', clean_text)  # 볼드 제거
        clean_text = re.sub(r'##\s*', '', clean_text)  # 헤더 제거
        clean_text = re.sub(r'#\s*', '', clean_text)  # 헤더 제거
        clean_text = re.sub(r'^\d+\.\s*', '', clean_text, flags=re.MULTILINE)  # 번호 리스트 제거
        clean_text = re.sub(r'\n+', ' ', clean_text)  # 줄바꿈을 공백으로
        clean_text = re.sub(r'\s+', ' ', clean_text)  # 여러 공백을 하나로
        clean_text = clean_text.strip()
        
        # 인사말 및 불필요한 표현 제거
        remove_patterns = [
            r'^안녕하세요[.,]?\s*',
            r'^안녕하세요[.,]?\s*[가-힣\s]*님[.,]?\s*',
            r'^질문[에대한]?\s*[답변안내]+[.:]\s*',
            r'^문서에\s*따르면[.,]?\s*',
            r'^제공된\s*문서[에의하면]*[.,]?\s*',
        ]
        
        for pattern in remove_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        # 괄호 안 내용 제거 
        clean_text = re.sub(r'\([^)]*\)', '', clean_text)
        clean_text = clean_text.strip()
        
        if not clean_text:
            return ""
        
        # 텍스트가 이미 충분히 짧으면 그대로 반환 (약간의 여유를 둠)
        if len(clean_text) <= max_length + 5:
            # 여전히 25자 내외로 조정
            if len(clean_text) > max_length:
                clean_text = clean_text[:max_length]
                last_space = clean_text.rfind(" ")
                if last_space > 15:
                    clean_text = clean_text[:last_space]
            return clean_text
        
        logger.info(f"🤖 mT5-base 모델 호출 준비 중... (정리된 텍스트: {len(clean_text)}자)")
        model, tokenizer = get_mt5_summarizer()
        device = next(model.parameters()).device
        logger.info(f"✅ 모델 준비 완료, 디바이스: {device}")
        
        # mT5에 제목 형식 요약 지시 (명확한 프롬프트)
        # "25자 내외 제목으로 사용 가능하도록, 완전한 제목으로 요약" 지시
        prompt_text = f"""다음 텍스트를 25자 내외의 완전한 제목 형식으로 요약해주세요. 
- 핵심 키워드만 추출하여 제목으로 사용 가능하게
- 중간에 끊기지 않고 완전한 의미의 제목으로
- 사용자 질문 내용은 제외하고 응답 내용만 요약:

{clean_text}"""
        
        # mT5는 text-to-text 모델이므로 "summarize:" 프리픽스 사용
        input_text = f"summarize: {prompt_text}"
        logger.debug(f"📤 프롬프트 길이: {len(input_text)}자")
        
        # 토큰화 (입력이 길 경우 잘라냄)
        max_input_length = 512
        inputs = tokenizer(
            input_text,
            max_length=max_input_length,
            truncation=True,
            padding=True,
            return_tensors="pt"
        ).to(device)
        
        # 제목 생성 (25자 내외로 제한, 완전한 제목으로)
        # max_length는 토큰 수이므로, 한글 기준으로 약 25자 = 약 18-22 토큰
        target_token_length = 22  # 한글 1자 = 약 1-1.2 토큰
        
        with torch.no_grad():
            outputs = model.generate(
                inputs.input_ids,
                max_length=target_token_length,
                min_length=10,  # 최소 토큰 수 (최소 10자 이상 보장)
                num_beams=5,  # 빔 수 증가 (더 나은 후보 탐색)
                early_stopping=True,
                no_repeat_ngram_size=2,
                do_sample=False,
                length_penalty=1.8,  # 적절한 길이 (너무 짧지 않도록)
                repetition_penalty=1.5  # 반복 방지
            )
        
        # 디코딩
        logger.info(f"🔄 모델 생성 완료, 디코딩 중...")
        summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
        summary = summary.strip()
        logger.debug(f"📥 원본 요약 결과: '{summary}' ({len(summary)}자)")
        
        # 불필요한 접두사 제거 ("요약:", "제목:", "답변:" 등)
        summary = re.sub(r'^(요약|제목|답변|응답)[:：]\s*', '', summary, flags=re.IGNORECASE)
        summary = summary.strip()
        logger.debug(f"📝 접두사 제거 후: '{summary}' ({len(summary)}자)")
        
        # 완전한 제목으로 조정 (25자 내외, 중간에 끊기지 않게)
        if len(summary) > max_length:
            # 25자 초과 시 자연스러운 위치에서 자르기
            summary = summary[:max_length]
            
            # 완전한 단어/구로 자르기 위해 자연스러운 끊김 지점 찾기
            # 공백, 구두점, 조사 등에서 끊기
            cut_points = [
                summary.rfind(" "),  # 공백
                summary.rfind("."),   # 마침표
                summary.rfind(","),  # 쉼표
                summary.rfind(":"),  # 콜론
                summary.rfind("에"), # 조사
                summary.rfind("의"), # 조사
                summary.rfind("를"), # 조사
                summary.rfind("을"), # 조사
                summary.rfind("와"), # 조사
                summary.rfind("과"), # 조사
            ]
            
            # 유효한 끊김 지점 중 가장 큰 값 찾기 (최소 12자 이상 유지)
            valid_cut_points = [cp for cp in cut_points if cp >= 12]
            
            if valid_cut_points:
                cut_index = max(valid_cut_points)
                summary = summary[:cut_index].strip()
            else:
                # 끊김 지점이 없으면 공백 기준으로 최대한 길게 유지
                last_space = summary.rfind(" ")
                if last_space >= 10:
                    summary = summary[:last_space].strip()
                else:
                    # 마지막 단어를 포함해서 25자로
                    summary = summary[:max_length].strip()
        
        # 최소 길이 확인 (너무 짧으면 첫 부분 사용)
        if len(summary) < 8:
            # fallback: 첫 25자 사용하되 자연스럽게
            summary = clean_text[:max_length]
            last_space = summary.rfind(" ")
            if last_space > 10:
                summary = summary[:last_space].strip()
        
        logger.info(f"✅ 제목 요약 완료: {len(clean_text)}자 -> {len(summary)}자 - '{summary}'")
        return summary
        
    except Exception as e:
        logger.error(f"Error summarizing text with mT5: {e}", exc_info=True)
        # 실패 시 fallback: 첫 25자 반환 (핵심만 추출)
        try:
            clean_text = re.sub(r'<[^>]*>', '', text).strip()
            clean_text = re.sub(r'\n+', ' ', clean_text)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            # 첫 번째 의미있는 문장이나 25자 추출
            first_sentence = clean_text.split('.')[0].split('!')[0].split('?')[0]
            if len(first_sentence) <= max_length:
                return first_sentence[:max_length]
            else:
                # 핵심 키워드 추출 (25자 내외)
                words = first_sentence.split()
                result = ""
                for word in words:
                    if len(result + word) <= max_length - 1:
                        result += word + " "
                    else:
                        break
                return result.strip()[:max_length]
        except:
            fallback = text[:max_length] if text else ""
            return fallback


def summarize_conversation_batch(messages: List[Dict[str, str]]) -> str:
    """
    mT5-base를 사용하여 대화 내용을 요약하는 함수 (10개 메시지마다 호출)
    
    Args:
        messages: 요약할 메시지 리스트 (role, content 포함)
    
    Returns:
        요약된 대화 내용 (3-5문장)
    """
    logger.info(f"📝 대화 배치 요약 시작: {len(messages)}개 메시지")
    try:
        if not messages or len(messages) == 0:
            logger.warning("⚠️ 요약할 메시지가 없습니다.")
            return ""
        
        # 대화 내용 포맷팅
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                conversation_text += f"사용자: {content}\n"
            elif role == "assistant":
                conversation_text += f"어시스턴트: {content}\n"
        
        conversation_text = conversation_text.strip()
        if not conversation_text:
            logger.warning("⚠️ 포맷팅된 대화 내용이 비어있습니다.")
            return ""
        
        logger.info(f"📋 대화 내용 길이: {len(conversation_text)}자")
        
        # 텍스트 정리 (HTML 태그, 마크다운 제거)
        clean_text = re.sub(r'<[^>]*>', '', conversation_text).strip()
        clean_text = re.sub(r'\*\*', '', clean_text)  # 볼드 제거
        clean_text = re.sub(r'##\s*', '', clean_text)  # 헤더 제거
        clean_text = re.sub(r'#\s*', '', clean_text)  # 헤더 제거
        clean_text = re.sub(r'\n+', ' ', clean_text)  # 줄바꿈을 공백으로
        clean_text = re.sub(r'\s+', ' ', clean_text)  # 여러 공백을 하나로
        clean_text = clean_text.strip()
        
        if not clean_text:
            logger.warning("⚠️ 정리된 대화 내용이 비어있습니다.")
            return ""
        
        logger.info(f"🤖 mT5-base 모델 호출 준비 중... (정리된 텍스트: {len(clean_text)}자)")
        model, tokenizer = get_mt5_summarizer()
        device = next(model.parameters()).device
        logger.info(f"✅ 모델 준비 완료, 디바이스: {device}")
        
        # mT5에 대화 요약 지시 (3-5문장, 핵심 정보 포함)
        prompt_text = f"""다음 대화 내용을 간결하게 요약해주세요. 중요한 정보(이름, 위치, 질문 내용, 답변의 핵심 내용 등)는 반드시 포함하세요.
- 대화의 핵심 내용만 요약
- 사용자의 이름이나 중요한 정보는 반드시 포함
- 질문과 답변의 주요 내용을 간결하게 정리
- 불필요한 인사말이나 반복 내용은 제외
- 3-5문장 정도로 간결하게 작성

대화 내용:
{clean_text}"""
        
        # mT5는 text-to-text 모델이므로 "summarize:" 프리픽스 사용
        input_text = f"summarize: {prompt_text}"
        logger.debug(f"📤 프롬프트 길이: {len(input_text)}자")
        
        # 토큰화 (입력이 길 경우 잘라냄)
        max_input_length = 512
        inputs = tokenizer(
            input_text,
            max_length=max_input_length,
            truncation=True,
            padding=True,
            return_tensors="pt"
        ).to(device)
        
        # 대화 요약 생성 (3-5문장, 약 100-150 토큰)
        # 한글 기준으로 약 100-150자 = 약 80-120 토큰
        target_token_length = 100  # 대화 요약용
        
        with torch.no_grad():
            outputs = model.generate(
                inputs.input_ids,
                max_length=target_token_length,
                min_length=40,  # 최소 토큰 수 (최소 3문장 보장)
                num_beams=5,  # 빔 수 증가 (더 나은 후보 탐색)
                early_stopping=True,
                no_repeat_ngram_size=2,
                do_sample=False,
                length_penalty=1.2,  # 적절한 길이 (너무 짧지 않도록)
                repetition_penalty=1.3  # 반복 방지
            )
        
        # 디코딩
        logger.info(f"🔄 모델 생성 완료, 디코딩 중...")
        summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
        summary = summary.strip()
        logger.debug(f"📥 원본 요약 결과: '{summary}' ({len(summary)}자)")
        
        # 불필요한 접두사 제거 ("요약:", "제목:", "답변:" 등)
        summary = re.sub(r'^(요약|제목|답변|응답|대화)[:：]\s*', '', summary, flags=re.IGNORECASE)
        summary = summary.strip()
        logger.debug(f"📝 접두사 제거 후: '{summary}' ({len(summary)}자)")
        
        # 요약이 너무 짧으면 경고
        if len(summary) < 20:
            logger.warning(f"⚠️ 요약 결과가 너무 짧습니다 ({len(summary)}자). 원본 일부 반환.")
            # Fallback: 첫 100자 반환
            summary = clean_text[:100]
            last_space = summary.rfind(" ")
            if last_space > 50:
                summary = summary[:last_space].strip() + "..."
        
        logger.info(f"✅ 대화 요약 완료: {len(clean_text)}자 -> {len(summary)}자")
        return summary
        
    except Exception as e:
        logger.error(f"❌ 대화 요약 중 오류 발생: {e}", exc_info=True)
        # 실패 시 fallback: 기본 포맷으로 반환
        try:
            fallback_summary = f"[대화 요약 실패] 총 {len(messages)}개의 메시지"
            logger.warning(f"Fallback 요약 사용: {fallback_summary}")
            return fallback_summary
        except:
            return "대화 요약 실패"
