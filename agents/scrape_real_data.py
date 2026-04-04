#!/usr/bin/env python3
"""
Scrape real competitive intelligence data using Google Places API
Generates JSON files for the test suite
"""

import os
import sys
from dotenv import load_dotenv
from google_places_scraper import GooglePlacesAPI, save_locations_to_json
from datetime import datetime

def main():
    # Load environment variables
    load_dotenv('.env.scraper')

    api_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not api_key:
        print("❌ Error: GOOGLE_PLACES_API_KEY not found in .env.scraper")
        sys.exit(1)

    print("=" * 70)
    print("COMPETITIVE INTELLIGENCE DATA COLLECTION")
    print("=" * 70)
    print(f"API Key: {api_key[:10]}..." if api_key else "Not configured")
    print()

    # Initialize Google Places API
    api = GooglePlacesAPI(api_key, delay=0.5)

    # Test 1: US Coffee Market - Starbucks vs Dunkin
    print("\n📊 TEST 1: US Coffee Market Analysis")
    print("-" * 70)

    starbucks_locations = api.search_brand_locations('Starbucks', 'US', 'coffee', max_results=30)
    dunkin_locations = api.search_brand_locations('Dunkin', 'US', 'coffee', max_results=30)

    all_coffee = starbucks_locations + dunkin_locations
    brands_discovered = list(set([loc.brand for loc in all_coffee]))

    save_locations_to_json(
        all_coffee,
        'us_coffee_competitive_analysis.json',
        metadata={
            'total_locations': len(all_coffee),
            'brands_discovered': brands_discovered,
            'country': 'US',
            'category': 'coffee',
            'data_source': 'google-places-api',
            'timestamp': datetime.now().isoformat()
        }
    )

    # Test 2: UK Fast Food Analysis
    print("\n🍔 TEST 2: UK Fast Food Market Analysis")
    print("-" * 70)

    mcdonalds_uk = api.search_brand_locations('McDonald\'s', 'UK', 'fast-food', max_results=20)
    kfc_uk = api.search_brand_locations('KFC', 'UK', 'fast-food', max_results=20)
    subway_uk = api.search_brand_locations('Subway', 'UK', 'fast-food', max_results=20)

    all_fastfood = mcdonalds_uk + kfc_uk + subway_uk
    brands_discovered_uk = list(set([loc.brand for loc in all_fastfood]))

    save_locations_to_json(
        all_fastfood,
        'uk_fastfood_analysis.json',
        metadata={
            'total_locations': len(all_fastfood),
            'brands_discovered': brands_discovered_uk,
            'country': 'UK',
            'category': 'fast-food',
            'data_source': 'google-places-api',
            'timestamp': datetime.now().isoformat()
        }
    )

    # Test 3: Canada Retail Comparison
    print("\n🏬 TEST 3: Canada Retail Market Analysis")
    print("-" * 70)

    walmart_ca = api.search_brand_locations('Walmart', 'CA', 'retail', max_results=20)
    target_ca = api.search_brand_locations('Target', 'CA', 'retail', max_results=20)

    all_retail = walmart_ca + target_ca
    brands_discovered_ca = list(set([loc.brand for loc in all_retail]))

    save_locations_to_json(
        all_retail,
        'ca_retail_analysis.json',
        metadata={
            'total_locations': len(all_retail),
            'brands_discovered': brands_discovered_ca,
            'country': 'CA',
            'category': 'retail',
            'data_source': 'google-places-api',
            'timestamp': datetime.now().isoformat()
        }
    )

    # Display usage stats
    print("\n" + "=" * 70)
    print("API USAGE STATISTICS")
    print("=" * 70)
    stats = api.get_usage_stats()
    print(f"Total API Requests: {stats['requests_made']}")
    print(f"Average Delay: {stats['average_delay']}s")
    print(f"Last Request: {stats['last_request']}")

    print("\n✅ Data collection complete!")
    print("\nGenerated files:")
    print("  • us_coffee_competitive_analysis.json")
    print("  • uk_fastfood_analysis.json")
    print("  • ca_retail_analysis.json")
    print("\nYou can now run: npx ts-node test-competitive-intelligence.ts")

if __name__ == '__main__':
    main()
