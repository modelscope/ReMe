#!/usr/bin/env python3
"""
Simple test script to verify the UpdateInsightOp implementation.
This is a basic validation test to ensure the class structure is correct.
"""

import sys
import os
sys.path.append('/Users/yuli/workspace/MemoryScope')

def test_update_insight_op_import():
    """Test that we can import the UpdateInsightOp class"""
    try:
        from reme_ai.summary.personal.update_insight_op import UpdateInsightOp
        print("✓ Successfully imported UpdateInsightOp")
        return True
    except ImportError as e:
        print(f"✗ Failed to import UpdateInsightOp: {e}")
        return False

def test_personal_memory_import():
    """Test that we can import PersonalMemory"""
    try:
        from reme_ai.schema.memory import PersonalMemory
        print("✓ Successfully imported PersonalMemory")
        return True
    except ImportError as e:
        print(f"✗ Failed to import PersonalMemory: {e}")
        return False

def test_op_utils_import():
    """Test that we can import the utility functions"""
    try:
        from reme_ai.utils.op_utils import parse_update_insight_response
        print("✓ Successfully imported parse_update_insight_response")
        return True
    except ImportError as e:
        print(f"✗ Failed to import parse_update_insight_response: {e}")
        return False

def test_personal_memory_creation():
    """Test PersonalMemory creation with reflection_subject"""
    try:
        from reme_ai.schema.memory import PersonalMemory
        
        memory = PersonalMemory(
            workspace_id="test_workspace",
            content="User likes playing basketball",
            target="test_user",
            reflection_subject="hobbies",
            author="test_system"
        )
        
        print(f"✓ Created PersonalMemory: {memory.content}")
        print(f"  - Memory ID: {memory.memory_id}")
        print(f"  - Target: {memory.target}")
        print(f"  - Reflection Subject: {memory.reflection_subject}")
        return True
    except Exception as e:
        print(f"✗ Failed to create PersonalMemory: {e}")
        return False

def test_parse_update_insight_response():
    """Test the parse_update_insight_response function"""
    try:
        from reme_ai.utils.op_utils import parse_update_insight_response
        
        # Test Chinese format
        chinese_response = "思考：用户喜欢篮球和足球\ntest_user的资料：<喜欢篮球和足球>"
        result_zh = parse_update_insight_response(chinese_response, "zh")
        print(f"✓ Parsed Chinese response: '{result_zh}'")
        
        # Test English format
        english_response = "Thoughts: User likes basketball and football\ntest_user's profile: <Likes basketball and football>"
        result_en = parse_update_insight_response(english_response, "en")
        print(f"✓ Parsed English response: '{result_en}'")
        
        return True
    except Exception as e:
        print(f"✗ Failed to test parse_update_insight_response: {e}")
        return False

def main():
    """Run all tests"""
    print("Running UpdateInsightOp validation tests...\n")
    
    tests = [
        test_personal_memory_import,
        test_op_utils_import,
        test_update_insight_op_import,
        test_personal_memory_creation,
        test_parse_update_insight_response
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\nRunning {test.__name__}:")
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The UpdateInsightOp implementation looks good.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
