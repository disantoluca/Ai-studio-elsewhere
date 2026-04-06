#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🌍 Google Places Agent for Location Scouting
For AI Studio Elsewhere

Uses the googlemaps library to search for real-world filming locations.
Directors can search by scene description and get photos, ratings, addresses.
"""

import os
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import googlemaps
    GMAPS_AVAILABLE = True
except ImportError:
    GMAPS_AVAILABLE = False
    logger.warning("⚠️ googlemaps not installed")


class GooglePlacesAgent:
    """Agent for searching real-world filming locations via Google Places"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_PLACES_API_KEY")
        self.client = None
        self.available = False
        
        if not GMAPS_AVAILABLE:
            logger.error("❌ googlemaps library not installed")
            return
        
        if not self.api_key:
            logger.warning("⚠️ No Google Places API key")
            return
        
        try:
            self.client = googlemaps.Client(key=self.api_key)
            self.available = True
            logger.info("✅ Google Places Agent initialized")
        except Exception as e:
            logger.error(f"❌ Failed to init Google Places: {e}")
    
    def search_locations(self, query: str, max_results: int = 5) -> List[Dict]:
        """
        Search for locations matching a query.
        
        Args:
            query: Search query (e.g., "abandoned tram station", "rooftop bar Shanghai")
            max_results: Max results to return
            
        Returns:
            List of location dicts with name, address, rating, photos, etc.
        """
        if not self.available:
            return []
        
        try:
            results = self.client.places(query=query)
            locations = []
            
            for place in results.get("results", [])[:max_results]:
                location = {
                    "place_id": place.get("place_id", ""),
                    "name": place.get("name", "Unknown"),
                    "address": place.get("formatted_address", ""),
                    "rating": place.get("rating", 0),
                    "user_ratings_total": place.get("user_ratings_total", 0),
                    "types": place.get("types", []),
                    "lat": place.get("geometry", {}).get("location", {}).get("lat", 0),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng", 0),
                    "photo_refs": [],
                }
                
                # Extract photo references
                for photo in place.get("photos", [])[:3]:
                    location["photo_refs"].append(photo.get("photo_reference", ""))
                
                locations.append(location)
            
            logger.info(f"✅ Found {len(locations)} locations for '{query}'")
            return locations
            
        except Exception as e:
            logger.error(f"❌ Location search failed: {e}")
            return []
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get detailed info about a specific place"""
        if not self.available:
            return None
        
        try:
            result = self.client.place(
                place_id=place_id,
                fields=[
                    "name", "formatted_address", "formatted_phone_number",
                    "rating", "review", "photo", "opening_hours",
                    "website", "url", "type", "geometry"
                ]
            )
            return result.get("result", {})
        except Exception as e:
            logger.error(f"❌ Place details failed: {e}")
            return None
    
    def get_photo_url(self, photo_reference: str, max_width: int = 800) -> str:
        """
        Get a photo URL from a photo reference.
        
        Note: This returns a URL that redirects to the actual photo.
        """
        if not self.api_key or not photo_reference:
            return ""
        
        return (
            f"https://maps.googleapis.com/maps/api/place/photo"
            f"?maxwidth={max_width}"
            f"&photo_reference={photo_reference}"
            f"&key={self.api_key}"
        )
    
    def search_for_scene(self, scene_location: str, scene_mood: str = "", 
                         scene_time: str = "") -> List[Dict]:
        """
        Smart search tailored for film scene locations.
        Builds a query from scene metadata.
        
        Args:
            scene_location: e.g., "night tram interior", "empty station"
            scene_mood: e.g., "melancholic", "surreal"
            scene_time: e.g., "Night", "Dawn"
            
        Returns:
            List of location results
        """
        # Build a smart query from scene data
        query_parts = [scene_location]
        
        # Add atmospheric keywords
        if scene_time and scene_time.lower() not in scene_location.lower():
            query_parts.append(scene_time.lower())
        
        # Add mood-based location hints
        mood_location_hints = {
            "melancholic": "quiet atmospheric",
            "surreal": "unique unusual",
            "nostalgic": "vintage classic",
            "mysterious": "hidden secret",
            "romantic": "beautiful scenic",
            "tense": "industrial urban",
            "peaceful": "serene tranquil",
        }
        
        if scene_mood:
            for mood_key, hint in mood_location_hints.items():
                if mood_key in scene_mood.lower():
                    query_parts.append(hint)
                    break
        
        query = " ".join(query_parts)
        return self.search_locations(query)
