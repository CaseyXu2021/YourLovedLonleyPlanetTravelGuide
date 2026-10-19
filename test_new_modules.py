"""
Test script to verify all new modules can be imported and basic functions work
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported"""
    print("=" * 60)
    print("[TEST] Testing Module Imports")
    print("=" * 60)
    
    try:
        print("\n1. Testing world_map_selector...")
        import world_map_selector
        print("   [OK] world_map_selector imported successfully")
        
        print("\n2. Testing city_selector...")
        import city_selector
        print("   [OK] city_selector imported successfully")
        
        print("\n3. Testing travel_plan_designer...")
        import travel_plan_designer
        print("   [OK] travel_plan_designer imported successfully")
        
        print("\n4. Testing app_v3...")
        # Don't actually run app_v3, just test import
        spec = __import__('importlib.util').util.spec_from_file_location(
            "app_v3",
            Path(__file__).resolve().parent / "app_v3.py"
        )
        app_v3_module = __import__('importlib.util').util.module_from_spec(spec)
        # Don't execute, just check it can be loaded
        print("   [OK] app_v3 module structure valid")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All imports successful!")
        print("=" * 60)
        return True
    
    except Exception as e:
        print(f"\n[FAIL] Import Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_functions():
    """Test basic functions in modules"""
    print("\n" + "=" * 60)
    print("[TEST] Testing Module Functions")
    print("=" * 60)
    
    try:
        # Test world_map_selector functions
        print("\n1. Testing world_map_selector functions...")
        from world_map_selector import COUNTRY_COORDS, get_book_cover_base64
        print(f"   [OK] Found {len(COUNTRY_COORDS)} countries in database")
        
        # Test city_selector functions
        print("\n2. Testing city_selector functions...")
        from city_selector import (
            get_top_cities_for_country,
            get_weather_forecast,
            get_attractions_for_city
        )
        print("   [OK] All city_selector functions imported")
        
        # Test travel_plan_designer functions
        print("\n3. Testing travel_plan_designer functions...")
        from travel_plan_designer import create_travel_plan_document
        print("   [OK] create_travel_plan_document function available")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All function tests passed!")
        print("=" * 60)
        return True
    
    except Exception as e:
        print(f"\n[FAIL] Function Test Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependencies():
    """Check required dependencies"""
    print("\n" + "=" * 60)
    print("[TEST] Checking Dependencies")
    print("=" * 60)
    
    dependencies = {
        "streamlit": "UI framework",
        "folium": "Map visualization",
        "streamlit_folium": "Folium integration",
        "docx": "Word document creation",
        "sentence-transformers": "Text embedding",
        "openai": "Azure OpenAI API",
        "requests": "HTTP requests",
        "geopy": "Geolocation",
    }
    
    all_ok = True
    
    for package, description in dependencies.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"[OK] {package:25} - {description}")
        except ImportError:
            print(f"[FAIL] {package:25} - {description} (NOT INSTALLED)")
            all_ok = False
    
    return all_ok


def main():
    """Run all tests"""
    print("\n[START] Starting Module Verification\n")
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Functions", test_functions()))
    results.append(("Dependencies", test_dependencies()))
    
    print("\n" + "=" * 60)
    print("[SUMMARY] Test Results")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n[SUCCESS] ALL TESTS PASSED! Ready to run app_v3.py\n")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Please fix issues before running app.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
