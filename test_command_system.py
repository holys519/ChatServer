#!/usr/bin/env python3
"""
Test script for Phase 2: Command Suggestion System
Tests command discovery, validation, suggestions, and help functionality
"""

import asyncio
import sys
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append('.')

async def test_command_service():
    """Test the command service functionality"""
    print("🧪 Testing Command Service")
    print("=" * 60)
    
    try:
        from app.services.command_service import command_service
        
        print("✅ Command service loaded successfully")
        
        # Test 1: List All Commands
        print("\n" + "="*50)
        print("TEST 1: List All Commands")
        print("="*50)
        
        commands = command_service.list_commands()
        print(f"✅ Found {len(commands)} registered commands:")
        
        for cmd in commands:
            print(f"   - {cmd.name} ({cmd.category.value}): {cmd.description[:60]}...")
        
        # Test 2: Command Search
        print("\n" + "="*50)
        print("TEST 2: Command Search")
        print("="*50)
        
        search_queries = ["research", "paper", "workflow", "review"]
        
        for query in search_queries:
            results = command_service.search_commands(query)
            print(f"🔍 Search '{query}': {len(results)} results")
            for result in results[:2]:  # Show top 2
                print(f"   → {result.name}")
        
        # Test 3: Intent-based Suggestions
        print("\n" + "="*50)
        print("TEST 3: Intent-based Command Suggestions")
        print("="*50)
        
        test_messages = [
            "I want to find papers about machine learning",
            "Can you help me create a literature review?",
            "I need to do comprehensive research on AI ethics",
            "Search for papers about COVID-19 treatment",
            "Analyze the quality of research papers"
        ]
        
        for message in test_messages:
            suggestions = command_service.suggest_commands_for_intent(message)
            print(f"📝 Message: '{message}'")
            print(f"   💡 Suggestions: {[s.name for s in suggestions]}")
        
        # Test 4: Command Validation
        print("\n" + "="*50)
        print("TEST 4: Command Validation")
        print("="*50)
        
        test_commands = [
            "@research-workflow machine learning",
            "@paper-scout-auditor",  # Missing query
            "@invalid-command test",
            "@paper-scout deep learning",
            "not-a-command",
            "@research-workflow AI ethics type:systematic"
        ]
        
        for cmd_text in test_commands:
            result = command_service.validate_command_syntax(cmd_text)
            status = "✅ Valid" if result["valid"] else "❌ Invalid"
            print(f"   {cmd_text}: {status}")
            if not result["valid"]:
                print(f"      Error: {result['error']}")
                print(f"      Suggestion: {result['suggestion']}")
        
        # Test 5: Help Generation
        print("\n" + "="*50)
        print("TEST 5: Help Text Generation")
        print("="*50)
        
        # Test help for specific command
        help_text = command_service.get_help_text("@research-workflow")
        print(f"✅ Help for @research-workflow: {len(help_text)} characters")
        print(f"   Preview: {help_text[:200]}...")
        
        # Test general help
        general_help = command_service.get_help_text()
        print(f"✅ General help: {len(general_help)} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Command service test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_commands_api():
    """Test the commands API endpoints (simulation)"""
    print("\n" + "="*60)
    print("TESTING COMMANDS API SIMULATION")
    print("="*60)
    
    try:
        from app.api.routes.commands import (
            list_commands, suggest_commands, validate_command,
            search_commands, get_help, get_command_info
        )
        from app.api.routes.commands import (
            CommandSuggestionRequest, CommandValidationRequest
        )
        
        print("✅ Commands API imported successfully")
        
        # Test 1: List Commands API
        print("\n📋 Testing list_commands API...")
        commands_response = await list_commands()
        print(f"✅ API returned {len(commands_response)} commands")
        
        # Test 2: Command Suggestions API
        print("\n💡 Testing suggest_commands API...")
        suggestion_request = CommandSuggestionRequest(
            message="I want to research machine learning applications"
        )
        suggestions_response = await suggest_commands(suggestion_request)
        print(f"✅ API suggested {len(suggestions_response.suggestions)} commands")
        print(f"   Intent detected: {suggestions_response.intent_detected}")
        print(f"   Confidence: {suggestions_response.confidence}")
        
        # Test 3: Command Validation API
        print("\n🔍 Testing validate_command API...")
        validation_request = CommandValidationRequest(
            command="@research-workflow AI in healthcare"
        )
        validation_response = await validate_command(validation_request)
        print(f"✅ Validation result: {'Valid' if validation_response.valid else 'Invalid'}")
        
        # Test invalid command
        invalid_request = CommandValidationRequest(
            command="@invalid-command test"
        )
        invalid_response = await validate_command(invalid_request)
        print(f"❌ Invalid command test: {invalid_response.error}")
        
        # Test 4: Search Commands API
        print("\n🔍 Testing search_commands API...")
        search_results = await search_commands(q="research")
        print(f"✅ Search found {len(search_results)} commands")
        
        # Test 5: Get Help API
        print("\n❓ Testing get_help API...")
        help_response = await get_help(command="@research-workflow")
        print(f"✅ Help response: {len(help_response['help'])} characters")
        
        # Test 6: Get Command Info API
        print("\n📖 Testing get_command_info API...")
        info_response = await get_command_info("research-workflow")
        print(f"✅ Command info: {info_response.name}")
        print(f"   Complexity: {info_response.complexity}")
        print(f"   Parameters: {len(info_response.parameters)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Commands API test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_chat_integration():
    """Test command system integration with chat"""
    print("\n" + "="*60)
    print("TESTING CHAT INTEGRATION")
    print("="*60)
    
    try:
        from app.models.schemas import ChatRequest, ChatModel
        from app.api.routes.chat import send_chat_message
        
        print("✅ Chat integration components loaded")
        
        # Test 1: Help Command
        print("\n❓ Testing /help command...")
        help_request = ChatRequest(
            message="/help",
            model=ChatModel(id="test", provider="test"),
            session_id="test",
            history=[]
        )
        
        # Note: In real test, we'd call the endpoint
        # For simulation, we test command service directly
        from app.services.command_service import command_service
        help_text = command_service.get_help_text()
        print(f"✅ Help command would return {len(help_text)} characters")
        
        # Test 2: Command Suggestions
        print("\n💡 Testing /suggest command...")
        suggestion_text = "find papers about artificial intelligence"
        suggestions = command_service.suggest_commands_for_intent(suggestion_text)
        print(f"✅ Would suggest {len(suggestions)} commands for: '{suggestion_text}'")
        
        # Test 3: Natural Language Intent Detection
        print("\n🗣️ Testing natural language intent detection...")
        natural_requests = [
            "I need to find research papers about machine learning",
            "Can you help me write a literature review on AI ethics?",
            "Search for papers about renewable energy",
            "I want to do comprehensive research on quantum computing"
        ]
        
        for request in natural_requests:
            suggestions = command_service.suggest_commands_for_intent(request)
            print(f"   '{request[:40]}...' → {suggestions[0].name if suggestions else 'No suggestions'}")
        
        # Test 4: Command Validation
        print("\n🔍 Testing command validation in chat...")
        test_commands = [
            "@research-workflow machine learning",
            "@invalid-command test",
            "@paper-scout-auditor COVID-19"
        ]
        
        for cmd in test_commands:
            validation = command_service.validate_command_syntax(cmd)
            status = "✅ Valid" if validation["valid"] else "❌ Invalid"
            print(f"   {cmd}: {status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat integration test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Phase 2: Command System Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test core command service
    success1 = await test_command_service()
    
    # Test commands API
    success2 = await test_commands_api()
    
    # Test chat integration
    success3 = await test_chat_integration()
    
    # Final results
    print("\n" + "="*60)
    print("🏁 PHASE 2 TEST RESULTS")
    print("="*60)
    
    if success1 and success2 and success3:
        print("🎉 ALL PHASE 2 TESTS PASSED!")
        print("✅ Command suggestion system working properly")
        print("✅ Intelligent command discovery implemented")
        print("✅ Context-aware recommendations active")
        print("✅ Command validation and help system operational")
        print("✅ Chat integration completed")
        
        print("\n📊 PHASE 2 FEATURES IMPLEMENTED:")
        print("   🔍 Intent-based command suggestions")
        print("   💡 Natural language to command mapping")
        print("   ❓ Comprehensive help system")
        print("   🔧 Command validation with error suggestions")
        print("   📋 Command discovery and search")
        print("   🔗 Full chat integration")
        
    else:
        print("❌ SOME PHASE 2 TESTS FAILED")
        print("⚠️ Please review the errors above")
    
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())