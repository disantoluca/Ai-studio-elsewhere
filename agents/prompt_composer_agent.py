"""
Prompt Composer Agent for Jieziyuan Huazhuan Multi-Agent System
================================================================
This agent generates visual prompts for Tongyi Wanxiang (通义万相) image engine
to create reference panels and step-by-step visual guides for traditional Chinese painting.

Author: Jieziyuan Huazhuan Project
License: Educational Use
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class PaintingStyle(Enum):
    """Traditional Chinese painting styles"""
    GONGBI = "工笔"  # Meticulous brush
    XIEYI = "写意"  # Freehand brush
    MOGU = "没骨"  # Boneless (no outline)
    BAIMIAO = "白描"  # Line drawing


class InkTone(Enum):
    """Five tones of ink (墨分五色)"""
    JIAO = "焦"  # Scorched/burnt
    NONG = "浓"  # Dark/concentrated
    ZHONG = "重"  # Heavy
    DAN = "淡"  # Light
    QING = "清"  # Clear/pale


@dataclass
class PromptParameters:
    """Parameters for visual prompt generation"""
    subject: str  # e.g., "竹叶", "山石"
    style: PaintingStyle
    step_number: int
    total_steps: int
    ink_tones: List[InkTone]
    materials: List[str]
    technique: str  # e.g., "中锋", "破墨"
    composition_notes: str
    aspect_ratio: str = "4:3"
    negative_prompts: List[str] = None
    
    def __post_init__(self):
        if self.negative_prompts is None:
            self.negative_prompts = [
                "西式油画",  # Western oil painting
                "水彩画",    # Watercolor
                "3D渲染",    # 3D rendering
                "照片写实",  # Photorealistic
                "数码绘画"   # Digital painting
            ]


class PromptComposerAgent:
    """
    Generates structured prompts for Tongyi Wanxiang image generation
    based on Jieziyuan Huazhuan teaching methodology.
    """
    
    def __init__(self, model_name: str = "wanxiang-v1"):
        self.model_name = model_name
        self.prompt_templates = self._load_prompt_templates()
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load pre-defined prompt templates for different scenarios"""
        return {
            "step_by_step": (
                "国画教学分镜：步骤{step_num}/{total_steps}，"
                "宣纸质感，墨分五色，禁止西式油画效果。"
                "主题：{subject}；风格：{style}；技法：{technique}；"
                "墨色：{ink_tones}；比例：{aspect_ratio}。"
                "{composition_notes}"
            ),
            "reference_panel": (
                "芥子园画传风格参考图：{subject}，"
                "{style}画法，展示{technique}技法要点。"
                "宣纸底纹，传统国画装裱样式，"
                "墨色层次：{ink_tones}。构图：{composition_notes}"
            ),
            "technique_demo": (
                "国画技法示范：{technique}在{subject}中的应用，"
                "分解动作：{step_description}。"
                "材料：{materials}；墨色变化：{ink_tones}；"
                "宣纸上的笔触特写，清晰展示运笔方向与力度。"
            ),
            "composition_study": (
                "国画构图研究：{subject}的布局与留白。"
                "{composition_notes}。"
                "体现{art_concepts}的美学原则，"
                "传统{style}风格，水墨质感。"
            ),
            "mistake_correction": (
                "国画常见错误对比：{subject}的{technique}技法。"
                "左图：{mistake_description}（错误示范）；"
                "右图：正确示范，展示{correction_notes}。"
                "宣纸质感，教学用途标注。"
            )
        }
    
    def compose_step_prompt(
        self, 
        params: PromptParameters,
        step_description: str
    ) -> Dict[str, str]:
        """
        Generate prompt for a single step in a lesson.
        
        Args:
            params: Prompt parameters including subject, style, technique
            step_description: Description of this specific step
            
        Returns:
            Dictionary with Chinese and English prompts plus metadata
        """
        ink_tones_str = "、".join([tone.value for tone in params.ink_tones])
        
        prompt_zh = self.prompt_templates["step_by_step"].format(
            step_num=params.step_number,
            total_steps=params.total_steps,
            subject=params.subject,
            style=params.style.value,
            technique=params.technique,
            ink_tones=ink_tones_str,
            aspect_ratio=params.aspect_ratio,
            composition_notes=params.composition_notes
        )
        
        # English translation for international users
        prompt_en = self._translate_prompt(prompt_zh, step_description)
        
        # Negative prompts to avoid Western painting styles
        negative_prompt = ", ".join(params.negative_prompts)
        
        return {
            "prompt_zh": prompt_zh,
            "prompt_en": prompt_en,
            "negative_prompt": negative_prompt,
            "step_description": step_description,
            "metadata": {
                "subject": params.subject,
                "style": params.style.value,
                "technique": params.technique,
                "step": f"{params.step_number}/{params.total_steps}",
                "ink_tones": ink_tones_str,
                "aspect_ratio": params.aspect_ratio
            }
        }
    
    def compose_reference_panel(
        self,
        lesson_id: str,
        subject: str,
        style: PaintingStyle,
        technique: str,
        composition_notes: str,
        ink_tones: List[InkTone]
    ) -> Dict[str, str]:
        """
        Generate prompt for creating a reference panel image.
        
        Returns:
            Dictionary with prompt and metadata for reference generation
        """
        ink_tones_str = "、".join([tone.value for tone in ink_tones])
        
        prompt_zh = self.prompt_templates["reference_panel"].format(
            subject=subject,
            style=style.value,
            technique=technique,
            ink_tones=ink_tones_str,
            composition_notes=composition_notes
        )
        
        return {
            "lesson_id": lesson_id,
            "type": "reference_panel",
            "prompt_zh": prompt_zh,
            "prompt_en": self._translate_prompt(prompt_zh, ""),
            "metadata": {
                "subject": subject,
                "style": style.value,
                "technique": technique,
                "purpose": "reference_learning"
            }
        }
    
    def compose_technique_demo(
        self,
        technique: str,
        subject: str,
        step_description: str,
        materials: List[str],
        ink_tones: List[InkTone]
    ) -> Dict[str, str]:
        """
        Generate prompt for technique demonstration close-up.
        
        Returns:
            Dictionary with prompt for detailed technique visualization
        """
        ink_tones_str = "、".join([tone.value for tone in ink_tones])
        materials_str = "、".join(materials)
        
        prompt_zh = self.prompt_templates["technique_demo"].format(
            technique=technique,
            subject=subject,
            step_description=step_description,
            materials=materials_str,
            ink_tones=ink_tones_str
        )
        
        return {
            "type": "technique_demo",
            "prompt_zh": prompt_zh,
            "prompt_en": self._translate_prompt(prompt_zh, step_description),
            "metadata": {
                "technique": technique,
                "subject": subject,
                "materials": materials,
                "focus": "brushwork_detail"
            }
        }
    
    def compose_composition_study(
        self,
        subject: str,
        style: PaintingStyle,
        composition_notes: str,
        art_concepts: List[str]
    ) -> Dict[str, str]:
        """
        Generate prompt for composition and layout study.
        
        Returns:
            Dictionary with prompt focused on spatial arrangement
        """
        art_concepts_str = "、".join(art_concepts)
        
        prompt_zh = self.prompt_templates["composition_study"].format(
            subject=subject,
            style=style.value,
            composition_notes=composition_notes,
            art_concepts=art_concepts_str
        )
        
        return {
            "type": "composition_study",
            "prompt_zh": prompt_zh,
            "prompt_en": self._translate_prompt(prompt_zh, composition_notes),
            "metadata": {
                "subject": subject,
                "style": style.value,
                "art_concepts": art_concepts,
                "focus": "spatial_arrangement"
            }
        }
    
    def compose_mistake_correction(
        self,
        subject: str,
        technique: str,
        mistake_description: str,
        correction_notes: str
    ) -> Dict[str, str]:
        """
        Generate prompt for mistake vs. correct comparison image.
        
        Returns:
            Dictionary with prompt for error correction visualization
        """
        prompt_zh = self.prompt_templates["mistake_correction"].format(
            subject=subject,
            technique=technique,
            mistake_description=mistake_description,
            correction_notes=correction_notes
        )
        
        return {
            "type": "mistake_correction",
            "prompt_zh": prompt_zh,
            "prompt_en": self._translate_prompt(prompt_zh, mistake_description),
            "metadata": {
                "subject": subject,
                "technique": technique,
                "purpose": "error_correction",
                "layout": "side_by_side"
            }
        }
    
    def compose_lesson_sequence(
        self,
        lesson_data: Dict
    ) -> List[Dict[str, str]]:
        """
        Generate complete sequence of prompts for an entire lesson.
        
        Args:
            lesson_data: Lesson JSON/dict from YAML schema
            
        Returns:
            List of prompt dictionaries for all steps and references
        """
        prompts_sequence = []
        
        # Extract lesson metadata
        lesson_id = lesson_data.get("lesson_id", "")
        subject = lesson_data.get("metadata", {}).get("subject_tags", [""])[0]
        materials = lesson_data.get("materials", [])
        art_concepts = lesson_data.get("metadata", {}).get("art_concepts", [])
        steps = lesson_data.get("steps", [])
        composition = lesson_data.get("composition", {})
        
        # Determine style (default to xieyi if not specified)
        style = PaintingStyle.XIEYI  # Could parse from lesson_data if specified
        
        # Generate reference panel first
        reference_prompt = self.compose_reference_panel(
            lesson_id=lesson_id,
            subject=subject,
            style=style,
            technique=steps[0].get("zh", "") if steps else "",
            composition_notes=composition.get("zh", ""),
            ink_tones=[InkTone.NONG, InkTone.DAN]  # Default ink tones
        )
        prompts_sequence.append(reference_prompt)
        
        # Generate prompts for each step
        for idx, step in enumerate(steps, 1):
            step_params = PromptParameters(
                subject=subject,
                style=style,
                step_number=idx,
                total_steps=len(steps),
                ink_tones=[InkTone.NONG, InkTone.DAN],  # Could be extracted from step
                materials=materials,
                technique=step.get("zh", "").split("：")[0] if "：" in step.get("zh", "") else "",
                composition_notes=composition.get("zh", "")
            )
            
            step_prompt = self.compose_step_prompt(
                params=step_params,
                step_description=step.get("zh", "")
            )
            step_prompt["step_id"] = step.get("id", f"s{idx}")
            prompts_sequence.append(step_prompt)
        
        return prompts_sequence
    
    def _translate_prompt(self, prompt_zh: str, context: str) -> str:
        """
        Provide basic English translation of prompt.
        In production, would use Qwen or translation API.
        
        Args:
            prompt_zh: Chinese prompt
            context: Additional context for translation
            
        Returns:
            English translation
        """
        # Simplified translation mappings
        translations = {
            "国画教学分镜": "Traditional Chinese painting instructional sequence",
            "宣纸质感": "rice paper texture",
            "墨分五色": "five tones of ink",
            "禁止西式油画效果": "no Western oil painting style",
            "主题": "subject",
            "风格": "style",
            "技法": "technique",
            "墨色": "ink tones",
            "比例": "aspect ratio",
            "芥子园画传风格": "Mustard Seed Garden Manual style",
            "参考图": "reference panel",
            "画法": "painting method",
            "展示": "demonstrates",
            "技法要点": "key technique points",
            "宣纸底纹": "rice paper background",
            "传统国画装裱样式": "traditional Chinese painting mounting style",
            "构图": "composition"
        }
        
        prompt_en = prompt_zh
        for zh_term, en_term in translations.items():
            prompt_en = prompt_en.replace(zh_term, en_term)
        
        return prompt_en
    
    def export_prompts_to_json(
        self,
        prompts_sequence: List[Dict],
        output_path: str
    ) -> None:
        """
        Export generated prompts to JSON file for API integration.
        
        Args:
            prompts_sequence: List of prompt dictionaries
            output_path: Path to save JSON file
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(prompts_sequence, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Exported {len(prompts_sequence)} prompts to {output_path}")


# Example usage and test function
def test_prompt_composer():
    """Test the Prompt Composer Agent with sample data"""
    
    composer = PromptComposerAgent()
    
    # Example lesson data (matching YAML schema)
    sample_lesson = {
        "lesson_id": "jzy_bamboo_leaves_01",
        "corpus": {
            "work_zh": "芥子园画传",
            "section_zh": "竹谱"
        },
        "materials": ["狼毫小笔", "浓墨"],
        "metadata": {
            "subject_tags": ["竹叶"],
            "art_concepts": ["骨法用笔", "虚实相生"]
        },
        "steps": [
            {
                "id": "s1",
                "zh": "第一笔起笔要有力，如风中之竹。",
                "en": "Start the first stroke with energy, like bamboo swaying in wind."
            },
            {
                "id": "s2",
                "zh": "第二笔要顺势斜下，三笔成叶。",
                "en": "The second stroke follows diagonally down; three strokes make a leaf."
            }
        ],
        "composition": {
            "zh": "叶叶相顾，不可平排。",
            "en": "Leaves should face each other, not line up flat."
        }
    }
    
    # Generate full lesson sequence
    print("=" * 60)
    print("Generating Prompt Sequence for Bamboo Leaves Lesson")
    print("=" * 60)
    
    prompts = composer.compose_lesson_sequence(sample_lesson)
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n[Prompt {i}]")
        print(f"Type: {prompt.get('type', 'step')}")
        print(f"Chinese: {prompt.get('prompt_zh', '')[:100]}...")
        print(f"English: {prompt.get('prompt_en', '')[:100]}...")
        if 'step_id' in prompt:
            print(f"Step ID: {prompt['step_id']}")
        print("-" * 60)
    
    # Export to JSON
    composer.export_prompts_to_json(prompts, "/home/claude/sample_prompts.json")
    
    return prompts


if __name__ == "__main__":
    # Run test when script is executed directly
    test_prompts = test_prompt_composer()
    print(f"\n✓ Generated {len(test_prompts)} prompts successfully!")
