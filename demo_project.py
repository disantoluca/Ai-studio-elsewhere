#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo Project Data — "The Last Night Tram"
A safe, professional demo film for AI Studio Elsewhere
No IP risk, emotionally strong, matches visual system perfectly
"""

def load_demo_project():
    """Load the complete demo film project"""
    return {
        "title": "The Last Night Tram",
        "title_zh": "夜晚最后一班电车",
        "director": "Demo Director",
        "logline_en": (
            "A woman boards the last tram of the night, only to realize that each stop "
            "pulls her deeper into memories she never chose to revisit — until the final "
            "station reveals a truth she can no longer escape."
        ),
        "logline_zh": (
            "一名女子登上夜晚的最后一班电车，却发现每一站都将她带入未曾选择回望的记忆，"
            "直到终点，她不得不面对一个无法逃避的真相。"
        ),
        "metadata": {
            "genre": "Drama / Poetic Realism",
            "setting": "Urban Night / City Tram",
            "tone": ["melancholic", "dreamlike", "quiet", "nostalgic"],
            "visual_style": "slow cinema, surreal realism, fog, night",
        },
        "scenes": [
            {
                "id": 1,
                "number": 1,
                "title": "Scene 1 — The Boarding",
                "title_zh": "场景1 — 登车",
                "text_en": (
                    "INT. NIGHT TRAM — LATE NIGHT\n\n"
                    "A nearly empty tram. Fluorescent lights flicker softly. "
                    "A woman steps in. The doors close behind her silently. "
                    "She is alone.\n\n"
                    "She finds a seat by the window and looks out at the dark city."
                ),
                "text_zh": (
                    "内景。夜间电车。深夜\n\n"
                    "几乎空荡荡的电车。荧光灯柔和地闪烁。一个女人踏上电车。"
                    "车门在她身后无声地关闭。她独自一人。\n\n"
                    "她找到靠窗的座位，看着黑暗的城市。"
                ),
                "mood": ["melancholic", "anticipation", "suspended time", "stillness"],
                "location": "night tram interior",
                "visual_prompt": (
                    "Empty night tram interior, cold blue tones, fluorescent flickering lights, "
                    "reflections on glass windows, minimal passengers, cinematic stillness, "
                    "slow cinema mood, melancholic atmosphere, soft haze."
                ),
                "video_prompt": (
                    "Woman entering an empty tram at late night, fluorescent flickering lights, "
                    "cold blue tones, quiet atmosphere, cinematic slow motion, soft handheld camera, "
                    "slow dolly-in, melancholic mood, 4 seconds."
                ),
            },
            {
                "id": 2,
                "number": 2,
                "title": "Scene 2 — The Memory Stops",
                "title_zh": "场景2 — 记忆站点",
                "text_en": (
                    "INT./EXT. TRAM WINDOWS — MOVING THROUGH CITY\n\n"
                    "The tram moves through the night city. At each stop, something shifts.\n\n"
                    "Through the window reflections, we see fragments of her past:\n"
                    "• A childhood street\n"
                    "• A lost relationship\n"
                    "• A moment she regrets\n\n"
                    "The outside world feels unreal. The past bleeds into the present."
                ),
                "text_zh": (
                    "内景/外景。电车窗户。穿过城市\n\n"
                    "电车在夜间城市中移动。每一站，都有什么转变了。\n\n"
                    "通过窗户的反射，我们看到她过去的碎片：\n"
                    "• 儿时的街道\n"
                    "• 失去的爱\n"
                    "• 一个她遗憾的时刻\n\n"
                    "外面的世界感觉不真实。过去融入了现在。"
                ),
                "mood": ["surreal", "nostalgic", "emotional pull", "dreamlike"],
                "location": "moving city reflections",
                "visual_prompt": (
                    "Tram window showing surreal reflection of childhood street blending with present city, "
                    "warm nostalgic tones mixed with cold night blue, slight distortion, dreamlike haze, "
                    "poetic realism, memories bleeding through glass, ethereal fog."
                ),
                "video_prompt": (
                    "City reflections in tram window morphing into memories, surreal transitions, "
                    "warm and cold tones blending, soft fog, cinematic slow motion, side tracking shot, "
                    "reflections emphasized, melancholic mood, 5 seconds."
                ),
            },
            {
                "id": 3,
                "number": 3,
                "title": "Scene 3 — The Final Station",
                "title_zh": "场景3 — 终点站",
                "text_en": (
                    "EXT. EMPTY TERMINAL — PRE-DAWN\n\n"
                    "The tram stops. The doors open. She stands and walks out slowly.\n\n"
                    "The platform is empty. No one else gets off.\n\n"
                    "She steps into silence. The city around her is unfamiliar. "
                    "The light is pale blue. Mist hangs in the air.\n\n"
                    "She stands alone, finally still."
                ),
                "text_zh": (
                    "外景。空荡的车站。黎明前\n\n"
                    "电车停下。车门打开。她缓缓站起，走出去。\n\n"
                    "站台是空的。没有其他人下车。\n\n"
                    "她踏入寂静。周围的城市陌生而遥远。"
                    "光线是淡蓝色的。雾气笼罩在空气中。\n\n"
                    "她独自站着，终于静止下来。"
                ),
                "mood": ["stillness", "acceptance", "solitude", "resolution"],
                "location": "empty station at dawn",
                "visual_prompt": (
                    "Empty tram station at pre-dawn, pale blue light, mist in the air, "
                    "long shadows on platform, minimalist architecture, quiet atmosphere, "
                    "emotional stillness, cinematic composition, solitude."
                ),
                "video_prompt": (
                    "Woman stepping off tram at empty station before dawn, pale blue light, mist, "
                    "slow wide shot pulling back, long shadows, quiet atmosphere, still cinematic mood, "
                    "emotional resolution, 4 seconds."
                ),
            }
        ]
    }


def get_demo_script():
    """Script for live demo — what you say to directors"""
    return {
        "opening": (
            "Let me show you something. This is not a finished film — "
            "this is just an idea. A concept we're developing together."
        ),
        "step_1": (
            "Imagine a simple scenario: a woman boards the last tram of the night. "
            "That's it. Just that moment."
        ),
        "step_2": (
            "The system automatically understands the structure. "
            "It finds the scenes, the mood, the emotional journey."
        ),
        "step_3": (
            "Now let's see what this world looks like. "
            "Not through a camera — through the system's understanding of the story."
        ),
        "step_4": (
            "We can generate images. We can test scenes. We can explore the mood."
        ),
        "step_5": (
            "This is before casting. Before shooting. Before production. "
            "This is imagination made visible. This is thinking like a director."
        ),
        "closing": (
            "And because it's instant, you can iterate. You can change. "
            "You can explore every possibility before you spend a single dollar on production."
        ),
        "final": (
            "Now imagine this is YOUR film. What would you explore first?"
        )
    }
