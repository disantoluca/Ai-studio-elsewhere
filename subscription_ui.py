#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💳 Subscription UI for AI Studio Elsewhere
Beautiful paywall and tier selection interface
"""

import streamlit as st
from subscription_manager import get_subscription_manager, TIERS
import logging

logger = logging.getLogger(__name__)

def display_subscription_modal():
    """Display subscription modal/paywall"""
    
    manager = get_subscription_manager()
    
    # Get user from session
    user_id = st.session_state.get("user_id", "guest")
    current_tier = manager.get_user_tier(user_id)
    
    st.header("💳 Upgrade Your Plan")
    st.write("Unlock full AI Studio capabilities for filmmaking")
    
    # Display tiers in columns
    col1, col2, col3 = st.columns(3)
    
    with col1:
        display_tier_card("free", TIERS["free"], current_tier)
    
    with col2:
        display_tier_card("pro", TIERS["pro"], current_tier)
    
    with col3:
        display_tier_card("studio", TIERS["studio"], current_tier)

def display_tier_card(tier_id: str, tier, current_tier: str):
    """Display a single tier card"""
    
    is_current = tier_id == current_tier
    
    with st.container(border=True):
        # Tier name
        if is_current:
            st.write(f"### ✅ {tier.name}")
        else:
            st.write(f"### {tier.name}")
        
        # Price
        st.write(f"**${tier.price_monthly}/month**")
        st.caption(f"or ${tier.price_yearly}/year (save 17%)")
        
        # Description
        st.write(tier.description)
        
        st.markdown("---")
        
        # Features list
        st.write("**Features:**")
        
        feature_names = {
            "script_upload": "📄 Script Upload",
            "scene_breakdown": "🎬 Scene Breakdown",
            "concept_images": "🎨 Concept Images",
            "video_generation": "🎥 Video Generation (Runway)",
            "location_scouting": "🌍 Location Scouting",
            "prompt_library": "📚 Prompt Library",
            "multi_angle": "🔄 Multi-Angle Videos",
            "batch_generation": "📹 Batch Processing",
            "export": "💾 Export & Download",
            "api_calls_per_month": "📊 API Quota",
        }
        
        for feature, label in feature_names.items():
            if feature == "api_calls_per_month":
                quota = tier.features[feature]
                if quota > 0:
                    st.write(f"✅ {quota} API calls/month")
                else:
                    st.write(f"❌ Limited API access")
            else:
                enabled = tier.features[feature]
                icon = "✅" if enabled else "❌"
                st.write(f"{icon} {label}")
        
        st.markdown("---")
        
        # Action button
        if is_current:
            st.button(f"✅ Current Plan", disabled=True, use_container_width=True)
        elif tier_id == "free":
            if st.button("📥 Use Free Plan", use_container_width=True):
                st.session_state.user_tier = "free"
                st.success("Using free plan")
        else:
            if st.button(f"🚀 Upgrade to {tier.name}", use_container_width=True):
                email = st.session_state.get("user_email", "user@example.com")
                checkout_url = get_subscription_manager().get_checkout_url(tier_id, email)
                
                if checkout_url:
                    st.write(f"[💳 Go to Checkout]({checkout_url})")
                else:
                    st.warning("Payment system not configured")

def check_feature_access(feature: str) -> bool:
    """Check if current user has access to a feature"""
    
    manager = get_subscription_manager()
    user_id = st.session_state.get("user_id", "guest")
    
    has_access = manager.has_feature(user_id, feature)
    
    if not has_access:
        tier = manager.get_user_tier(user_id)
        st.warning(f"⭐ This feature requires an upgrade from {tier if tier else 'Free'} plan")
        st.write("Upgrade to Pro or Studio to unlock this feature")
        
        if st.button("🚀 See Pricing Plans"):
            st.switch_page("pages/pricing.py")
    
    return has_access

def display_feature_gate(feature: str, feature_name: str = ""):
    """Gate a feature behind subscription"""
    
    manager = get_subscription_manager()
    user_id = st.session_state.get("user_id", "guest")
    
    if not manager.has_feature(user_id, feature):
        st.error(f"🔒 {feature_name or feature} - Upgrade Required")
        
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("💳 Upgrade Now", use_container_width=True):
                display_subscription_modal()
        
        return False
    
    return True

def display_usage_info():
    """Display user's usage and quota"""
    
    manager = get_subscription_manager()
    user_id = st.session_state.get("user_id", "guest")
    
    tier = manager.get_user_tier(user_id)
    quota = manager.get_api_quota(user_id)
    usage = manager.get_usage(user_id)
    
    if quota > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Plan", tier.title())
        with col2:
            st.metric("API Usage", f"{usage}/{quota}")
        with col3:
            percentage = (usage / quota * 100) if quota > 0 else 0
            st.metric("% Used", f"{percentage:.1f}%")
        
        if usage > quota:
            st.error("⚠️ API quota exceeded. Upgrade to continue.")

if __name__ == "__main__":
    st.set_page_config(page_title="Pricing", layout="wide")
    display_subscription_modal()
