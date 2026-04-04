"""
OCR/Vision Module for Chinese Text Extraction from Manual Images
"""
import os
import base64
from typing import Dict, Optional
import dashscope
from dashscope import MultiModalConversation

class ManualTextExtractor:
    """Extract Chinese text from painting manual images"""
    
    def __init__(self, api_key: Optional[str] = None, region: str = "intl"):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        dashscope.api_key = self.api_key
        
        # Set base URL for region
        if region == "intl":
            dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        else:
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    
    def extract_text_from_image(self, image_path_or_bytes) -> Dict:
        """
        Extract Chinese text from manual page image
        
        Args:
            image_path_or_bytes: Path to image file or bytes
            
        Returns:
            Dict with extracted text and metadata
        """
        try:
            # Convert to base64 if needed
            if isinstance(image_path_or_bytes, str):
                with open(image_path_or_bytes, 'rb') as f:
                    image_bytes = f.read()
            else:
                image_bytes = image_path_or_bytes
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Use Tongyi Vision to extract text
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": f"data:image/jpeg;base64,{image_base64}"},
                        {"text": """请仔细分析这张中国画教学图片，提取其中的所有文字内容。

请按以下格式输出：

1. 标题（如果有）
2. 主要说明文字
3. 技法要点（按条列出）

要求：
- 保持原文的准确性
- 保留所有标点符号
- 按原文顺序排列
- 如果有多段文字，请分段输出

请直接输出提取的文字，不要添加其他说明。"""}
                    ]
                }
            ]
            
            response = MultiModalConversation.call(
                model='qwen-vl-max',
                messages=messages
            )
            
            if response.status_code == 200:
                extracted_text = response.output.choices[0].message.content[0]['text']
                
                return {
                    "status": "success",
                    "text": extracted_text,
                    "raw_response": response.output
                }
            else:
                return {
                    "status": "failed",
                    "error": f"API Error: {response.code} - {response.message}"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def extract_text_simple(self, image_bytes) -> str:
        """
        Simple extraction returning just the text string
        
        Args:
            image_bytes: Image as bytes
            
        Returns:
            Extracted text string
        """
        result = self.extract_text_from_image(image_bytes)
        
        if result["status"] == "success":
            return result["text"]
        else:
            return f"Error: {result.get('error', 'Unknown error')}"


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 1:
        extractor = ManualTextExtractor()
        result = extractor.extract_text_from_image(sys.argv[1])
        print(result)
