import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, Optional

import requests

from client.model import GetAllVoicesResponse, GetSupportedVoiceModelResponse, DubbingInfoResponse, RemovalInfoResponse, \
    ExtractionInfoResponse, TextTranslationResultResponse


class VoiceCloneNoPermissionError(Exception):
    """Exception raised when user has no permission to clone voice."""
    pass


class AllVoiceLab:
    """
    AllVoiceLab class, encapsulates all API methods, providing a unified interface
    """

    def __init__(self, api_key: str, api_domain: str):
        """
        Initialize AllVoiceLab class
        
        Args:
            api_key: API key
            api_domain: API domain
        """
        self.api_key = api_key
        self.api_domain = api_domain.rstrip('/')
        self.default_output_path = os.path.expanduser("~/Desktop")

    def get_output_path(self, output_path_param: str = None) -> str:
        user_setting_output_path = os.getenv("ALLVOICELAB_BASE_PATH")
        if user_setting_output_path:
            return user_setting_output_path
        else:
            user_setting_output_path = self.default_output_path
        if not output_path_param:
            return user_setting_output_path
        return output_path_param

    def _get_headers(self, content_type: str = "application/json", accept: str = "application/json") -> Dict[str, str]:
        """
        Get request headers
        
        Args:
            content_type: Content type
            
        Returns:
            Request headers dictionary
        """
        headers = {
            "ai-api-key": self.api_key,
            "tt-req-source": "5"
        }
        if content_type and content_type != "":
            headers["Content-Type"] = content_type
        if accept and accept != "":
            headers["Accept"] = accept

        return headers

    def get_all_voices(self, language_code: str = "en") -> Optional[GetAllVoicesResponse]:
        """
        Get all voices
        
        Returns:
            Voice list response object
        """
        # Create HTTP request
        url = f"{self.api_domain}/v1/voices/get_all_voices?language_code={language_code}&show_legacy=true"

        # Send request
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        logging.info(f"get_all_voices response: {response.headers}")
        # Check status code
        if response.status_code != 200:
            logging.error(f"Request failed, status code: {response.status_code}")
            raise Exception(f"Request failed, status code: {response.status_code}")

        # Read response content
        response_data = response.text
        logging.info(response_data)

        # Parse JSON response and convert directly to object
        json_data = json.loads(response_data)
        api_resp = GetAllVoicesResponse.from_dict(json_data)

        return api_resp

    def get_supported_voice_model(self) -> GetSupportedVoiceModelResponse:
        """
        Get supported voice models
        
        Returns:
            Supported voice model response object
        """
        # Create HTTP request
        url = f"{self.api_domain}/v1/voices/get_supported_model"

        # Directly use requests library to send request
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        logging.info(f"get_supported_voice_model response: {response.headers}")
        # Check status code
        if response.status_code != 200:
            # Throw an exception
            logging.error(f"Request failed, status code: {response.status_code}")
            raise Exception(f"Request failed, status code: {response.status_code}")

        # Read response content
        response_data = response.text
        logging.info(response_data)

        # Parse JSON response
        json_data = json.loads(response_data)
        resp = GetSupportedVoiceModelResponse.from_dict(json_data)

        return resp

    def audio_isolation(self, audio_file_path: str, output_dir: str) -> str:
        """
        Send audio file to voice isolation API and save the result locally
        
        Args:
            audio_file_path: Audio file path
            output_dir: Output directory
        
        Returns:
            Saved file path
        """
        # Check if file exists
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_file_path}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Prepare HTTP request
        url = f"{self.api_domain}/v1/audio-isolation/create"

        # Safely open file using with statement
        with open(audio_path, 'rb') as audio_file:
            # Create multipart form data
            files = {
                'audio': (audio_path.name, audio_file)
            }

            # Set request headers
            headers = self._get_headers(content_type="", accept="*/*")

            # Send request
            response = requests.post(url, files=files, headers=headers)
            logging.info(f"audio isolation response: {response.headers}")
            # Check response status
            response.raise_for_status()

            # Try to get filename from response headers
            filename = None
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if filename_match:
                    filename = filename_match.group(1)

            # If filename not obtained from response headers, use original filename with suffix
            if not filename:
                # Get original filename without extension
                original_filename = os.path.splitext(os.path.basename(audio_file_path))[0]
                timestamp = int(time.time())
                random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
                filename = f"{original_filename}_isolation_{timestamp}_{random_suffix}.mp3"

            # Build complete file path
            file_path = output_path / filename

            # Save response content to file
            with open(file_path, 'wb') as f:
                f.write(response.content)

            # Return file path
            return str(file_path)

    def speech_to_speech(self, audio_file_path: str, voice_id_str: str, output_dir: str, similarity: float = 1,
                         remove_background_noise: bool = False) -> str:
        """
        Call API to convert audio to another voice and save locally
        
        Args:
            audio_file_path: Audio file path
            voice_id_str: Voice ID
            output_dir: Output directory
            similarity: Similarity, range [0, 1]
            remove_background_noise: Whether to remove background noise
            
        Returns:
            Saved audio file path
        """
        # Check if file exists
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_file_path}")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Prepare request parameters
        url = f"{self.api_domain}/v1/speech-to-speech/create"

        # Prepare request data
        data = {
            'voice_id': voice_id_str,
            'similarity': str(similarity),
            'remove_background_noise': str(remove_background_noise).lower()
        }

        headers = self._get_headers(content_type="", accept="*/*")

        # Safely open file using with statement
        with open(audio_path, 'rb') as audio_file:
            files = {
                'audio': (audio_path.name, audio_file)
            }

            # Send request
            response = requests.post(url, headers=headers, data=data, files=files)
            logging.info(f"speech to speech response: {response.headers}")
            # Check response status
            response.raise_for_status()

            # Try to get filename from response headers
            filename = None
            content_disposition = response.headers.get('Content-Disposition')
            if content_disposition:
                filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
                if filename_match:
                    filename = filename_match.group(1)

            # If filename not obtained from response headers, use original filename with suffix
            if not filename:
                # Get original filename without extension
                original_filename = os.path.splitext(os.path.basename(audio_file_path))[0]
                timestamp = int(time.time())
                random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
                filename = f"{original_filename}_s2s_{timestamp}_{random_suffix}.mp3"

            # Build complete file path
            file_path = output_path / filename

            # Save response content to file
            with open(file_path, 'wb') as f:
                f.write(response.content)

            # Return file path
            return str(file_path)

    def text_to_speech(self, text: str, voice_id, model_id: str, output_dir: str, speed: float = 1.0) -> str:
        """
        Call API to convert text to speech and save as file

        Args:
            text: Text to convert
            voice_id: Voice ID
            model_id: Model ID
            output_dir: Output directory
            speed: Speech speed

        Returns:
            Saved audio file path
        """
        # Build request body
        request_body = {
            "text": text,
            "language_code": "auto",
            "voice_id": int(voice_id),
            "model_id": model_id,
            "voice_settings": {
                "speed": float(speed)
            }
        }

        # API endpoint
        url = f"{self.api_domain}/v1/text-to-speech/create"

        # Send request and get response
        response = requests.post(
            url=url,
            json=request_body,
            headers=self._get_headers(),
            stream=True  # Use streaming for large files
        )
        logging.info(f"text to speech response: {response.headers}")
        # Check response status
        response.raise_for_status()

        # Try to get filename from response headers
        filename = None
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if filename_match:
                filename = filename_match.group(1)

        # If filename not obtained from response headers, generate a unique filename
        if not filename:
            timestamp = int(time.time())
            random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
            filename = f"tts_{timestamp}_{random_suffix}.mp3"

        # Build complete file path
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / filename

        # Save response content to file
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Return file path
        return str(file_path)

    def add_voice(self, name: str, audio_file_path: str, description: str = None) -> str:
        """
        Add a new voice to your collection of voices
        
        Args:
            name: Voice name
            audio_file_path: Audio file path 
            description: Voice description (optional)
            
        Returns:
            Voice ID 
            
        Raises:
            VoiceCloneNoPermissionError: When user has no permission to clone voice
        """
        # Check if file exists
        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {audio_file_path}")

        # Prepare HTTP request
        url = f"{self.api_domain}/v1/voices/add"

        # Prepare request data
        data = {
            'name': name
        }

        # Add optional description if provided
        if description:
            data['description'] = description

        # Set request headers
        headers = self._get_headers(content_type="", accept="*/*")

        # Safely open file using with statement
        with open(audio_path, 'rb') as audio_file:
            # Create multipart form data
            files = {
                'files': (audio_path.name, audio_file)
            }

            # Send request
            response = requests.post(url, headers=headers, data=data, files=files)
            logging.info(f"Add voice response: {response.headers}")
            if response.status_code != 200 and response.status_code != 422:
                response.raise_for_status()

            # Parse JSON response
            response_data = response.json()
            logging.info(f"Add voice response: {response_data}")

            # Check if there is a permission error
            if isinstance(response_data, dict) and 'detail' in response_data:
                details = response_data.get('detail', [])
                if isinstance(details, list) and len(details) > 0:
                    for detail in details:
                        if isinstance(detail, dict) and detail.get('type') == 'err_voice_clone_no_permission':
                            error_msg = detail.get('msg', 'No permission to clone voice')
                            raise VoiceCloneNoPermissionError(error_msg)

            # Extract voice_id from response
            voice_id = response_data.get('voice_id')
            if not voice_id:
                raise Exception("Failed to get voice_id from response")

            return voice_id

    def dubbing(self, video_file_path: str, target_lang: str, source_lang: str = "auto",
                name: str = None, watermark: bool = True, drop_background_audio: bool = False) -> str:
        """
        Call API to dub a video file and save the result locally
        
        Args:
            video_file_path: Video file path
            target_lang: Target language code (e.g., 'en', 'zh', 'ja', 'fr', 'de', 'ko')
            source_lang: Source language code, default is 'auto'
            name: Project name (optional)
            watermark: Whether to add watermark to the output video
            drop_background_audio: Whether to remove background audio
            
        Returns:
            Dubbing ID
            
        Note:
            Supported video formats: MP3, WAV, MP4, MOV
            Video file size limit: 10MB to 200MB, 2GB
        """
        # Check if file exists
        video_path = Path(video_file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file does not exist: {video_file_path}")

        # Prepare HTTP request
        url = f"{self.api_domain}/v1/videotrans/dubbing"

        # Prepare request data
        data = {
            'target_lang': target_lang
        }

        # Add optional parameters if provided
        if source_lang and source_lang != "auto":
            data['source_lang'] = source_lang

        if name:
            data['name'] = name

        if watermark:
            data['watermark'] = str(watermark).lower()

        if drop_background_audio:
            data['drop_background_audio'] = str(drop_background_audio).lower()

        # Set request headers for multipart/form-data
        headers = self._get_headers(content_type="", accept="*/*")

        # Safely open file using with statement
        with open(video_path, 'rb') as video_file:
            # Create multipart form data
            files = {
                'file': (video_path.name, video_file)
            }

            # Send request
            response = requests.post(url, headers=headers, data=data, files=files)
            
            logging.info(f"Dubbing response: {response.headers}")
            # Check response status
            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()
            logging.info(f"Dubbing response: {response_data}")

            # Extract dubbing_id from response
            dubbing_id = response_data.get('dubbing_id')
            if not dubbing_id:
                raise Exception("Failed to get dubbing_id from response")

            return dubbing_id

    def subtitle_removal(self, video_file_path: str, language_code: str = "auto",
                         name: str = None) -> str:
        """
        Use OCR technology to extract subtitles from video and erase them
        
        Args:
            video_file_path: Video file path
            language_code: Language code for subtitle extraction (e.g., 'zh', 'en'), default is 'auto'
            name: Project name (optional)
            
        Returns:
            Project ID
            
        Note:
            Supported video formats: MP4, MOV
            Video file size limit: 10 seconds to 200 minutes, maximum 2GB
        """
        # Check if file exists
        video_path = Path(video_file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file does not exist: {video_file_path}")

        # Prepare HTTP request
        url = f"{self.api_domain}/v1/videotrans/removal"

        # Prepare request data
        data = {}

        # Add optional parameters if provided
        if language_code and language_code != "auto":
            data['language_code'] = language_code

        if name:
            data['name'] = name

        # Set request headers for multipart/form-data
        headers = self._get_headers(content_type="", accept="*/*")

        # Safely open file using with statement
        with open(video_path, 'rb') as video_file:
            # Create multipart form data
            files = {
                'file': (video_path.name, video_file)
            }

            # Send request
            response = requests.post(url, headers=headers, data=data, files=files)
            logging.info(f"Subtitle removal response: {response.headers}")
            # Check response status
            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()
            logging.info(f"Subtitle removal response: {response_data}")

            # Extract project_id from response
            project_id = response_data.get('project_id')
            if not project_id:
                raise Exception("Failed to get project_id from response")

            return project_id

    def get_dubbing_info(self, dubbing_id: str) -> DubbingInfoResponse:
        """
        Query detailed information of a dubbing project
        
        Args:
            dubbing_id: Dubbing project ID
            
        Returns:
            Dubbing project information response object
            
        Raises:
            Exception: When the request fails
        """
        # Create HTTP request
        url = f"{self.api_domain}/v1/videotrans/dubbing?dubbing_id={dubbing_id}"

        # Send request
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        logging.info(f"get_dubbing_info response: {response.headers}")
        # Check status code
        if response.status_code != 200:
            logging.error(f"get_dubbing_info Request failed, status code: {response.status_code}")
            raise Exception(f"get_dubbing_info Request failed, status code: {response.status_code}")

        # Read response content
        response_data = response.text
        logging.info(response_data)

        # Parse JSON response
        json_data = json.loads(response_data)
        resp = DubbingInfoResponse.from_dict(json_data)

        return resp

    def get_removal_info(self, project_id: str) -> RemovalInfoResponse:
        """
        Query the result of subtitle removal
        
        Args:
            project_id: Subtitle removal project ID
            
        Returns:
            Subtitle removal project information response object
            
        Raises:
            Exception: When the request fails
        """
        # Create HTTP request
        url = f"{self.api_domain}/v1/videotrans/removal?project_id={project_id}"

        # Send request
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        logging.info(f"get_removal_info response: {response.headers}")
        # Check status code
        if response.status_code != 200:
            logging.error(f"get_removal_info Request failed, status code: {response.status_code}")
            raise Exception(f"get_removal_info Request failed, status code: {response.status_code}")

        # Read response content
        response_data = response.text
        logging.info(response_data)

        # Parse JSON response
        json_data = json.loads(response_data)
        resp = RemovalInfoResponse.from_dict(json_data)

        return resp

    def get_dubbing_audio(self, dubbing_id: str, output_dir: str, ori_file_path:str=None) -> str:
        """
        Download the audio file of a dubbing project and save it locally
        
        Args:
            dubbing_id: Dubbing project ID
            output_dir: Output directory
            ori_file_path: Original file path (optional)
            
        Returns:
            Saved file path
            
        Note:
            Video will be returned in MP4 format, pure audio will be returned in MP3 format
        """
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Prepare HTTP request
        url = f"{self.api_domain}/v1/videotrans/dubbing/audio"

        # Prepare request parameters
        params = {
            'dubbing_id': dubbing_id
        }

        # Set request headers, accept all types of responses
        headers = self._get_headers(content_type="", accept="*/*")

        # Send request and get response
        response = requests.get(url, headers=headers, params=params, stream=True)
        logging.info(f"get_dubbing_audio response: {response.headers}")
        # Check response status
        response.raise_for_status()

        # Try to get filename from response headers
        filename = None
        content_disposition = response.headers.get('Content-Disposition')
        if content_disposition:
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            if filename_match:
                filename = filename_match.group(1)

        # If filename not obtained from response headers, generate a filename based on dubbing_id
        if not filename:
            # Determine file extension based on content type
            content_type = response.headers.get('Content-Type', '')
            if 'video' in content_type:
                extension = 'mp4'
            else:
                extension = 'mp3'
            if ori_file_path:
                original_filename = os.path.splitext(os.path.basename(ori_file_path))[0]
                timestamp = int(time.time())
                filename = f"{original_filename}_{timestamp}.{extension}"
            else:
                filename = f"dubbing_{dubbing_id}.{extension}"

        # Build complete file path
        file_path = output_path / filename

        # Save response content to file
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Return file path
        return str(file_path)

    def text_translation(self, file_path: str, target_lang: str, source_lang: Optional[str] = "auto") -> str:
        """
        Translate text from a file.

        Args:
            file_path: Path to the text file (txt, srt).
            target_lang: Target language code (e.g., "zh", "en").
            source_lang: Source language code (e.g., "auto", "en"). Defaults to "auto".

        Returns:
            Project ID for the translation task.
        """
        # Check if file exists
        input_file_path = Path(file_path)
        if not input_file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")

        # Prepare HTTP request
        url = f"{self.api_domain}/v1/text-translation/create"

        files = {
            'file': (input_file_path.name, open(input_file_path, 'rb'), 'text/plain')
        }
        data = {
            'target_lang': target_lang,
            'source_lang': source_lang
        }

        # Send request without Content-Type in headers for multipart/form-data
        response = requests.post(url, headers=self._get_headers(content_type=None), files=files, data=data, timeout=60)
        logging.info(f"text_translation response: {response.headers}")
        # Check status code
        if response.status_code != 200:
            logging.error(f"text_translation Request failed, status code: {response.status_code}, response: {response.text}")
            raise Exception(f"text_translation Request failed, status code: {response.status_code}, response: {response.text}")

        # Read response content
        response_data = response.json()
        logging.info(response_data)

        project_id = response_data.get("project_id")
        if not project_id:
            logging.error(f"Failed to get project_id from response: {response_data}")
            raise Exception(f"Failed to get project_id from response: {response_data}")

        return project_id

    def get_text_translation_result(self, project_id: str) -> Optional[TextTranslationResultResponse]:
        """
        Get text translation result by project_id

        Args:
            project_id: Project ID of the translation task

        Returns:
            TextTranslationResultResponse object or None if an error occurs
        """
        url = f"{self.api_domain}/v1/text-translation/result?project_id={project_id}"

        try:
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            logging.info(f"get_text_translation_result response: {response.headers}")
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            response_data = response.json()
            logging.info(f"get_text_translation_result Text translation result response: {response_data}")

            return TextTranslationResultResponse.from_dict(response_data)

        except requests.exceptions.RequestException as e:
            logging.error(f"get_text_translation_result Request failed for get_text_translation_result: {e}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"get_text_translation_result Failed to decode JSON response for get_text_translation_result: {e}")
            return None
        except Exception as e:
            logging.error(f"get_text_translation_result An unexpected error occurred in get_text_translation_result: {e}")
            return None

    def subtitle_extraction(self, video_file_path: str, language_code: str = "auto",
                            name: str = None) -> str:
        """
        Extract subtitles from video using OCR technology
        
        Args:
            video_file_path: Path to the video file
            language_code: Subtitle language code (e.g., 'zh', 'en'), defaults to 'auto'
            name: Project name (optional)
            
        Returns:
            Project ID (project_id)
            
        Note:
            Supported video formats: MP4, MOV
            Video duration limit: 10 seconds to 200 minutes
            Maximum file size: 2GB
        """
        # 检查文件是否存在
        video_path = Path(video_file_path)
        if not video_path.exists():
            raise FileNotFoundError(f"file not found: {video_file_path}")

        # 准备HTTP请求
        url = f"{self.api_domain}/v1/videotrans/extraction"

        # 准备请求数据
        data = {}

        # 添加可选参数
        if language_code and language_code != "auto":
            data['language_code'] = language_code

        if name:
            data['name'] = name

        # 设置请求头
        headers = self._get_headers(content_type="", accept="*/*")

        # 安全打开文件
        with open(video_path, 'rb') as video_file:
            # 创建multipart表单数据
            files = {
                'file': (video_path.name, video_file)
            }

            # 发送请求
            response = requests.post(url, headers=headers, data=data, files=files)
            logging.info(f"subtitle_extraction response: {response.headers}")
            # 检查响应状态
            response.raise_for_status()

            # 解析JSON响应
            response_data = response.json()
            logging.info(f"Subtitle extraction response: {response_data}")

            # 提取project_id
            project_id = response_data.get('project_id')
            if not project_id:
                raise Exception("Unable to retrieve project_id from the response")

            return project_id

    def get_extraction_info(self, project_id: str) -> ExtractionInfoResponse:
        """
        Query subtitle extraction results

        Args:
            project_id: Subtitle extraction project ID

        Returns:
            Subtitle extraction project information response object

        Raises:
            Exception: Raised when the request fails
        """
        # 创建HTTP请求
        url = f"{self.api_domain}/v1/videotrans/extraction?project_id={project_id}"

        # 发送请求
        response = requests.get(url, headers=self._get_headers(), timeout=30)
        logging.info(f"get_extraction_info response: {response.headers}")
        # 检查状态码
        if response.status_code != 200:
            logging.error(f"get_extraction_info Request failed, status code: {response.status_code}")
            raise Exception(f"Request failed, status code: {response.status_code}")

        # 读取响应内容
        response_data = response.text
        logging.info(response_data)

        # 解析JSON响应
        json_data = json.loads(response_data)
        resp = ExtractionInfoResponse.from_dict(json_data)

        return resp
