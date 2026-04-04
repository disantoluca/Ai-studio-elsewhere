#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
💳 AI Studio Elsewhere - Subscription & Payment System
Stripe integration for monetization

Features:
- Freemium model
- Subscription tiers (Basic, Pro, Studio)
- Usage-based billing
- Feature gating
"""

import os
import json
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("⚠️ Stripe not installed. Run: pip install stripe")

# ============================================================
# SUBSCRIPTION TIERS
# ============================================================

@dataclass
class SubscriptionTier:
    """Subscription tier definition"""
    name: str
    price_monthly: float
    price_yearly: float
    description: str
    features: Dict[str, bool]
    stripe_price_id: Optional[str] = None

# Define tiers
TIERS = {
    "free": SubscriptionTier(
        name="Free",
        price_monthly=0,
        price_yearly=0,
        description="Get started with AI Studio",
        features={
            "script_upload": True,
            "scene_breakdown": True,
            "concept_images": False,
            "video_generation": False,
            "location_scouting": True,
            "prompt_library": True,
            "multi_angle": False,
            "batch_generation": False,
            "export": False,
            "api_calls_per_month": 0,
        }
    ),
    "pro": SubscriptionTier(
        name="Pro",
        price_monthly=9.99,
        price_yearly=99.99,
        description="For individual filmmakers",
        features={
            "script_upload": True,
            "scene_breakdown": True,
            "concept_images": True,
            "video_generation": True,
            "location_scouting": True,
            "prompt_library": True,
            "multi_angle": True,
            "batch_generation": False,
            "export": True,
            "api_calls_per_month": 100,
        }
    ),
    "studio": SubscriptionTier(
        name="Studio",
        price_monthly=49.99,
        price_yearly=499.99,
        description="For production studios",
        features={
            "script_upload": True,
            "scene_breakdown": True,
            "concept_images": True,
            "video_generation": True,
            "location_scouting": True,
            "prompt_library": True,
            "multi_angle": True,
            "batch_generation": True,
            "export": True,
            "api_calls_per_month": 1000,
        }
    ),
}

# ============================================================
# SUBSCRIPTION MANAGER
# ============================================================

class SubscriptionManager:
    """Manage user subscriptions and feature access"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize subscription manager
        
        Args:
            api_key: Stripe API key
        """
        self.api_key = api_key or os.getenv("STRIPE_SECRET_KEY")
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        
        if self.api_key and STRIPE_AVAILABLE:
            stripe.api_key = self.api_key
            self.available = True
            logger.info("✅ Stripe subscription manager initialized")
        else:
            self.available = False
            logger.warning("⚠️ Stripe not configured")
        
        self.users = {}  # In-memory user subscriptions (use database in production)
    
    # ============================================================
    # PAYMENT LINKS
    # ============================================================
    
    def get_checkout_url(self, tier: str, email: str, interval: str = "month") -> str:
        """
        Get Stripe checkout URL for a tier
        
        Args:
            tier: Subscription tier (pro, studio)
            email: User email
            interval: "month" or "year"
        
        Returns:
            Checkout URL
        """
        if not self.available:
            logger.error("❌ Stripe not configured")
            return ""
        
        if tier == "free":
            return ""  # No checkout for free tier
        
        tier_config = TIERS.get(tier)
        if not tier_config:
            return ""
        
        try:
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"AI Studio Elsewhere - {tier_config.name}",
                                "description": tier_config.description,
                            },
                            "unit_amount": int(tier_config.price_monthly * 100),
                            "recurring": {
                                "interval": interval,
                                "interval_count": 1 if interval == "month" else 12,
                            },
                        },
                        "quantity": 1,
                    }
                ],
                mode="subscription",
                customer_email=email,
                success_url="https://aistudioelsewhere.com/success",
                cancel_url="https://aistudioelsewhere.com/cancel",
            )
            
            logger.info(f"✅ Checkout session created: {session.id}")
            return session.url
        
        except Exception as e:
            logger.error(f"❌ Checkout error: {e}")
            return ""
    
    # ============================================================
    # USER SUBSCRIPTION
    # ============================================================
    
    def get_user_tier(self, user_id: str) -> str:
        """Get user's current subscription tier"""
        return self.users.get(user_id, {}).get("tier", "free")
    
    def set_user_tier(self, user_id: str, tier: str, stripe_customer_id: Optional[str] = None):
        """Set user's subscription tier"""
        if tier not in TIERS:
            logger.error(f"Invalid tier: {tier}")
            return
        
        self.users[user_id] = {
            "tier": tier,
            "stripe_customer_id": stripe_customer_id,
            "subscribed_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        }
        
        logger.info(f"✅ User {user_id} upgraded to {tier}")
    
    # ============================================================
    # FEATURE ACCESS
    # ============================================================
    
    def has_feature(self, user_id: str, feature: str) -> bool:
        """Check if user has access to a feature"""
        tier = self.get_user_tier(user_id)
        tier_config = TIERS.get(tier)
        
        if not tier_config:
            return False
        
        return tier_config.features.get(feature, False)
    
    def get_feature_status(self, user_id: str) -> Dict[str, bool]:
        """Get all feature access for user"""
        tier = self.get_user_tier(user_id)
        tier_config = TIERS.get(tier)
        
        if not tier_config:
            return {}
        
        return tier_config.features
    
    def get_api_quota(self, user_id: str) -> int:
        """Get monthly API call quota"""
        tier = self.get_user_tier(user_id)
        tier_config = TIERS.get(tier)
        
        if not tier_config:
            return 0
        
        return tier_config.features.get("api_calls_per_month", 0)
    
    # ============================================================
    # USAGE TRACKING
    # ============================================================
    
    def track_api_call(self, user_id: str):
        """Track an API call for usage-based billing"""
        if user_id not in self.users:
            self.users[user_id] = {"usage": 0}
        
        self.users[user_id]["usage"] = self.users[user_id].get("usage", 0) + 1
        
        logger.info(f"API call tracked for {user_id}. Total: {self.users[user_id]['usage']}")
    
    def get_usage(self, user_id: str) -> int:
        """Get current month's API usage"""
        return self.users.get(user_id, {}).get("usage", 0)
    
    def reset_monthly_usage(self, user_id: str):
        """Reset monthly usage counter"""
        if user_id in self.users:
            self.users[user_id]["usage"] = 0

# ============================================================
# GLOBAL INSTANCE
# ============================================================

_subscription_manager: Optional[SubscriptionManager] = None

def get_subscription_manager() -> SubscriptionManager:
    """Get or create global subscription manager"""
    global _subscription_manager
    if _subscription_manager is None:
        _subscription_manager = SubscriptionManager()
    return _subscription_manager

if __name__ == "__main__":
    # Demo
    manager = SubscriptionManager()
    
    print("🎬 AI Studio Elsewhere - Subscription Tiers")
    print("=" * 60)
    
    for tier_name, tier in TIERS.items():
        print(f"\n💳 {tier.name}")
        print(f"   Price: ${tier.price_monthly}/month (${tier.price_yearly}/year)")
        print(f"   Description: {tier.description}")
        print(f"   API Calls/Month: {tier.features['api_calls_per_month']}")
        print(f"   Features:")
        for feature, enabled in tier.features.items():
            if feature != "api_calls_per_month":
                status = "✅" if enabled else "❌"
                print(f"      {status} {feature.replace('_', ' ').title()}")
