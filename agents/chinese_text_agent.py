#!/usr/bin/env python3
"""
Chinese Text Expert Agent
A bilingual agent specializing in Chinese language processing, translation, and cultural context.
Uses Qwen3 model for high-quality Chinese-English understanding.
"""

import json
import os
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
except ImportError:
    print("Required packages not installed. Please run: pip install transformers torch accelerate")
    sys.exit(1)

# ===========================================
# Load .env reliably (NO auto-detection)
# ===========================================
try:
    from dotenv import load_dotenv
except ImportError:
    print("⚠️ python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Proceeding without .env support...")
    load_dotenv = None

if load_dotenv is not None:
    # Determine absolute path to .env file
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ENV_PATH = os.path.join(BASE_DIR, ".env")
    print(f"🔍 Loading .env from: {ENV_PATH}")
    if os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH)
        print("✅ .env file loaded successfully")
    else:
        print("⚠️ .env file not found — Environment variables will use system defaults!")
else:
    print("⚠️ Skipping .env loading — install python-dotenv for environment variable support")


@dataclass
class AgentResponse:
    """Structured response from the Chinese Text Expert Agent"""
    content: str
    content_zh: Optional[str] = None
    content_en: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        if self.metadata is None:
            self.metadata = {}


class ChineseTextExpertAgent:
    """
    Chinese Text Expert Agent using Qwen3
    
    Capabilities:
    - Chinese-English translation
    - Text analysis and refinement
    - Cultural context explanation
    - Idiom interpretation
    - Bilingual instruction generation
    """
    
    def __init__(self, config_path: str = "agent_config.json"):
        """Initialize the agent with configuration"""
        self.config = self._load_config(config_path)
        self.model = None
        self.tokenizer = None
        self.conversation_history = []
        
        print("🚀 Initializing Chinese Text Expert Agent...")
        print("⚠️ Skipping Qwen-30B load (using OpenAI-only mode).")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load agent configuration"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_model(self):
        """Stub: Model loading disabled (using OpenAI-only mode)"""
        print("⚠️ Model loading skipped (OpenAI-only mode active)")
        return
    
    def _build_prompt(self, text: str, task: str = "general", context: Dict = None) -> str:
        """Build a bilingual prompt based on task type"""
        
        system_prompt_en = self.config['system_prompt']['en']
        system_prompt_zh = self.config['system_prompt']['zh']
        
        prompts = {
            "translate": f"""Task: Translate the following text accurately, maintaining tone and cultural nuances.
任务：准确翻译以下文本，保持语气和文化细微差别。

Text to translate / 待翻译文本:
{text}

Provide:
1. Translation / 译文
2. Key cultural notes if applicable / 文化注释（如适用）
""",
            
            "explain": f"""Task: Explain the meaning, cultural context, and usage of this Chinese text or idiom.
任务：解释这段中文或成语的含义、文化背景和用法。

Text / 文本:
{text}

Provide bilingual explanation covering:
请提供双语解释，包括：
1. Literal meaning / 字面意思
2. Figurative meaning / 比喻意义
3. Cultural context / 文化背景
4. Usage examples / 使用示例
""",
            
            "analyze": f"""Task: Analyze this Chinese text for tone, style, and linguistic features.
任务：分析这段中文的语气、风格和语言特征。

Text / 文本:
{text}

Provide bilingual analysis:
请提供双语分析：
1. Tone and style / 语气和风格
2. Key linguistic features / 主要语言特征
3. Target audience / 目标读者
4. Suggestions for improvement / 改进建议
""",
            
            "ocr_review": f"""Task: Review this OCR-extracted Chinese text and provide corrections.
任务：审查这段OCR提取的中文文本并提供修正。

OCR Text / OCR文本:
{text}

Context / 背景: {json.dumps(context, ensure_ascii=False) if context else 'None'}

Provide:
请提供：
1. Corrected text / 修正后的文本
2. List of corrections made / 修改列表
3. Confidence assessment / 置信度评估
""",
            
            "general": f"""Text / 文本:
{text}

Please process this text and provide your expert analysis in both Chinese and English.
请处理这段文本并用中英文提供专家分析。
"""
        }
        
        return prompts.get(task, prompts["general"])
    
    def process(self, text: str, task: str = "general", context: Dict = None) -> AgentResponse:
        """
        Process text with the specified task
        
        Args:
            text: Input text (Chinese or English)
            task: Task type ('translate', 'explain', 'analyze', 'ocr_review', 'general')
            context: Optional context dictionary
        
        Returns:
            AgentResponse with bilingual content
        """
        if self.model is None:
            self.load_model()
        
        # Build prompt
        prompt = self._build_prompt(text, task, context)
        
        # Generate response
        print(f"🤔 Processing task: {task}")
        response_text = self._generate_response(prompt)
        
        # Parse bilingual content if possible
        content_zh, content_en = self._extract_bilingual(response_text)
        
        # Build response
        response = AgentResponse(
            content=response_text,
            content_zh=content_zh,
            content_en=content_en,
            metadata={
                "task": task,
                "model": self.config['model']['model_name'],
                "context": context
            }
        )
        
        # Save to conversation history
        self.conversation_history.append({
            "timestamp": response.timestamp,
            "input": text,
            "task": task,
            "output": response_text
        })
        
        return response
    
    def _generate_response(self, prompt: str) -> str:
        """Generate response using OpenAI (Qwen model skipped in OpenAI-only mode)"""
        try:
            # Use OpenAI for generation (since Qwen model is not loaded)
            import os
            api_key = os.environ.get("OPENAI_API_KEY")
            
            if not api_key:
                return "⚠️ Error: OPENAI_API_KEY not set. Please set your OpenAI API key."
            
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            messages = [
                {"role": "system", "content": self.config['system_prompt']['en']},
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=self.config['model']['max_tokens'],
                temperature=self.config['model']['temperature']
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
            print(f"❌ Error generating response: {error_msg}")
            return f"Error: {error_msg}"
    
    def _extract_bilingual(self, text: str) -> tuple:
        """Extract Chinese and English content from response"""
        # Simple extraction - can be enhanced with more sophisticated parsing
        content_zh = None
        content_en = None
        
        # Try to find sections marked with language indicators
        lines = text.split('\n')
        current_lang = None
        zh_lines = []
        en_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if 'chinese' in line_lower or '中文' in line or '译文' in line:
                current_lang = 'zh'
            elif 'english' in line_lower or '英文' in line:
                current_lang = 'en'
            elif line.strip():
                if current_lang == 'zh':
                    zh_lines.append(line)
                elif current_lang == 'en':
                    en_lines.append(line)
        
        if zh_lines:
            content_zh = '\n'.join(zh_lines)
        if en_lines:
            content_en = '\n'.join(en_lines)
        
        return content_zh, content_en
    
    def save_conversation(self, filename: str = None):
        """Save conversation history to file"""
        if filename is None:
            filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_history, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Conversation saved to: {filename}")


def main():
    """Main function for testing the agent"""
    print("=" * 60)
    print("🇨🇳 Chinese Text Expert Agent 中文文本专家")
    print("=" * 60)
    
    # Initialize agent
    agent = ChineseTextExpertAgent()
    
    # Example usage
    examples = [
        {
            "text": "人工智能正在改变世界",
            "task": "translate",
            "description": "Translation example"
        },
        {
            "text": "塞翁失马，焉知非福",
            "task": "explain",
            "description": "Idiom explanation"
        }
    ]
    
    for example in examples:
        print(f"\n{'='*60}")
        print(f"📝 Example: {example['description']}")
        print(f"{'='*60}")
        print(f"Input: {example['text']}")
        print(f"Task: {example['task']}")
        print()
        
        response = agent.process(example['text'], task=example['task'])
        
        print("Response:")
        print(response.content)
        print()
    
    # Save conversation
    agent.save_conversation()


if __name__ == "__main__":
    main()
