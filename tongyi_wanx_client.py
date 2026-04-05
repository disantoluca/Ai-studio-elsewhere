"""
Tongyi Wanxiang Client using native DashScope SDK
"""
import os
import time
import dashscope
from dashscope import ImageSynthesis
from typing import Dict, Optional

class TongyiWanxClient:
    """Client for Tongyi Wanxiang"""
    
    def __init__(self, api_key: Optional[str] = None, region: str = "cn"):
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        dashscope.api_key = self.api_key
        
        # Set base URL for region
        if region == "intl":
            dashscope.base_http_api_url = "https://dashscope-intl.aliyuncs.com/api/v1"
        else:
            dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    
    def generate_image(self, prompt: str, negative_prompt: str = "", 
                      seed: int = 12345, size: str = "1024*1024", n: int = 1, 
                      ref_images: list = None) -> Dict:
        """Generate image using Tongyi Wanxiang"""
        
        try:
            # Submit generation task
            rsp = ImageSynthesis.call(
                model="wanx-v1",
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else None,
                n=n,
                size=size,
                seed=seed
            )
            
            if rsp.status_code != 200:
                return {
                    "status": "failed",
                    "error": f"{rsp.code}: {rsp.message}"
                }
            
            # Get task ID
            task_id = rsp.output.task_id
            
            # Poll for result (max 60 seconds)
            for attempt in range(30):
                time.sleep(2)
                
                result = ImageSynthesis.fetch(task_id)
                
                if result.output.task_status == "SUCCEEDED":
                    return {
                        "status": "succeeded",
                        "images": [img.url for img in result.output.results]
                    }
                elif result.output.task_status == "FAILED":
                    return {
                        "status": "failed",
                        "error": result.output.message
                    }
            
            return {"status": "failed", "error": "Timeout waiting for generation"}
            
        except Exception as e:
            return {"status": "failed", "error": str(e)}
