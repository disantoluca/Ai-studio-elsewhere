#!/usr/bin/env python3
"""
Video Translator/Dubber and Subtitler Agent
Using AllVoiceLab MCP for comprehensive video processing capabilities

Features:
- Video translation and dubbing to multiple languages
- Subtitle extraction from videos using OCR
- Subtitle removal from videos
- Text-to-speech conversion
- Voice cloning and conversion
- Background noise removal

Author: Video Processing Agent
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/lucadisanto/video_translator_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SupportedLanguages(Enum):
    """Supported languages for translation and voice synthesis"""
    ENGLISH = "en"
    CHINESE = "zh"
    JAPANESE = "ja"
    FRENCH = "fr"
    GERMAN = "de"
    KOREAN = "ko"
    SPANISH = "es"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    RUSSIAN = "ru"
    ARABIC = "ar"
    HINDI = "hi"

class VideoFormats(Enum):
    """Supported video formats"""
    MP4 = ".mp4"
    MOV = ".mov"
    AVI = ".avi"
    MKV = ".mkv"

class AudioFormats(Enum):
    """Supported audio formats"""
    MP3 = ".mp3"
    WAV = ".wav"
    M4A = ".m4a"
    FLAC = ".flac"

@dataclass
class TranslationTask:
    """Data class for tracking translation tasks"""
    task_id: str
    input_file: str
    target_language: str
    source_language: str = "auto"
    task_type: str = "dubbing"  # dubbing, subtitle_extraction, subtitle_removal
    status: str = "pending"
    output_file: Optional[str] = None
    created_at: str = ""

class VideoTranslatorAgent:
    """
    Comprehensive Video Translation and Subtitling Agent

    This agent provides a complete suite of video processing capabilities:
    - Multi-language video dubbing and translation
    - Subtitle extraction and translation
    - Subtitle removal from videos
    - Voice cloning and conversion
    - Text-to-speech synthesis
    """

    def __init__(self, api_key: str, api_domain: str = "https://api.allvoicelab.com", output_dir: str = None):
        """
        Initialize the Video Translator Agent

        Args:
            api_key: AllVoiceLab API key
            api_domain: API domain (global: https://api.allvoicelab.com, China: https://api.allvoicelab.cn)
            output_dir: Directory for output files (default: user's desktop)
        """
        self.api_key = api_key
        self.api_domain = api_domain
        self.output_dir = output_dir or os.path.join(os.path.expanduser("~"), "Desktop", "VideoTranslator")

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Task tracking
        self.active_tasks: Dict[str, TranslationTask] = {}
        self.task_history_file = os.path.join(self.output_dir, "task_history.json")

        # Load task history
        self._load_task_history()

        logger.info(f"Video Translator Agent initialized with output directory: {self.output_dir}")

    def _load_task_history(self):
        """Load task history from file"""
        try:
            if os.path.exists(self.task_history_file):
                with open(self.task_history_file, 'r') as f:
                    data = json.load(f)
                    for task_data in data.get('tasks', []):
                        task = TranslationTask(**task_data)
                        self.active_tasks[task.task_id] = task
                logger.info(f"Loaded {len(self.active_tasks)} tasks from history")
        except Exception as e:
            logger.error(f"Error loading task history: {e}")

    def _save_task_history(self):
        """Save task history to file"""
        try:
            data = {
                'tasks': [task.__dict__ for task in self.active_tasks.values()]
            }
            with open(self.task_history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving task history: {e}")

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return [lang.value for lang in SupportedLanguages]

    def get_supported_video_formats(self) -> List[str]:
        """Get list of supported video formats"""
        return [fmt.value for fmt in VideoFormats]

    def get_supported_audio_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return [fmt.value for fmt in AudioFormats]

    def validate_file_format(self, file_path: str, allowed_formats: List[str]) -> bool:
        """Validate if file format is supported"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in allowed_formats

    def validate_file_size(self, file_path: str, max_size_gb: float = 2.0) -> bool:
        """Validate file size (default max 2GB for videos)"""
        try:
            file_size = os.path.getsize(file_path)
            max_size_bytes = max_size_gb * 1024 * 1024 * 1024  # Convert GB to bytes
            return file_size <= max_size_bytes
        except OSError:
            return False

    def create_claude_desktop_config(self) -> str:
        """
        Generate Claude Desktop configuration for AllVoiceLab MCP

        Returns:
            JSON configuration string for Claude Desktop
        """
        config = {
            "mcpServers": {
                "AllVoiceLab": {
                    "command": "uvx",
                    "args": ["allvoicelab-mcp"],
                    "env": {
                        "ALLVOICELAB_API_KEY": self.api_key,
                        "ALLVOICELAB_API_DOMAIN": self.api_domain,
                        "ALLVOICELAB_BASE_PATH": self.output_dir
                    }
                }
            }
        }

        config_str = json.dumps(config, indent=2)

        # Save to file
        config_file = os.path.join(self.output_dir, "claude_desktop_config.json")
        with open(config_file, 'w') as f:
            f.write(config_str)

        logger.info(f"Claude Desktop configuration saved to: {config_file}")
        return config_str

    def create_mcp_installation_script(self) -> str:
        """
        Create installation script for AllVoiceLab MCP

        Returns:
            Path to the installation script
        """
        script_content = f"""#!/bin/bash
# AllVoiceLab MCP Installation Script
# Generated by Video Translator Agent

echo "🚀 Installing AllVoiceLab MCP Server..."

# Install uv (Python package manager)
echo "📦 Installing uv package manager..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Reload shell to use uv
source ~/.bashrc || source ~/.zshrc || true

# Install AllVoiceLab MCP
echo "📦 Installing AllVoiceLab MCP..."
uvx allvoicelab-mcp --help

# Set environment variables
echo "🔧 Setting up environment variables..."
export ALLVOICELAB_API_KEY="{self.api_key}"
export ALLVOICELAB_API_DOMAIN="{self.api_domain}"
export ALLVOICELAB_BASE_PATH="{self.output_dir}"

# Copy Claude Desktop configuration
echo "⚙️ Setting up Claude Desktop configuration..."
CONFIG_DIR="$HOME/.claude"
mkdir -p "$CONFIG_DIR"

cat > "$CONFIG_DIR/claude_desktop_config.json" << 'EOF'
{json.dumps({"mcpServers": {"AllVoiceLab": {"command": "uvx", "args": ["allvoicelab-mcp"], "env": {"ALLVOICELAB_API_KEY": self.api_key, "ALLVOICELAB_API_DOMAIN": self.api_domain, "ALLVOICELAB_BASE_PATH": self.output_dir}}}}, indent=2)}
EOF

echo "✅ AllVoiceLab MCP installation completed!"
echo "📁 Output directory: {self.output_dir}"
echo "🔧 Configuration saved to: $CONFIG_DIR/claude_desktop_config.json"
echo ""
echo "📝 Next Steps:"
echo "1. Restart Claude Desktop application"
echo "2. Go to Claude > Settings > Developer > Edit Config"
echo "3. Verify the configuration is loaded correctly"
echo "4. Start using AllVoiceLab tools in Claude!"
echo ""
echo "🎯 Available Commands:"
echo "- video_translation_dubbing: Translate and dub videos"
echo "- subtitle_extraction: Extract subtitles from videos"
echo "- remove_subtitle: Remove hardcoded subtitles"
echo "- text_to_speech: Convert text to speech"
echo "- speech_to_speech: Convert voice to another voice"
echo "- clone_voice: Clone a voice from audio sample"
"""

        script_path = os.path.join(self.output_dir, "install_allvoicelab_mcp.sh")
        with open(script_path, 'w') as f:
            f.write(script_content)

        # Make script executable
        os.chmod(script_path, 0o755)

        logger.info(f"Installation script created: {script_path}")
        return script_path

    def create_usage_guide(self) -> str:
        """
        Create comprehensive usage guide for the Video Translator Agent

        Returns:
            Path to the usage guide file
        """
        guide_content = f"""# Video Translator/Dubber & Subtitler Agent - Usage Guide

## 🎯 Overview

This agent provides comprehensive video processing capabilities using AllVoiceLab's AI-powered tools:

- **Video Translation & Dubbing**: Translate speech in videos to different languages
- **Subtitle Extraction**: Extract hardcoded subtitles from videos using OCR
- **Subtitle Removal**: Remove burned-in subtitles from videos
- **Text-to-Speech**: Convert text to natural-sounding speech
- **Voice Conversion**: Change voice characteristics while preserving content
- **Voice Cloning**: Clone voices from audio samples

## 🔧 Setup

### API Configuration
- **API Key**: {self.api_key[:10]}...
- **API Domain**: {self.api_domain}
- **Output Directory**: {self.output_dir}

### Supported Languages
{chr(10).join([f"- {lang.name.title()}: {lang.value}" for lang in SupportedLanguages])}

### Supported Formats

**Video Formats**:
{chr(10).join([f"- {fmt.value.upper()}" for fmt in VideoFormats])}

**Audio Formats**:
{chr(10).join([f"- {fmt.value.upper()}" for fmt in AudioFormats])}

## 🎬 Available Operations

### 1. Video Translation & Dubbing

Translate and dub video content to different languages while preserving timing and emotion.

**Claude Command**:
```
Select your video file and ask: "Translate this video to [language]"
```

**Example**:
```
"Translate this video to Japanese"
"Dub this video in French with natural voices"
```

**Limitations**:
- Max file size: 2GB
- Supported formats: MP4, MOV, MP3, WAV
- Processing time: 2-10 minutes depending on length

### 2. Subtitle Extraction

Extract hardcoded subtitles from videos using advanced OCR technology.

**Claude Command**:
```
Select your video and ask: "Extract subtitles from this video"
```

**Features**:
- Automatic language detection
- High accuracy OCR (98%+)
- SRT format output
- Multi-language support

### 3. Subtitle Removal

Remove burned-in subtitles from videos while preserving video quality.

**Claude Command**:
```
Select your video and ask: "Remove subtitles from this video"
```

**Use Cases**:
- Clean videos for re-subtitling
- Remove unwanted text overlays
- Prepare content for dubbing

### 4. Text-to-Speech

Convert text to natural-sounding speech in multiple languages and voices.

**Claude Command**:
```
"Convert this text to speech: [your text]"
"Generate audio from this text using a female voice"
```

**Features**:
- 30+ languages supported
- Multiple voice options per language
- Adjustable speed (0.5x to 1.5x)
- High-quality output

### 5. Voice Conversion

Change the voice in audio while preserving the original speech content.

**Claude Command**:
```
Select an audio file and ask: "Convert this to a [male/female] voice"
"Change the voice in this audio to sound like [description]"
```

### 6. Voice Cloning

Create custom voice profiles from audio samples for personalized TTS.

**Claude Command**:
```
Select an audio sample and ask: "Clone this voice"
"Create a voice profile from this audio sample"
```

**Requirements**:
- Clear audio sample (3+ seconds)
- Minimal background noise
- Single speaker only

## 📁 File Management

### Output Directory Structure
```
{self.output_dir}/
├── translated_videos/      # Dubbed video outputs
├── extracted_subtitles/    # SRT subtitle files
├── cleaned_videos/         # Videos with subtitles removed
├── generated_audio/        # TTS and voice conversion outputs
├── cloned_voices/         # Voice profile data
├── task_history.json      # Processing history
└── claude_desktop_config.json  # Claude configuration
```

### File Naming Convention
- Translated videos: `[original]_[target_lang]_dubbed.[ext]`
- Extracted subtitles: `[original]_subtitles.srt`
- Cleaned videos: `[original]_no_subtitles.[ext]`
- Generated audio: `[timestamp]_tts_[lang].[ext]`

## 🔍 Monitoring & Status

### Task Tracking
All processing tasks are tracked with unique IDs and status updates:
- `pending`: Task submitted, waiting to start
- `processing`: Currently being processed
- `success`: Completed successfully
- `failed`: Processing failed

### Status Commands
```
"Check status of dubbing task [task_id]"
"Show my processing history"
"List all active tasks"
```

## 💡 Tips for Best Results

### Video Translation
1. **Clear Audio**: Ensure source video has clear speech
2. **Minimal Background Noise**: Better translation accuracy
3. **Standard Formats**: Use MP4 for best compatibility
4. **File Size**: Keep under 2GB for faster processing

### Subtitle Extraction
1. **High Contrast**: White text on dark backgrounds work best
2. **Standard Fonts**: Avoid stylized or decorative fonts
3. **Clear Resolution**: Higher resolution improves OCR accuracy

### Voice Cloning
1. **Sample Quality**: Use high-quality audio samples
2. **Single Speaker**: Ensure only one person speaking
3. **Natural Speech**: Avoid overly dramatic or processed audio
4. **Length**: 5-10 seconds of clear speech is optimal

## 🚨 Troubleshooting

### Common Issues

**"Tool not available" error**:
- Check API key is correct
- Verify domain matches your region
- Ensure AllVoiceLab MCP is properly installed

**Processing takes too long**:
- Large files require more processing time
- Check file size limits
- Consider breaking large videos into segments

**Poor translation quality**:
- Ensure source audio is clear
- Check if source language is correctly detected
- Try manual language specification

**Subtitle extraction issues**:
- Verify subtitles are visible and high contrast
- Check video resolution and quality
- Try different language detection settings

### Log Files
- Agent logs: `/Users/lucadisanto/video_translator_agent.log`
- MCP logs: `~/.mcp/allvoicelab_mcp.log`

## 📞 Support

For technical issues:
- Email: tech@allvoicelab.com
- Include log files and task IDs
- Describe steps to reproduce the issue

## 🎯 Advanced Usage

### Batch Processing
Process multiple files by selecting them and asking:
```
"Translate all these videos to Spanish"
"Extract subtitles from all selected videos"
```

### Custom Workflows
1. Extract subtitles → Translate text → Generate new audio → Create dubbed video
2. Remove subtitles → Add translated subtitles → Export final video
3. Clone voice → Use for TTS → Create personalized narration

### API Credits
Monitor your AllVoiceLab credit usage at:
- Global: https://www.allvoicelab.com/workbench
- China: https://www.allvoicelab.cn/workbench

---

*Generated by Video Translator Agent v1.0*
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        guide_path = os.path.join(self.output_dir, "Video_Translator_Usage_Guide.md")
        with open(guide_path, 'w') as f:
            f.write(guide_content)

        logger.info(f"Usage guide created: {guide_path}")
        return guide_path

    def create_demo_script(self) -> str:
        """
        Create demonstration script showing all capabilities

        Returns:
            Path to the demo script file
        """
        demo_content = f"""#!/usr/bin/env python3
\"\"\"
Video Translator Agent - Demonstration Script
Shows all available capabilities with example usage
\"\"\"

import os
from video_translator_agent import VideoTranslatorAgent

def main():
    # Initialize agent with your API key
    agent = VideoTranslatorAgent(
        api_key="{self.api_key}",
        api_domain="{self.api_domain}",
        output_dir="{self.output_dir}"
    )

    print("🎬 Video Translator Agent Demo")
    print("=" * 50)

    # Show supported languages
    print("\\n📝 Supported Languages:")
    for lang in agent.get_supported_languages():
        print(f"  - {{lang}}")

    # Show supported formats
    print("\\n🎞️ Supported Video Formats:")
    for fmt in agent.get_supported_video_formats():
        print(f"  - {{fmt}}")

    print("\\n🎵 Supported Audio Formats:")
    for fmt in agent.get_supported_audio_formats():
        print(f"  - {{fmt}}")

    # Show configuration
    print("\\n⚙️ Configuration:")
    print(f"  API Domain: {{agent.api_domain}}")
    print(f"  Output Directory: {{agent.output_dir}}")

    # Generate Claude Desktop config
    print("\\n🔧 Generating Claude Desktop Configuration...")
    config = agent.create_claude_desktop_config()
    print("Configuration generated successfully!")

    # Create installation script
    print("\\n📦 Creating Installation Script...")
    script_path = agent.create_mcp_installation_script()
    print(f"Installation script created: {{script_path}}")

    # Create usage guide
    print("\\n📚 Creating Usage Guide...")
    guide_path = agent.create_usage_guide()
    print(f"Usage guide created: {{guide_path}}")

    print("\\n✅ Demo completed! Check the output directory for all generated files.")
    print(f"\\n📁 Output Directory: {{agent.output_dir}}")

    # Instructions for next steps
    print("\\n🚀 Next Steps:")
    print("1. Run the installation script to set up AllVoiceLab MCP")
    print("2. Restart Claude Desktop")
    print("3. Check that AllVoiceLab tools are available")
    print("4. Start translating and dubbing your videos!")

if __name__ == "__main__":
    main()
\"\"\"

# Example Claude Commands to Try:

# Video Translation:
# "Translate this video to Japanese"
# "Dub this English video in Spanish with natural voices"

# Subtitle Operations:
# "Extract subtitles from this video"
# "Remove the hardcoded subtitles from this video"

# Voice Operations:
# "Convert this text to speech: Hello, welcome to our presentation"
# "Change this audio to a female voice"
# "Clone the voice from this audio sample"

# Batch Operations:
# "Translate all these videos to French"
# "Extract subtitles from all selected video files"
\"\"\"
"""

        demo_path = os.path.join(self.output_dir, "demo_video_translator.py")
        with open(demo_path, 'w') as f:
            f.write(demo_content)

        # Make script executable
        os.chmod(demo_path, 0o755)

        logger.info(f"Demo script created: {demo_path}")
        return demo_path

def main():
    """Main function to initialize the Video Translator Agent"""

    # Your AllVoiceLab API key
    API_KEY = "ak_57b6e1783340b045354b0077842675b8331b"

    # API domain (use global or China based on your account)
    API_DOMAIN = "https://api.allvoicelab.com"  # Global
    # API_DOMAIN = "https://api.allvoicelab.cn"  # China

    # Initialize the agent
    agent = VideoTranslatorAgent(
        api_key=API_KEY,
        api_domain=API_DOMAIN,
        output_dir="/Users/lucadisanto/Desktop/VideoTranslator"
    )

    print("🎬 Video Translator/Dubber & Subtitler Agent")
    print("=" * 50)
    print(f"📁 Output Directory: {agent.output_dir}")
    print(f"🌐 API Domain: {agent.api_domain}")
    print(f"🔑 API Key: {agent.api_key[:10]}...")

    # Generate all configuration files
    print("\\n🔧 Generating configuration files...")

    # Claude Desktop configuration
    config = agent.create_claude_desktop_config()
    print("✅ Claude Desktop configuration generated")

    # Installation script
    script_path = agent.create_mcp_installation_script()
    print(f"✅ Installation script created: {script_path}")

    # Usage guide
    guide_path = agent.create_usage_guide()
    print(f"✅ Usage guide created: {guide_path}")

    # Demo script
    demo_path = agent.create_demo_script()
    print(f"✅ Demo script created: {demo_path}")

    print("\\n🚀 Setup Complete!")
    print("\\nNext Steps:")
    print("1. Run the installation script:")
    print(f"   bash {script_path}")
    print("2. Restart Claude Desktop")
    print("3. Check AllVoiceLab tools are available")
    print("4. Read the usage guide for detailed instructions")
    print("5. Start processing your videos!")

    print(f"\\n📚 Documentation: {guide_path}")
    print(f"📁 All files saved to: {agent.output_dir}")

if __name__ == "__main__":
    main()