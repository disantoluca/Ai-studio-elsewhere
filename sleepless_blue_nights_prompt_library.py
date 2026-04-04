#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 Sleepless Blue Nights — Complete Prompt Library
Integrated with AI Studio Elsewhere for Concept Generation, Video Prompts, and Color Scripting

Includes:
- Concept image prompts (Wanxiang)
- Color script (emotional journey)
- Video prompts (Runway Gen-3)
- Ink transition prompts (CHDC)
- Location prompts (Google Places)
- Actor consistency prompts
- Director's statement (bilingual)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from enum import Enum

# ============================================================
# ENUMS & DATA STRUCTURES
# ============================================================

class Act(Enum):
    """Film acts for color scripting"""
    REUNION = "ACT I - Reunion"
    AFTER_REUNION = "ACT II - After the Reunion"
    SURREAL_NIGHT = "ACT III - The Surreal Night"
    MORNING_AFTER = "ACT IV - The Morning After"

class PromptType(Enum):
    """Types of prompts in the library"""
    CONCEPT_IMAGE = "concept_image"
    VIDEO = "video"
    INK_TRANSITION = "ink_transition"
    LOCATION = "location"
    ACTOR_CONSISTENCY = "actor_consistency"

@dataclass
class ColorMotif:
    """Color motif for emotional expression"""
    name: str
    hex_code: str
    emotional_meaning_en: str
    emotional_meaning_zh: str
    
    def __str__(self):
        return f"{self.name} ({self.hex_code}) - {self.emotional_meaning_en}"

