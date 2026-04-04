#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Scene 1 - Opening Banquet Hall
Runway Video Generation Prompts for "Sleepless Blue Nights"

Ready to paste directly into Runway Gen-3 Alpha
"""

SCENE_1_METADATA = {
    "scene_number": 1,
    "heading": "INT. 1980S SHANGHAI BANQUET HALL - NIGHT",
    "location": "High-school reunion venue",
    "time": "Evening",
    "mood": "Nostalgic, tense, melancholic",
    "color_scheme": "Warm lantern yellow + Deep cobalt blue shadows",
    "visual_reference": "Wong Kar-wai, slow cinema, poetic realism"
}

# ============================================================
# ESTABLISHING SHOT (5-7 seconds)
# ============================================================

ESTABLISHING_SHOT = {
    "id": "scene_1_establishing",
    "type": "establishing",
    "duration": 6,
    "prompt_en": """1980s-style Shanghai high-school reunion banquet hall at night. Warm lantern glow 
    illuminates cheap red tablecloths and worn wooden chairs. Soft haze drifts through the air. 
    Nostalgic atmosphere. People chatting softly in the background. Slow cinema mood. 
    Shallow depth of field. Poetic realism. Film grain texture. 35mm lens feel.""",
    
    "prompt_zh": """80年代风格的上海高中同学会宴会厅，夜间。暖黄色灯笼光照亮廉价红桌布和旧木椅。
    轻微烟雾飘散在空气中。怀旧氛围。背景有人轻声交谈。慢电影质感。浅景深。诗意现实主义。
    胶片纹理。35毫米镜头感觉。""",
    
    "motion": "dolly_in",
    "motion_description": "Slow push-in, slight handheld, 35mm lens feel",
    "style": "cinematic",
    "notes": "Opening shot - establish venue and mood"
}

# ============================================================
# EMOTIONAL ATMOSPHERE SHOT (5-7 seconds)
# ============================================================

ATMOSPHERE_SHOT = {
    "id": "scene_1_atmosphere",
    "type": "atmosphere",
    "duration": 6,
    "prompt_en": """Slow pan across banquet tables with empty seats. Condensation droplets on glasses. 
    Warm lights reflecting on cheap red tablecloths. Fog drifting subtly through air. 
    Emotional distance between people. Nostalgic melancholy. Deep cobalt blue shadows in corners. 
    Wong Kar-wai mood. Cinematic grain. Poetic stillness.""",
    
    "prompt_zh": """缓缓平移过宴会桌，座位空荡荡的。玻璃杯上的冷凝水珠。暖光反射在廉价红桌布上。
    雾气在空气中缓缓飘散。人群之间的情感距离。怀旧忧郁。角落里深钴蓝色的阴影。
    王家卫风格。电影纹理。诗意的静寂。""",
    
    "motion": "pan_left",
    "motion_description": "Left-to-right slow pan, soft motion blur, film grain",
    "style": "cinematic",
    "notes": "Mood establishment - emphasize emptiness and anticipation"
}

# ============================================================
# CLASSMATES MID-SHOT (5-7 seconds)
# ============================================================

CLASSMATES_SHOT = {
    "id": "scene_1_classmates",
    "type": "character",
    "duration": 6,
    "prompt_en": """Classmates talking politely at banquet table. Subtle tension under the surface. 
    Warm lantern lighting illuminates faces. Fog-softened air creates dreamy quality. 
    Vintage 1980s atmosphere. Realistic but poetic. Deep blue shadows behind them. 
    Unspoken emotions visible in their expressions. Handheld camera slight movement.""",
    
    "prompt_zh": """同学们在宴会桌前有礼貌地交谈。表面之下的微妙张力。暖黄灯笼光照亮脸庞。
    被雾气柔化的空气营造梦幻感。80年代复古氛围。真实又诗意。身后有深蓝色阴影。
    未诉说的情感在表情中可见。手持摄像机略微运动。""",
    
    "motion": "static",
    "motion_description": "Shoulder-level shot, slight dolly sideways",
    "style": "cinematic",
    "notes": "Character focus - show underlying emotions and connections"
}

# ============================================================
# INK TRANSITION VARIANT (3-5 seconds)
# ============================================================

INK_TRANSITION = {
    "id": "scene_1_ink_transition",
    "type": "transition",
    "duration": 4,
    "prompt_en": """Warm banquet hall scene dissolving into an ink splash transition. Ink blooming 
    across the screen like Zhang Daqian brushwork. Warm orange light fading into deep cobalt blue. 
    CHDC ink dynamics. Surreal but soft. Poetic transformation. Traditional Chinese painting style 
    merging with cinematic reality.""",
    
    "prompt_zh": """暖色宴会厅场景溶解成墨迹飞溅的过渡。墨水像张大千笔触一样在屏幕上绽放。
    暖橙光褪去成深钴蓝。CHDC墨迹动力学。超现实但柔和。诗意的变换。传统中国绘画风格与电影现实融合。""",
    
    "motion": "static",
    "motion_description": "Static shot → ink overtakes frame",
    "style": "experimental",
    "notes": "Surreal transition - bridge to emotional revelation"
}

# ============================================================
# MOOD SHOT - FOG & LANTERN (4-6 seconds)
# ============================================================

MOOD_SHOT = {
    "id": "scene_1_mood",
    "type": "mood",
    "duration": 5,
    "prompt_en": """Single lantern swinging gently in the wind. Fog drifting beneath warm light. 
    Lantern flickering softly. Nostalgic, dreamy atmosphere. Subtle melancholy. 
    Soft focus photography. Shallow depth of field. Poetic loneliness. Time suspended. 
    Wong Kar-wai inspired color grading.""",
    
    "prompt_zh": """单个灯笼在风中轻轻摇晃。雾气在暖光下飘散。灯笼柔和闪烁。怀旧、梦幻的氛围。
    细微的忧郁。柔焦摄影。浅景深。诗意的孤独。时间悬停。王家卫启发的色彩分级。""",
    
    "motion": "tilt_up",
    "motion_description": "Slow tilt-up, slight vignette bleed",
    "style": "cinematic",
    "notes": "Lyrical moment - emotional essence of scene"
}

# ============================================================
# MULTI-ANGLE PACK
# ============================================================

MULTI_ANGLE_SHOTS = {
    "wide_establishing": {
        "angle": "wide",
        "prompt_en": "Wide establishing shot of entire reunion banquet hall, warm lanterns, electric fans, cheap festive decor, slight haze, warm-to-blue color tension, poetic and quiet undertone.",
        "prompt_zh": "整个同学会宴会厅的宽阔镜头，暖灯笼，电风扇，廉价节庆装饰，轻微雾气，暖到蓝色的色彩张力，诗意宁静的基调。"
    },
    "mid_two_shot": {
        "angle": "medium",
        "prompt_en": "Medium shot of two classmates sitting across from each other, warm lantern light between them, subtle tension, nostalgic sadness, fog softening the scene.",
        "prompt_zh": "两个同学相对而坐的中景，暖灯笼光在他们之间，微妙的张力，怀旧的悲伤，雾气柔化场景。"
    },
    "close_up_portrait": {
        "angle": "close",
        "prompt_en": "Close-up portrait of single classmate, warm lantern glow on face, deep blue shadows, years of untold stories visible in expression, fog in background.",
        "prompt_zh": "单个同学的近景肖像，暖灯笼光照亮脸庞，深蓝色阴影，未诉说的故事岁月在表情中可见，背景有雾。"
    },
    "object_macro": {
        "angle": "macro",
        "prompt_en": "Macro shot of nostalgic banquet props: fog-softened lanterns, old name tags, cheap red tablecloth fibers, condensation on glasses, soft haze, poetic realism.",
        "prompt_zh": "怀旧宴会道具的微距镜头：被雾柔化的灯笼，旧名牌，廉价红桌布纤维，玻璃上的冷凝水，柔和雾霾，诗意现实主义。"
    },
    "low_angle_approach": {
        "angle": "low",
        "prompt_en": "Low angle slow approach toward banquet table, looking up at people, emphasizing their presence and dominance, warm light above, cooler shadows below.",
        "prompt_zh": "低角度缓慢靠近宴会桌，向上看向人们，强调他们的存在和支配力，上方暖光，下方较冷阴影。"
    },
    "over_shoulder": {
        "angle": "over_shoulder",
        "prompt_en": "Over-the-shoulder shot as if listening to whispered words, warm light on face, blurred figure in foreground, intimate but distant feeling.",
        "prompt_zh": "过肩镜头，仿佛在听低声细语，脸上有暖光，前景模糊人物，亲密但遥远的感觉。"
    }
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_all_scene_1_videos():
    """Get all video prompts for Scene 1"""
    return {
        "establishing": ESTABLISHING_SHOT,
        "atmosphere": ATMOSPHERE_SHOT,
        "classmates": CLASSMATES_SHOT,
        "ink_transition": INK_TRANSITION,
        "mood": MOOD_SHOT,
    }

def get_scene_1_multi_angles():
    """Get multi-angle variations"""
    return MULTI_ANGLE_SHOTS

def get_scene_1_metadata():
    """Get scene metadata"""
    return SCENE_1_METADATA

def format_runway_prompt(shot_dict: dict) -> str:
    """Format a shot dict into a Runway-ready prompt"""
    return f"""{shot_dict['prompt_en']}

Motion: {shot_dict['motion_description']}
Duration: {shot_dict['duration']}s
Style: {shot_dict['style']}"""

if __name__ == "__main__":
    import json
    
    print("🎬 Scene 1 - Sleepless Blue Nights")
    print("=" * 60)
    print("\nMetadata:")
    print(json.dumps(SCENE_1_METADATA, indent=2, ensure_ascii=False))
    
    print("\n\nVideo Shots:")
    for shot_name, shot_data in get_all_scene_1_videos().items():
        print(f"\n📹 {shot_name.upper()}")
        print(f"   Duration: {shot_data['duration']}s")
        print(f"   Motion: {shot_data['motion']}")
        print(f"   Prompt: {shot_data['prompt_en'][:100]}...")
    
    print("\n\nMulti-Angle Variations:")
    for angle_name in get_scene_1_multi_angles().keys():
        print(f"   • {angle_name}")
