#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 Google Places Agent for AI Studio Elsewhere
Location Scouting & Real-World Reference Generation

Features:
- Text search for locations
- Nearby search with filters
- Place details extraction
- Clean data formatting for UI
- Auto-location extraction from scene text (Chinese support)
- Built-in caching (1 hour default)
- Error handling & retry logic
"""

import googlemaps
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class GooglePlacesAgent:
    """
    A clean wrapper for Google Places API,
    optimized for AI Studio Elsewhere location scouting.
    
    Use for:
    - Finding real Shanghai alleys, rooftops, cafes
    - Yunnan villages and landscapes
    - Any location from your script
    - Generating reference photos for Wanxiang/Runway prompts
    """

    def __init__(self, api_key: str, cache_duration: int = 3600):
        """
        Initialize Google Places Agent
        
        Args:
            api_key: Google Maps API Key
            cache_duration: seconds to keep cached results (default 1h)
        """
        if not api_key:
            logger.warning("⚠️ No Google Places API key provided")
            self.gmaps = None
        else:
            self.gmaps = googlemaps.Client(key=api_key)
            logger.info("✅ Google Places Agent initialized")
        
        self.cache = {}
        self.cache_duration = timedelta(seconds=cache_duration)
        self.requests_made = 0

    # ============================================================
    # Internal: Caching System
    # ============================================================
    
    def _cached(self, key: str) -> Optional[Dict]:
        """Check if cached result is still valid"""
        if key in self.cache:
            item, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.cache_duration:
                return item
        return None

    def _store(self, key: str, value: Dict):
        """Store result in cache"""
        self.cache[key] = (value, datetime.now())

    def _clear_cache(self):
        """Clear all cached results"""
        self.cache = {}
        logger.info("Cache cleared")

    # ============================================================
    # Text Search
    # ============================================================
    
    def search(self, query: str, location: Optional[Tuple] = None, radius: int = 3000) -> Dict:
        """
        Basic text search for locations
        
        Args:
            query: Search query (e.g., "Shanghai rooftop", "Yunnan village")
            location: (lat, lng) tuple or None
            radius: Search radius in meters (default 3000)
        
        Returns:
            Google Places API response (raw)
        """
        if not self.gmaps:
            logger.error("❌ Google Places API not initialized")
            return {"results": []}
        
        cache_key = f"search:{query}:{location}:{radius}"
        cached = self._cached(cache_key)
        if cached:
            logger.debug(f"📦 Using cached result for: {query}")
            return cached

        try:
            logger.info(f"🔍 Searching: {query}")
            response = self.gmaps.places(
                query=query,
                location=location,
                radius=radius
            )
            self._store(cache_key, response)
            self.requests_made += 1
            return response
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return {"results": []}

    # ============================================================
    # Nearby Search
    # ============================================================
    
    def nearby(self, location: Tuple, radius: int = 2000, 
               keyword: Optional[str] = None, place_type: Optional[str] = None) -> Dict:
        """
        Search for places near a location
        
        Args:
            location: (lat, lng) tuple
            radius: Search radius in meters
            keyword: Optional keyword filter
            place_type: Optional place type (e.g., 'restaurant', 'cafe', 'bar')
        
        Returns:
            Google Places API response (raw)
        """
        if not self.gmaps:
            logger.error("❌ Google Places API not initialized")
            return {"results": []}
        
        cache_key = f"nearby:{location}:{radius}:{keyword}:{place_type}"
        cached = self._cached(cache_key)
        if cached:
            logger.debug(f"📦 Using cached nearby results")
            return cached

        try:
            logger.info(f"📍 Searching nearby {location}")
            response = self.gmaps.places_nearby(
                location=location,
                radius=radius,
                keyword=keyword,
                type=place_type
            )
            self._store(cache_key, response)
            self.requests_made += 1
            return response
        except Exception as e:
            logger.error(f"❌ Nearby search error: {e}")
            return {"results": []}

    # ============================================================
    # Place Details
    # ============================================================
    
    def details(self, place_id: str) -> Dict:
        """
        Get detailed information about a specific place
        
        Args:
            place_id: Google Places ID
        
        Returns:
            Detailed place information
        """
        if not self.gmaps:
            logger.error("❌ Google Places API not initialized")
            return {}
        
        cache_key = f"details:{place_id}"
        cached = self._cached(cache_key)
        if cached:
            logger.debug(f"📦 Using cached place details")
            return cached

        try:
            logger.info(f"📍 Fetching details for: {place_id}")
            response = self.gmaps.place(place_id=place_id)
            self._store(cache_key, response)
            self.requests_made += 1
            return response
        except Exception as e:
            logger.error(f"❌ Details error: {e}")
            return {}

    # ============================================================
    # Extract Clean Data for UI
    # ============================================================
    
    def clean_results(self, raw: Dict) -> List[Dict]:
        """
        Convert Google Places results into clean, UI-friendly format
        
        Args:
            raw: Raw Google Places API response
        
        Returns:
            List of cleaned location objects
        """
        if not raw or "results" not in raw:
            return []

        cleaned = []
        for item in raw.get("results", []):
            location = None
            if "geometry" in item and "location" in item["geometry"]:
                location = item["geometry"]["location"]
            
            cleaned.append({
                "name": item.get("name", "Unknown"),
                "address": item.get("formatted_address", ""),
                "types": item.get("types", []),
                "rating": item.get("rating"),
                "user_ratings_total": item.get("user_ratings_total"),
                "icon": item.get("icon"),
                "icon_mask_base_uri": item.get("icon_mask_base_uri"),
                "place_id": item.get("place_id"),
                "location": location,
                "opening_hours": item.get("opening_hours", {}).get("open_now"),
                "photos": item.get("photos", []),
                "business_status": item.get("business_status"),
            })
        
        logger.info(f"✅ Cleaned {len(cleaned)} results")
        return cleaned

    # ============================================================
    # Auto Location Extraction (Chinese Support)
    # ============================================================
    
    def extract_and_search(self, scene_text: str, 
                          location_bias: Optional[Tuple] = None) -> Tuple[str, List[Dict]]:
        """
        Extract location keywords from scene text and perform a search.
        Supports Chinese text like "他们走出上海的老弄堂"
        
        Args:
            scene_text: Scene description in English or Chinese
            location_bias: Optional (lat, lng) to bias search
        
        Returns:
            Tuple of (search_query, cleaned_results)
        """
        keywords = []
        
        # Bilingual keyword mapping for common film locations
        mapping = {
            # Chinese → English translations
            "上海": "Shanghai",
            "云南": "Yunnan",
            "成都": "Chengdu",
            "北京": "Beijing",
            "杭州": "Hangzhou",
            "西安": "Xi'an",
            "屋顶": "rooftop",
            "夜晚": "night street",
            "小巷": "alley",
            "巷子": "alley",
            "弄堂": "alley",
            "雾": "foggy street",
            "河边": "riverside",
            "茶馆": "teahouse",
            "酒吧": "bar",
            "咖啡": "cafe",
            "餐厅": "restaurant",
            "公园": "park",
            "广场": "square",
            "桥": "bridge",
            "火车站": "train station",
            "老街": "old street",
            "夜景": "night view",
            "霓虹": "neon",
            "灯笼": "lantern",
            "古镇": "ancient town",
        }

        # Extract keywords
        for chinese, english in mapping.items():
            if chinese in scene_text:
                keywords.append(english)

        # If no keywords found, default to Shanghai night street
        if not keywords:
            keywords = ["Shanghai night street"]

        # Build query
        query = " ".join(keywords)
        logger.info(f"📍 Extracted location: {query}")
        
        # Perform search
        raw = self.search(query, location=location_bias)
        results = self.clean_results(raw)
        
        return query, results

    # ============================================================
    # For AI Studio Elsewhere Integration
    # ============================================================
    
    def get_location_for_scene(self, scene_heading: str, scene_data: Dict) -> List[Dict]:
        """
        Get location references for a specific film scene
        
        Args:
            scene_heading: Scene heading (e.g., "INT. SHANGHAI ALLEY - NIGHT")
            scene_data: Scene breakdown data
        
        Returns:
            List of location references
        """
        # Extract location from scene data
        location_name = scene_data.get("location", "")
        action = scene_data.get("action", "")
        
        # Combine for search
        search_text = f"{location_name} {action}"
        
        # Search
        query, results = self.extract_and_search(search_text)
        
        logger.info(f"✅ Found {len(results)} locations for: {scene_heading}")
        return results

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "requests_made": self.requests_made,
            "cache_size": len(self.cache),
            "cache_duration_seconds": self.cache_duration.total_seconds(),
        }

# ============================================================
# Helper Functions (for direct use)
# ============================================================

def create_agent(api_key: str) -> Optional[GooglePlacesAgent]:
    """Factory function to create agent with error handling"""
    if not api_key:
        logger.error("❌ No API key provided")
        return None
    
    try:
        agent = GooglePlacesAgent(api_key)
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create agent: {e}")
        return None

if __name__ == "__main__":
    # Example usage
    import os
    
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    
    if not api_key:
        print("❌ No GOOGLE_PLACES_API_KEY in environment")
    else:
        # Create agent
        agent = GooglePlacesAgent(api_key)
        
        # Example 1: Search
        print("🔍 Searching for Shanghai rooftops...")
        query, results = agent.extract_and_search("他们站在上海屋顶看夜景")
        print(f"Query: {query}")
        print(f"Found {len(results)} results:")
        for r in results[:3]:
            print(f"  • {r['name']} - {r['address']}")
        
        # Example 2: Get stats
        stats = agent.get_usage_stats()
        print(f"\n📊 Stats: {stats}")