@dataclass
class Prompt:
    """Single prompt with bilingual support"""
    id: str
    title: str
    prompt_en: str
    prompt_zh: str
    type: PromptType
    scene_number: Optional[int] = None
    act: Optional[Act] = None
    color_motifs: List[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.color_motifs is None:
            self.color_motifs = []

@dataclass
class ColorFrame:
    """Color script frame for a scene"""
    scene_number: int
    scene_heading: str
    primary_color: str
    secondary_color: str
    emotional_tone: str
    notes: str
    act: Act

# ============================================================
# 1. COLOR MOTIF LIBRARY
# ============================================================

COLOR_MOTIFS = {
    "cobalt_blue": ColorMotif(
        name="Deep Cobalt Blue",
        hex_code="#003D82",
        emotional_meaning_en="sleepless night / emotional distance",
        emotional_meaning_zh="失眠的夜晚 / 情感距离"
    ),
    "sodium_yellow": ColorMotif(
        name="Sodium Yellow",
        hex_code="#FFB81C",
        emotional_meaning_en="memory, warmth, temptation",
        emotional_meaning_zh="记忆、温暖、诱惑"
    ),
    "ink_black": ColorMotif(
        name="Ink Black",
        hex_code="#1A1A1A",
        emotional_meaning_en="surreal transitions, suppressed feelings",
        emotional_meaning_zh="超现实过渡、被压抑的感受"
    ),
    "fog_white": ColorMotif(
        name="Fog White",
        hex_code="#E8E8E8",
        emotional_meaning_en="ambiguity, time suspension",
        emotional_meaning_zh="模糊性、时间悬浮"
    ),
    "warm_dust_orange": ColorMotif(
        name="Warm Dust Orange",
        hex_code="#D4844A",
        emotional_meaning_en="nostalgia, past Yunnan memories",
        emotional_meaning_zh="怀旧、云南往事"
    ),
    "neon_red": ColorMotif(
        name="Neon Red",
        hex_code="#FF3366",
        emotional_meaning_en="emotional rupture, danger, desire",
        emotional_meaning_zh="情感裂隙、危险、渴望"
    ),
    "lotus_pink": ColorMotif(
        name="Lotus Pink",
        hex_code="#FFB3BA",
        emotional_meaning_en="blooming emotion, fleeting beauty",
        emotional_meaning_zh="绽放的情感、短暂的美"
    ),
    "electric_purple": ColorMotif(
        name="Electric Purple",
        hex_code="#9D4EDD",
        emotional_meaning_en="the impossible, what cannot exist",
        emotional_meaning_zh="不可能的、无法存在的"
    ),
}

# ============================================================
# 2. CONCEPT IMAGE PROMPTS
# ============================================================

CONCEPT_PROMPTS = [
    Prompt(
        id="concept_01",
        title="Urban Night (Neon + Fog)",
        prompt_en="Shanghai street at 2am, neon reflections on wet pavement, deep cobalt-blue tones, diffused fog, soft cinematic grain, poetic realism, empty sidewalks, emotional silence, Wong Kar-wai mood, slow cinema atmosphere, suspended time.",
        prompt_zh="凌晨2点的上海街道，霓虹在湿润路面上反射，深钴蓝色调，弥漫雾气，柔和胶片颗粒，诗意现实主义，空旷安静，王家卫式氛围，慢电影，时间被悬浮。",
        type=PromptType.CONCEPT_IMAGE,
        color_motifs=["cobalt_blue", "sodium_yellow", "fog_white"],
        notes="Core establishing imagery for the film"
    ),
    Prompt(
        id="concept_02",
        title="Emotional Close-up (Portrait Style)",
        prompt_en="Close-up of a woman looking away in soft neon light, mist around her face, melancholic expression, gentle highlights, shallow depth of field, intimate and quiet mood, unresolved longing.",
        prompt_zh="霓虹柔光下的女性特写，脸庞被雾气包围，眼神忧郁，浅景深，亲密静谧，未解的渴望。",
        type=PromptType.CONCEPT_IMAGE,
        color_motifs=["sodium_yellow", "fog_white", "neon_red"],
        notes="Emotional core of the female lead"
    ),
    Prompt(
        id="concept_03",
        title="Memory Sequence (Surreal Realism)",
        prompt_en="Dreamlike flashback in Yunnan village, soft warm dusk light, floating dust particles, gentle handscroll-paper texture, surreal subtle bloom, ink-washed gradients.",
        prompt_zh="云南村庄的梦境式回忆，暖黄昏光线，飘动尘埃，宣纸质感，隐约超现实的光晕，水墨晕染。",
        type=PromptType.CONCEPT_IMAGE,
        color_motifs=["warm_dust_orange", "fog_white", "ink_black"],
        notes="Flashback sequences to their past"
    ),
    Prompt(
        id="concept_04",
        title="The Reunion Banquet Hall",
        prompt_en="1980s Shanghai high-school reunion banquet room, warm lantern glow, cheap tablecloths, nostalgic atmosphere, soft haze, lively but emotionally distant faces.",
        prompt_zh="80年代上海同学会宴会厅，暖色灯笼光，朴素桌布，怀旧氛围，轻微雾气，热闹却情感疏离的脸庞。",
        type=PromptType.CONCEPT_IMAGE,
        scene_number=2,
        act=Act.REUNION,
        color_motifs=["warm_dust_orange", "sodium_yellow"],
        notes="Opening scene - emotional duality"
    ),
]

# ============================================================
# 3. VIDEO PROMPTS (RUNWAY GEN-3 ALPHA)
# ============================================================

VIDEO_PROMPTS = [
    Prompt(
        id="video_01",
        title="Woman Standing Under Streetlight (Core Imagery)",
        prompt_en="Woman standing alone under a sodium-yellow streetlight at 2am, fog drifting around her, slight handheld camera, deep blue shadows, neon reflections, melancholic atmosphere, poetic realism.",
        prompt_zh="女性独自站在凌晨2点的钠灯下，雾气环绕，微弱的手持相机晃动，深蓝阴影，霓虹反射，忧郁气氛。",
        type=PromptType.VIDEO,
        color_motifs=["cobalt_blue", "sodium_yellow", "fog_white"],
        notes="Camera: Dolly-in slow, Fog simulation, 35mm lens equivalent"
    ),
    Prompt(
        id="video_02",
        title="Alley Walk (Surreal Moment)",
        prompt_en="Man and woman walking through narrow Shanghai alley at night, misty haze, warm lanterns, time feels suspended, subtle surreal distortion at edges, ink particles floating in the air.",
        prompt_zh="男女在深夜狭窄的上海巷子里行走，雾霭笼罩，暖色灯笼，时间被悬浮，边缘微妙扭曲，墨点漂浮空中。",
        type=PromptType.VIDEO,
        color_motifs=["cobalt_blue", "fog_white", "ink_black"],
        notes="Camera: Slow tracking shot, Slight vignette, Ink particles FX"
    ),
    Prompt(
        id="video_03",
        title="Surreal Night (Breaking Reality)",
        prompt_en="The city lights bend slightly, colors blur, neon stretches like ink on wet paper, the couple dissolves into silhouettes, dreamlike aesthetic.",
        prompt_zh="城市灯光微微弯曲，色彩模糊，霓虹如墨在宣纸上晕散，两人溶解成剪影，梦幻美学。",
        type=PromptType.VIDEO,
        act=Act.SURREAL_NIGHT,
        color_motifs=["ink_black", "electric_purple", "cobalt_blue"],
        notes="Camera: Wide lens, Lens breathing, Ink-splash timing cues"
    ),
    Prompt(
        id="video_04",
        title="Reunion Banquet (Documentary Style)",
        prompt_en="High-school reunion banquet, handheld documentary realism, imperfect light, nostalgic 80s Shanghai mood, soft grain.",
        prompt_zh="高中同学会宴会，手持纪录片风格，不完美的光线，80年代怀旧上海氛围，柔和颗粒感。",
        type=PromptType.VIDEO,
        scene_number=2,
        act=Act.REUNION,
        color_motifs=["warm_dust_orange", "sodium_yellow"],
        notes="Camera: Handheld shake, 50mm documentary realism"
    ),
]

# ============================================================
# 4. INK TRANSITION PROMPTS (CHDC ENGINE)
# ============================================================

INK_PROMPTS = [
    Prompt(
        id="transition_01",
        title="Ink Bloom Transition",
        prompt_en="Zhang Daqian ink-splash style, ink droplets expand into mist, then urban silhouettes emerge from the mist, wet-ink texture as it dries, dreamlike passage.",
        prompt_zh="张大千泼墨风格，墨滴扩散成云雾，再从雾中勾勒出城市轮廓，湿墨渐干的质感，梦境般的过渡。",
        type=PromptType.INK_TRANSITION,
        color_motifs=["ink_black", "fog_white"],
        notes="Use between banquet and street scenes"
    ),
    Prompt(
        id="transition_02",
        title="Mist-Dissolve Transition",
        prompt_en="Ink-wash mist spreads, edges soften, dissolve from night scene to dawn memory, gentle, poetic, slow passage.",
        prompt_zh="水墨云雾弥散，边缘柔化，从黑夜场景溶解到清晨记忆，柔和、诗意、缓慢的过渡。",
        type=PromptType.INK_TRANSITION,
        color_motifs=["fog_white", "cobalt_blue"],
        notes="Dream sequence transitions"
    ),
    Prompt(
        id="transition_03",
        title="Brushstroke Reveal",
        prompt_en="Massive ink brushstroke sweeps across frame, pushes darkness aside, reveals neon street; ink spatters, natural randomness, xuan paper texture.",
        prompt_zh="巨大的墨刷痕横扫画面，将黑夜推开，露出霓虹街道；墨迹飞溅、自然随机、具有宣纸纹理。",
        type=PromptType.INK_TRANSITION,
        color_motifs=["ink_black", "sodium_yellow", "neon_red"],
        notes="High-energy emotional shift"
    ),
    Prompt(
        id="transition_04",
        title="Lotus Splash (Emotional Peak)",
        prompt_en="Splatter-paint lotus bloom transition, vibrant yet controlled colors, soft pink and deep blue, symbolizing emotion bursting then fading.",
        prompt_zh="泼彩荷花绽放式过渡，艳丽但控制色彩不喧哗，用柔粉和深蓝，象征情感突生又凋零。",
        type=PromptType.INK_TRANSITION,
        act=Act.SURREAL_NIGHT,
        color_motifs=["lotus_pink", "cobalt_blue"],
        notes="Emotional climax transition"
    ),
]

# ============================================================
# 5. LOCATION PROMPTS
# ============================================================

LOCATION_PROMPTS = [
    Prompt(
        id="location_01",
        title="Shanghai Late-Night Streets",
        prompt_en="Shanghai old-city narrow alleys at night, tight lanes, stone steps, vintage neon signs, sodium streetlights, wet asphalt roads.",
        prompt_zh="上海深夜旧城区，窄巷、台阶、老式霓虹灯、钠灯、湿润柏油路。",
        type=PromptType.LOCATION,
        color_motifs=["cobalt_blue", "sodium_yellow"],
        notes="Primary filming location for night sequences"
    ),
    Prompt(
        id="location_02",
        title="Yunnan Village Memory",
        prompt_en="Yunnan village alley, dark stone paths, thin morning mist, ancient mud walls, soft dawn light.",
        prompt_zh="云南小村落，青石巷道、薄雾、土墙，清晨柔光。",
        type=PromptType.LOCATION,
        color_motifs=["warm_dust_orange", "fog_white"],
        notes="Flashback sequences - nostalgic setting"
    ),
    Prompt(
        id="location_03",
        title="Rooftop at Night (Intimate Scene)",
        prompt_en="Shanghai old apartment rooftop, iron railings, distant neon glow, wind sounds, solitary night atmosphere.",
        prompt_zh="上海老公寓屋顶，铁栏杆、远处霓虹、风声、孤独的夜色。",
        type=PromptType.LOCATION,
        color_motifs=["cobalt_blue", "sodium_yellow"],
        notes="High point for intimate conversation"
    ),
    Prompt(
        id="location_04",
        title="Chengdu Alley",
        prompt_en="Chengdu old alley, hotpot aroma, red lantern reflections on pavement, light smoke atmosphere.",
        prompt_zh="成都老巷子，火锅香气、红灯笼反射在地面、轻烟氛围。",
        type=PromptType.LOCATION,
        color_motifs=["neon_red", "warm_dust_orange"],
        notes="Possible secondary memory location"
    ),
]

# ============================================================
# 6. ACTOR CONSISTENCY PROMPTS
# ============================================================

ACTOR_PROMPTS = [
    Prompt(
        id="actor_01",
        title="Female Lead Consistency",
        prompt_en="Female character: early 30s, delicate features, tired eyes, soft expression, shoulder-length black hair, minimalist clothing, quiet presence, introspective mood.",
        prompt_zh="女性角色：三十出头，精致的面容，疲倦的眼神，柔和的表情，齐肩黑发，极简主义穿着，安静的气质，沉思的情绪。",
        type=PromptType.ACTOR_CONSISTENCY,
        notes="Use for all female lead shots in Runway"
    ),
    Prompt(
        id="actor_02",
        title="Male Lead Consistency",
        prompt_en="Male character: late 30s, slightly unshaven, reserved face, emotionally restrained, professional appearance, subtle sorrow in the eyes.",
        prompt_zh="男性角色：接近四十，胡茬微微显露，保留的面容，情感克制，专业的外表，眼神里隐含哀伤。",
        type=PromptType.ACTOR_CONSISTENCY,
        notes="Use for all male lead shots in Runway"
    ),
]

# ============================================================
# 7. COLOR SCRIPT (COMPLETE EMOTIONAL JOURNEY)
# ============================================================

COLOR_SCRIPT = [
    # ACT I - REUNION
    ColorFrame(
        scene_number=1,
        scene_heading="Reunion Arrival",
        primary_color="Warm Dust Orange",
        secondary_color="Dim Wood Brown",
        emotional_tone="Nostalgic warmth with underlying restraint",
        notes="Faces lit by soft warm lanterns, background: slightly desaturated beige tones, Feeling: 'We've all aged in different directions.'",
        act=Act.REUNION
    ),
    ColorFrame(
        scene_number=2,
        scene_heading="Banquet Hall",
        primary_color="Lantern Gold",
        secondary_color="Red Memory Hues",
        emotional_tone="Lively surface, inner emptiness",
        notes="Warm, cheap, nostalgic banquet light, camera reveals shadows behind smiles, Red décor signals 'history they cannot escape'",
        act=Act.REUNION
    ),
    ColorFrame(
        scene_number=3,
        scene_heading="First Eye Contact",
        primary_color="Flash of Cobalt Blue",
        secondary_color="Warm Orange Foreground",
        emotional_tone="The first chill inside the warmth",
        notes="Blue shadow crosses behind her shoulder, Contrast: orange foreground, blue background, Emotional shift begins",
        act=Act.REUNION
    ),
    ColorFrame(
        scene_number=4,
        scene_heading="Shared Toast",
        primary_color="Two-color split (Warm Gold × Deep Blue)",
        secondary_color="—",
        emotional_tone="Half warmth, half unspoken longing",
        notes="Light from left = warm, Light from right = cold, This duality becomes the film's emotional spine",
        act=Act.REUNION
    ),
    
    # ACT II - AFTER REUNION
    ColorFrame(
        scene_number=13,
        scene_heading="Street Exit",
        primary_color="Fog White",
        secondary_color="Streetlight Yellow",
        emotional_tone="The moment they step into the night",
        notes="Soft fog dissolves the banquet warmth, Shadows lengthen, Symbolic crossing from past to present",
        act=Act.AFTER_REUNION
    ),
    ColorFrame(
        scene_number=14,
        scene_heading="Sidewalk Conversation",
        primary_color="Cobalt Blue",
        secondary_color="Warm Skin Tones",
        emotional_tone="Two people in two emotional temperatures",
        notes="The night is cold, but their faces remain human-warm, Blue expands behind them slowly, Dialogue shifts into emotional honesty",
        act=Act.AFTER_REUNION
    ),
    ColorFrame(
        scene_number=20,
        scene_heading="Alley Passage",
        primary_color="Blue Mist",
        secondary_color="Fog White",
        emotional_tone="Gentle intimacy, time slowing",
        notes="Mist becomes thicker, Edges of frame soften, CHDC ink texture can appear subtly in fog",
        act=Act.AFTER_REUNION
    ),
    ColorFrame(
        scene_number=23,
        scene_heading="Rooftop Scene",
        primary_color="Blue Black",
        secondary_color="Soft Grey Moonlight",
        emotional_tone="Secret calm",
        notes="Clean night air, Small traces of warm memory flicker, Feel like standing inside a breath",
        act=Act.AFTER_REUNION
    ),
    
    # ACT III - SURREAL NIGHT
    ColorFrame(
        scene_number=35,
        scene_heading="The Walk That Breaks Reality",
        primary_color="Ink Black",
        secondary_color="Electric Blue",
        emotional_tone="Universe bending",
        notes="Urban lights distort like wet ink, Color edges smear, Motion blur becomes emotional blur",
        act=Act.SURREAL_NIGHT
    ),
    ColorFrame(
        scene_number=39,
        scene_heading="Dreamlike Memory Returns",
        primary_color="Yunnan Orange",
        secondary_color="Ink Blue",
        emotional_tone="Past and present collapse",
        notes="Warm memory intrudes into cold city, CHDC ink bloom to transition, Light becomes watercolor",
        act=Act.SURREAL_NIGHT
    ),
    ColorFrame(
        scene_number=44,
        scene_heading="Emotional Peak",
        primary_color="Lotus Pink",
        secondary_color="Cobalt Blue",
        emotional_tone="Beauty + heartbreak",
        notes="CHDC lotus splash transition, Pink appears only to symbolize blooming emotion, Immediately swallowed by blue",
        act=Act.SURREAL_NIGHT
    ),
    
    # ACT IV - MORNING AFTER
    ColorFrame(
        scene_number=50,
        scene_heading="Dawn Street",
        primary_color="Fog White",
        secondary_color="Pale Blue",
        emotional_tone="Truth emerges",
        notes="City is washed of color, Soft daylight exposes what night concealed",
        act=Act.MORNING_AFTER
    ),
    ColorFrame(
        scene_number=54,
        scene_heading="Final Parting",
        primary_color="Soft Grey",
        secondary_color="Skin Tone Warmth",
        emotional_tone="Gentle heartbreak",
        notes="Only warmth is on their faces, Background entirely desaturated, Emotional distance visually complete",
        act=Act.MORNING_AFTER
    ),
    ColorFrame(
        scene_number=56,
        scene_heading="Aftermath",
        primary_color="Morning Grey",
        secondary_color="Neutral Light",
        emotional_tone="Life resumes",
        notes="No blue, no neon, Life returns to realism, Audience feels the absence of night's colors",
        act=Act.MORNING_AFTER
    ),
]

# ============================================================
# 8. DIRECTOR'S STATEMENT (BILINGUAL)
# ============================================================

DIRECTOR_STATEMENT_EN = """
🎬 DIRECTOR'S STATEMENT — Sleepless Blue Nights

Sleepless Blue Nights is a film about the silence between two people — the silence of what was once possible, the silence of what will never be, and the silence that lives inside a single night when time briefly loses its shape.

I wanted to explore the emotional terrain that exists between memory and reality — a terrain where desire is not expressed through dramatic confession, but through glances, distance, hesitation, and the quiet pull of the past. For me, the most powerful moments in life are often the ones where nothing "happens" on the surface, yet everything inside is changing.

This film follows two former lovers who meet again at a high-school reunion. Both have moved on, yet both carry unfinished echoes within them. When they step out into the sleepless streets of Shanghai, the night becomes a space where their past and present drift into each other — first gently, then uncontrollably, until the city itself begins to bend under the weight of their unspoken feelings.

Visually, I wanted the night to feel alive — a character of its own. Fog becomes memory. Neon becomes temptation. Ink-black shadows become the things they cannot say. The surreal elements are not fantasy, but emotional truth made visible.

At its heart, Sleepless Blue Nights is not a story about forbidden love, but about the fragile moments when two lives momentarily touch before drifting apart again. It is a film about the beauty of what almost was, and the acceptance of what cannot be.

This is a story that lives in the quiet space between breathing in and breathing out — a story carried by the color blue.
"""

DIRECTOR_STATEMENT_ZH = """
🎬 导演阐述 —《蓝夜未眠》

《蓝夜未眠》讲述的是两个人之间的沉默——
曾经可能发生的沉默、
永远不再发生的沉默、
以及在某个时间失序的夜晚里，那段悬浮在现实与记忆之间的沉默。

我想探索的是一种介于"回忆"与"现实"之间的情感地带。
在这片地带里，渴望不是通过激烈表达来呈现，
而是通过眼神、距离、犹豫、以及对过去的轻微牵引。
生命中最强烈的情绪，往往不是在事件发生时，而是在无声的变化中。

影片讲述一对旧情人在高中同学会上重逢。
他们的生活都已向前，却都带着未曾落地的回声。
当夜幕下的上海将他们包裹起来，他们的过去与现在逐渐交错——
先是轻微的，再是无法抑制的，
直到城市本身都在他们的情感压力下悄然变形。

在视觉上，我希望"夜"本身成为一个角色。
雾是记忆，霓虹是诱惑，
墨色的阴影则是他们说不出口的部分。
片中的超现实，并不是幻想，而是情绪被看见的真实形态。

《蓝夜未眠》不是关于禁忌之爱的故事。
它讲述的是生命中那些短暂而脆弱的瞬间——
当两条人生轨迹短暂靠近，却最终仍要各自漂向远方。

这是一个存在于呼吸之间的故事，
一个被"蓝色"轻轻托起的故事。
"""

# ============================================================
# LIBRARY FUNCTIONS
# ============================================================

def get_prompts_by_type(prompt_type: PromptType) -> List[Prompt]:
    """Get all prompts of a specific type"""
    all_prompts = CONCEPT_PROMPTS + VIDEO_PROMPTS + INK_PROMPTS + LOCATION_PROMPTS + ACTOR_PROMPTS
    return [p for p in all_prompts if p.type == prompt_type]

def get_prompts_by_act(act: Act) -> List[Prompt]:
    """Get prompts for a specific act"""
    all_prompts = CONCEPT_PROMPTS + VIDEO_PROMPTS + INK_PROMPTS + LOCATION_PROMPTS + ACTOR_PROMPTS
    return [p for p in all_prompts if p.act == act]

def get_color_script_by_act(act: Act) -> List[ColorFrame]:
    """Get color script frames for a specific act"""
    return [cf for cf in COLOR_SCRIPT if cf.act == act]

def get_color_motif(motif_id: str) -> Optional[ColorMotif]:
    """Get a specific color motif"""
    return COLOR_MOTIFS.get(motif_id)

def get_prompt_by_id(prompt_id: str) -> Optional[Prompt]:
    """Get a specific prompt by ID"""
    all_prompts = CONCEPT_PROMPTS + VIDEO_PROMPTS + INK_PROMPTS + LOCATION_PROMPTS + ACTOR_PROMPTS
    for p in all_prompts:
        if p.id == prompt_id:
            return p
    return None

def get_library_stats() -> Dict:
    """Get overall library statistics"""
    return {
        "total_prompts": len(CONCEPT_PROMPTS + VIDEO_PROMPTS + INK_PROMPTS + LOCATION_PROMPTS + ACTOR_PROMPTS),
        "concept_images": len(CONCEPT_PROMPTS),
        "video_prompts": len(VIDEO_PROMPTS),
        "ink_transitions": len(INK_PROMPTS),
        "locations": len(LOCATION_PROMPTS),
        "actor_consistency": len(ACTOR_PROMPTS),
        "color_frames": len(COLOR_SCRIPT),
        "color_motifs": len(COLOR_MOTIFS),
    }

def export_prompt_for_generation(prompt: Prompt, include_metadata: bool = True) -> Dict:
    """Export a prompt for actual generation (painter_agent, runway, etc.)"""
    return {
        "id": prompt.id,
        "title": prompt.title,
        "prompt_en": prompt.prompt_en,
        "prompt_zh": prompt.prompt_zh,
        "type": prompt.type.value,
        "color_motifs": prompt.color_motifs,
        "notes": prompt.notes,
        "metadata": {
            "scene_number": prompt.scene_number,
            "act": prompt.act.value if prompt.act else None,
        } if include_metadata else None
    }

# ============================================================
# PRINT FUNCTIONS (FOR DEBUGGING)
# ============================================================

def print_color_motifs():
    """Print all color motifs"""
    print("🎨 COLOR MOTIFS")
    print("=" * 80)
    for motif_id, motif in COLOR_MOTIFS.items():
        print(f"{motif.name} ({motif.hex_code})")
        print(f"  EN: {motif.emotional_meaning_en}")
        print(f"  ZH: {motif.emotional_meaning_zh}")
        print()

def print_library_summary():
    """Print library summary"""
    stats = get_library_stats()
    print("📚 SLEEPLESS BLUE NIGHTS PROMPT LIBRARY")
    print("=" * 80)
    for key, value in stats.items():
        print(f"{key}: {value}")
    print()
    print("Director's Statement: Available in English & Chinese")

if __name__ == "__main__":
    print_library_summary()
    print_color_motifs()
