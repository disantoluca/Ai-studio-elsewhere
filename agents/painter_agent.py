# -*- coding: utf-8 -*-
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from PIL import Image
import os, time, json, base64, io
from openai import OpenAI
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from tongyi_wanx_client import TongyiWanxClient

DASHSCOPE_INTL_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
DASHSCOPE_CN_BASE   = "https://dashscope.aliyuncs.com/compatible-mode/v1"

@dataclass
class PainterParameters:
    subject: str
    style: List[str]
    negative: List[str]
    aspect_ratio: str = "4:3"
    seed: Optional[int] = None
    steps: int = 4
    controlnet: Optional[str] = None
    language: str = "zh"
    prompt_zh: Optional[str] = None
    prompt_en: Optional[str] = None

class PainterAgent:
    def __init__(self, api_key: Optional[str] = None, region: str = "intl", model: str = "wanx-v1"):
        # --- Setup client ---
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY not set")

        region = os.getenv("DASHSCOPE_REGION", region)
        base_url = DASHSCOPE_INTL_BASE if region == "intl" else DASHSCOPE_CN_BASE
        self.client = OpenAI(api_key=self.api_key, base_url=base_url)

        # Prefer env model if provided (e.g., qwen-image-edit-plus)
        self.model = os.getenv("DASHSCOPE_IMAGE_MODEL", model)

        self.out_dir = Path(os.getenv("PAINTER_OUT_DIR", "./generated_panels")).resolve()
        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ---------- HELPER METHODS: place RIGHT AFTER __init__ ----------
    def _size_from_ratio(self, ratio: str) -> str:
        """Map aspect ratio to size string."""
        return {
            "1:1":  "1024x1024",
            "4:3":  "1024x768",
            "3:4":  "768x1024",
            "16:9": "1280x720",
        }.get(ratio, "1024x768")

    def _size_to_wh(self, size_str: str) -> Tuple[int, int]:
        try:
            w, h = size_str.lower().split("x")
            return int(w), int(h)
        except Exception:
            return (1024, 768)

    def _blank_png_b64(self, w: int = 1024, h: int = 768, color=(255, 255, 255)) -> str:
        """Create a white (xuan-paper-like) base image for image-edit models."""
        im = Image.new("RGB", (w, h), color)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

    def _compose_prompt(self, params: PainterParameters, step_index: int, step_desc: str) -> str:
        style_tags = ", ".join(params.style)
        neg_tags = ", ".join(params.negative)

        prefix_zh = (
            f"国画教学分镜：步骤{step_index}/{params.steps}，宣纸质感，墨分五色，"
            f"题材：{params.subject}，风格：{style_tags}。"
        )
        prefix_en = (
            f"Traditional Chinese painting teaching panel step {step_index}/{params.steps}, "
            f"xuan paper texture, five ink tones, subject: {params.subject}, style: {style_tags}."
        )

        # Compose bilingual prompt; include negatives inline so edit models respect them
        prompt_zh = (params.prompt_zh or prefix_zh) + " " + step_desc
        prompt_en = (params.prompt_en or prefix_en) + " " + step_desc
        full = (
            f"{prompt_zh}\n\n"
            f"EN HINT: {prompt_en}\n\n"
            f"禁止：{neg_tags}"
        )
        return full

    def _save(self, b64: str, name: str) -> str:
        p = self.out_dir / name
        with open(p, "wb") as f:
            f.write(base64.b64decode(b64))
        return str(p)

    def _generate_image(self, prompt: str, size: str, negative: Optional[str] = None,
                        seed: Optional[int] = None, controlnet: Optional[str] = None) -> str:
        """
        Unified image creation: uses image **edits** on a blank canvas when model
        is qwen-image-edit*, and falls back to generate if supported (Wanxiang).
        Returns base64 string.
        """
        w, h = self._size_to_wh(size)

        # If using image-edit model, draw on a blank xuan-paper canvas
        if self.model.startswith("qwen-image-edit"):
            init_img = self._blank_png_b64(w, h)
            result = self.client.images.edit(
                model=self.model,
                image=init_img,
                prompt=prompt,     # negatives already included in prompt text
                n=1,
                size=size,
            )
            return result.data[0].b64_json

        # Otherwise try text-to-image (Wanxiang or other T2I available on account)
        try:
            extra = {}
            if seed is not None:
                extra["seed"] = seed
            if negative:
                extra["negative_prompt"] = negative
            if controlnet:
                extra["controlnet"] = controlnet

            result = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                n=1,
                extra_body=extra or None,
            )
            return result.data[0].b64_json
        except Exception:
            # Last ditch: fallback to edit if generate isn't supported on the account
            init_img = self._blank_png_b64(w, h)
            result = self.client.images.edit(
                model="qwen-image-edit-plus",
                image=init_img,
                prompt=prompt,
                n=1,
                size=size,
            )
            return result.data[0].b64_json
    # ---------- END HELPER METHODS ----------

    def generate_panel(self, params: PainterParameters, step_index: int, step_description: str) -> Dict:
        size = self._size_from_ratio(params.aspect_ratio)
        neg_tags = ", ".join(params.negative)
        seed = params.seed if params.seed is not None else int(time.time()) % 100000

        composed = self._compose_prompt(params, step_index, step_description)
        b64 = self._generate_image(
            prompt=composed,
            size=size,
            negative=neg_tags,
            seed=seed,
            controlnet=params.controlnet,
        )
        return {
            "path": self._save(b64, f"{params.subject.replace(' ', '_')}_step{step_index}.png"),
            "step": step_index,
            "seed": seed,
        }

    def generate_lesson(self, params: PainterParameters, step_descriptions: List[str]) -> Dict:
        assert len(step_descriptions) == params.steps, "step_descriptions length must equal params.steps"

        # Panels
        panels = [self.generate_panel(params, i + 1, d) for i, d in enumerate(step_descriptions)]

        # Final composition (broader guidance, same switch logic)
        try:
            size_final = {
                "4:3":  "1280x960",
                "1:1":  "1024x1024",
                "16:9": "1280x720",
                "3:4":  "960x1280",
            }.get(params.aspect_ratio, "1280x960")

            neg = ", ".join(params.negative)
            final_prompt = (
                f"国画成品图：{params.subject}，遵循上述步骤完成整体构图；"
                f"留白明显；中锋为主；宣纸墨韵。禁止：{neg}"
            )

            b64 = self._generate_image(
                prompt=final_prompt,
                size=size_final,
                negative=neg,
                seed=(params.seed or int(time.time()) % 100000) + 99,
                controlnet=None,
            )
            final_path = self._save(b64, f"{params.subject.replace(' ', '_')}_final.png")
        except Exception:
            final_path = ""

        return {"panels": panels, "final": final_path, "params": asdict(params)}

