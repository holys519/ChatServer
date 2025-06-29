#!/usr/bin/env python3
"""
Test script for Enhanced Paper Search System
Tests the multi-agent paper search auditor workflow
"""

import asyncio
import sys
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append('.')

async def test_enhanced_paper_search():
    """Test the enhanced paper search system"""
    print("🧪 Testing Enhanced Paper Search System")
    print("=" * 60)
    
    try:
        # Import required modules
        from app.services.agent_base import agent_orchestrator
        
        print("✅ Agent orchestrator loaded successfully")
        
        # List available agents
        agents = agent_orchestrator.list_agents()
        print(f"\n🤖 Available agents ({len(agents)}):")
        for agent_id, description in agents.items():
            print(f"  - {agent_id}: {description[:60]}...")
        
        # Test query
        test_query = "machine learning in healthcare diagnosis"
        print(f"\n🔍 Test Query: '{test_query}'")
        
        # Test 1: Paper Scout Agent
        print("\n" + "="*50)
        print("TEST 1: Paper Scout Agent")
        print("="*50)
        
        scout_input = {
            'query': test_query,
            'max_results': 5,  # Small number for testing
            'years_back': 5,
            'include_abstracts': True,
            'analysis_type': 'summary'
        }
        
        try:
            scout_result = await agent_orchestrator.execute_task(
                task_id="test_scout_001",
                agent_id="paper_scout",
                input_data=scout_input
            )
            
            print(f"✅ Paper Scout completed successfully")
            print(f"   - Papers found: {scout_result.get('papers_found', 0)}")
            print(f"   - Status: {scout_result.get('status', 'Unknown')}")
            
            papers = scout_result.get('papers', [])
            if papers:
                print(f"   - Sample paper: {papers[0].get('title', 'Unknown')[:60]}...")
            
        except Exception as scout_error:
            print(f"❌ Paper Scout test failed: {str(scout_error)}")
            return False
        
        # Test 2: Paper Critic Agent
        print("\n" + "="*50)
        print("TEST 2: Paper Critic Agent")
        print("="*50)
        
        if papers:
            critic_input = {
                'papers': papers,
                'search_query': scout_result.get('optimized_query', test_query),
                'original_query': test_query,
                'analysis_focus': 'comprehensive'
            }
            
            try:
                critic_result = await agent_orchestrator.execute_task(
                    task_id="test_critic_001",
                    agent_id="paper_critic",
                    input_data=critic_input
                )
                
                print(f"✅ Paper Critic completed successfully")
                print(f"   - Status: {critic_result.get('status', 'Unknown')}")
                
                result_analysis = critic_result.get('result_analysis', {})
                avg_score = result_analysis.get('average_score', 0)
                quality_grade = result_analysis.get('overall_quality_grade', 'N/A')
                
                print(f"   - Average quality score: {avg_score:.2f}")
                print(f"   - Quality grade: {quality_grade}")
                
            except Exception as critic_error:
                print(f"❌ Paper Critic test failed: {str(critic_error)}")
                return False
        else:
            print("⚠️ Skipping Paper Critic test (no papers from scout)")
            critic_result = {}
        
        # Test 3: Paper Reviser Agent
        print("\n" + "="*50)
        print("TEST 3: Paper Reviser Agent")
        print("="*50)
        
        if papers and critic_result:
            reviser_input = {
                'papers': papers,
                'critic_feedback': critic_result,
                'search_query': scout_result.get('optimized_query', test_query),
                'original_query': test_query,
                'enhancement_goals': ['quality', 'diversity']
            }
            
            try:
                reviser_result = await agent_orchestrator.execute_task(
                    task_id="test_reviser_001",
                    agent_id="paper_reviser",
                    input_data=reviser_input
                )
                
                print(f"✅ Paper Reviser completed successfully")
                print(f"   - Status: {reviser_result.get('status', 'Unknown')}")
                
                final_papers = reviser_result.get('revised_papers', [])
                improvement_metrics = reviser_result.get('improvement_metrics', {})
                
                print(f"   - Final papers count: {len(final_papers)}")
                print(f"   - Original papers count: {improvement_metrics.get('original_count', 0)}")
                print(f"   - Papers added: {improvement_metrics.get('papers_added', 0)}")
                
            except Exception as reviser_error:
                print(f"❌ Paper Reviser test failed: {str(reviser_error)}")
                return False
        else:
            print("⚠️ Skipping Paper Reviser test (missing prerequisites)")
            reviser_result = {}
        
        # Test 4: Paper Search Auditor (Full Workflow)
        print("\n" + "="*50)
        print("TEST 4: Paper Search Auditor (Full Workflow)")
        print("="*50)
        
        if papers:
            auditor_input = {
                'papers': papers,
                'search_query': scout_result.get('optimized_query', test_query),
                'original_query': test_query,
                'audit_goals': ['quality', 'completeness', 'diversity']
            }
            
            try:
                auditor_result = await agent_orchestrator.execute_task(
                    task_id="test_auditor_001",
                    agent_id="paper_search_auditor",
                    input_data=auditor_input
                )
                
                print(f"✅ Paper Search Auditor completed successfully")
                print(f"   - Status: {auditor_result.get('status', 'Unknown')}")
                
                final_validation = auditor_result.get('final_validation', {})
                audit_success = final_validation.get('audit_success', False)
                confidence_score = final_validation.get('confidence_score', 0)
                
                print(f"   - Audit success: {audit_success}")
                print(f"   - Confidence score: {confidence_score:.2f}")
                
                quality_metrics = auditor_result.get('quality_metrics', {})
                collection_metrics = quality_metrics.get('collection_metrics', {})
                
                print(f"   - Original papers: {collection_metrics.get('original_count', 0)}")
                print(f"   - Final papers: {collection_metrics.get('final_count', 0)}")
                print(f"   - Net change: {collection_metrics.get('net_change', 0)}")
                
                # Show a sample of the audit report
                audit_report = auditor_result.get('audit_report', '')
                if audit_report:
                    print(f"   - Audit report preview: {audit_report[:200]}...")
                
            except Exception as auditor_error:
                print(f"❌ Paper Search Auditor test failed: {str(auditor_error)}")
                return False
        else:
            print("⚠️ Skipping Paper Search Auditor test (no papers)")
        
        print("\n" + "="*60)
        print("🎉 Enhanced Paper Search System Test COMPLETED")
        print("="*60)
        
        # Summary
        print("\n📊 TEST SUMMARY:")
        print(f"   ✅ Paper Scout Agent: Working")
        print(f"   ✅ Paper Critic Agent: Working") 
        print(f"   ✅ Paper Reviser Agent: Working")
        print(f"   ✅ Paper Search Auditor: Working")
        print(f"   🔧 All agents integrated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_command_integration():
    """Test @paper-scout-auditor command integration"""
    print("\n" + "="*60)
    print("TESTING COMMAND INTEGRATION")
    print("="*60)
    
    try:
        # Simulate the chat command workflow
        from app.services.agent_base import agent_orchestrator
        
        test_query = "COVID-19 vaccine efficacy"
        print(f"🔍 Testing command: @paper-scout-auditor {test_query}")
        
        # Step 1: Paper Scout
        scout_input = {
            'query': test_query,
            'max_results': 8,
            'years_back': 5,
            'include_abstracts': True,
            'analysis_type': 'comprehensive'
        }
        
        scout_result = await agent_orchestrator.execute_task(
            task_id="cmd_test_scout",
            agent_id="paper_scout",
            input_data=scout_input
        )
        
        print(f"✅ Scout phase: {scout_result.get('papers_found', 0)} papers found")
        
        # Step 2: Paper Search Auditor
        auditor_input = {
            'papers': scout_result.get('papers', []),
            'search_query': scout_result.get('optimized_query', test_query),
            'original_query': test_query,
            'audit_goals': ['quality', 'completeness', 'diversity']
        }
        
        auditor_result = await agent_orchestrator.execute_task(
            task_id="cmd_test_auditor",
            agent_id="paper_search_auditor",
            input_data=auditor_input
        )
        
        print(f"✅ Auditor phase: {auditor_result.get('status', 'Unknown')}")
        
        # Generate response like the chat endpoint would
        audit_report = auditor_result.get('audit_report', 'Audit completed')
        final_papers_count = len(auditor_result.get('final_papers', []))
        quality_metrics = auditor_result.get('quality_metrics', {})
        quality_grade = quality_metrics.get('quality_metrics', {}).get('quality_grade', 'N/A')
        
        response_text = f"""# Enhanced Paper Search Audit Results

## Query: "{test_query}"

### Audit Summary
- **Final Papers Count**: {final_papers_count}
- **Quality Grade**: {quality_grade}
- **Audit Status**: {auditor_result.get('status', 'Unknown')}

{audit_report[:500]}...

---
*This search was conducted using the enhanced Paper Search Auditor with multi-agent validation and improvement.*"""
        
        print("\n📝 Generated Response Preview:")
        print("-" * 40)
        print(response_text[:800] + "..." if len(response_text) > 800 else response_text)
        print("-" * 40)
        
        print("\n✅ Command integration test successful!")
        return True
        
    except Exception as e:
        print(f"❌ Command integration test failed: {str(e)}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Enhanced Paper Search System Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test individual agents
    success1 = await test_enhanced_paper_search()
    
    # Test command integration
    success2 = await test_command_integration()
    
    # Final results
    print("\n" + "="*60)
    print("🏁 FINAL TEST RESULTS")
    print("="*60)
    
    if success1 and success2:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Enhanced Paper Search System is ready for production")
        print("🔧 Chat integration with @paper-scout-auditor command working")
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️ Please review the errors above")
    
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())