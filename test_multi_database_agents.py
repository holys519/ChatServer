"""
Integration test for Multi-Database Search and Citation Discovery agents.
Tests the complete workflow from database initialization to result generation.
"""
import asyncio
import json
from datetime import datetime, timedelta

from app.services.database_interfaces import database_registry
from app.services.pubmed_adapter import pubmed_adapter
from app.services.google_scholar_service import google_scholar_service
from app.services.arxiv_service import arxiv_service
from app.agents.multi_database_search_agent import multi_database_search_agent
from app.agents.citation_discovery_agent import citation_discovery_agent


async def test_database_initialization():
    """Test database service initialization."""
    print("🧪 Testing database initialization...")
    
    # Register adapters
    database_registry.register(pubmed_adapter)
    database_registry.register(google_scholar_service)
    database_registry.register(arxiv_service)
    
    # Initialize all databases
    init_results = await database_registry.initialize_all()
    
    print("Database initialization results:")
    for db_type, success in init_results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {db_type.value}: {'Success' if success else 'Failed'}")
    
    # Health check
    health_results = await database_registry.health_check_all()
    print("\nDatabase health check:")
    for db_type, health in health_results.items():
        print(f"  📊 {db_type.value}: {health}")
    
    return init_results


async def test_multi_database_search():
    """Test multi-database search functionality."""
    print("\n🔍 Testing multi-database search...")
    
    # Test query
    test_input = {
        "query": "machine learning healthcare",
        "max_results": 20,
        "years_back": 3,
        "databases": ["pubmed", "arxiv", "google_scholar"],
        "strategy": {
            "parallel_search": True,
            "merge_duplicates": True,
            "similarity_threshold": 0.85,
            "include_preprints": True
        }
    }
    
    try:
        # Execute search
        start_time = datetime.now()
        result = await multi_database_search_agent.execute(
            task_id="test_search_001",
            input_data=test_input
        )
        search_time = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print(f"Search completed in {search_time:.2f} seconds")
        print(f"Total papers found: {result.get('total_papers', 0)}")
        print(f"Duplicates removed: {result.get('duplicates_removed', 0)}")
        
        print("\nDatabase breakdown:")
        for db, stats in result.get('database_breakdown', {}).items():
            print(f"  📚 {db}: {stats['papers_found']} papers ({stats['search_time']:.2f}s) - {stats['status']}")
        
        print(f"\nQuality metrics: {result.get('quality_metrics', {})}")
        
        # Show sample papers
        papers = result.get('papers', [])
        if papers:
            print(f"\nSample papers (showing first 3 of {len(papers)}):")
            for i, paper in enumerate(papers[:3], 1):
                print(f"  {i}. {paper['title']}")
                print(f"     Authors: {', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}")
                print(f"     Source: {paper['database_source']} | Confidence: {paper['confidence_score']}")
                print(f"     URL: {paper.get('url', 'N/A')}")
                print()
        
        return result
        
    except Exception as e:
        print(f"❌ Multi-database search test failed: {str(e)}")
        return None


async def test_citation_discovery():
    """Test citation discovery functionality."""
    print("\n🔗 Testing citation discovery...")
    
    # Test with a sample seminal paper
    test_input = {
        "seminal_paper": {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani", "Shazeer", "Parmar"],
            "publication_date": "2017-06-12T00:00:00",
            "journal": "NIPS",
            "database_source": "arxiv"
        },
        "analysis_depth": "medium",
        "years_back": 5,
        "max_citing_papers": 30
    }
    
    try:
        # Execute citation analysis
        start_time = datetime.now()
        result = await citation_discovery_agent.execute(
            task_id="test_citation_001",
            input_data=test_input
        )
        analysis_time = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print(f"Citation analysis completed in {analysis_time:.2f} seconds")
        print(f"Citation network size: {result.get('citation_network_size', 0)}")
        print(f"Recent citing papers: {len(result.get('recent_citing_papers', []))}")
        print(f"Highly cited papers: {len(result.get('highly_cited_papers', []))}")
        
        # Network metrics
        network_metrics = result.get('network_metrics', {})
        print(f"\nNetwork metrics:")
        print(f"  Total citations: {network_metrics.get('total_citations', 0)}")
        print(f"  Network density: {network_metrics.get('network_density', 0):.3f}")
        print(f"  Key papers: {network_metrics.get('key_papers_count', 0)}")
        
        # Citation trends
        citation_trends = result.get('citation_trends', {})
        print(f"\nCitation trends:")
        print(f"  Citation trend: {citation_trends.get('citation_trend', 'unknown')}")
        print(f"  Paper trend: {citation_trends.get('paper_trend', 'unknown')}")
        print(f"  Peak year: {citation_trends.get('peak_year', 'unknown')}")
        
        # Related topics
        related_topics = result.get('related_topics', [])
        if related_topics:
            print(f"\nRelated topics (top 5): {', '.join(related_topics[:5])}")
        
        # Insights
        insights = result.get('insights', {})
        if insights:
            print(f"\nKey insights:")
            print(f"  Summary: {insights.get('summary', 'N/A')}")
            print(f"  Research impact: {insights.get('research_impact', 'N/A')}")
            if insights.get('key_findings'):
                for finding in insights['key_findings'][:3]:
                    print(f"  • {finding}")
        
        return result
        
    except Exception as e:
        print(f"❌ Citation discovery test failed: {str(e)}")
        return None


async def test_integration_workflow():
    """Test complete integration workflow."""
    print("\n🔄 Testing complete integration workflow...")
    
    try:
        # Step 1: Multi-database search
        print("Step 1: Performing multi-database search...")
        search_result = await test_multi_database_search()
        
        if not search_result or not search_result.get('papers'):
            print("❌ Cannot continue integration test - no papers found")
            return
        
        # Step 2: Use first paper for citation analysis
        first_paper = search_result['papers'][0]
        print(f"\nStep 2: Analyzing citations for: {first_paper['title']}")
        
        citation_input = {
            "seminal_paper": {
                "title": first_paper['title'],
                "authors": first_paper['authors'],
                "publication_date": first_paper.get('publication_date'),
                "journal": first_paper.get('journal'),
                "doi": first_paper.get('doi'),
                "database_source": first_paper.get('database_source')
            },
            "analysis_depth": "shallow",  # Use shallow for faster testing
            "years_back": 3,
            "max_citing_papers": 15
        }
        
        citation_result = await citation_discovery_agent.execute(
            task_id="test_integration_citation",
            input_data=citation_input
        )
        
        if citation_result:
            print("✅ Integration workflow completed successfully!")
            
            # Summary
            total_papers_discovered = (
                len(search_result.get('papers', [])) + 
                len(citation_result.get('recent_citing_papers', []))
            )
            
            print(f"\nWorkflow summary:")
            print(f"  📊 Total unique papers discovered: {total_papers_discovered}")
            print(f"  🔍 Multi-database search papers: {len(search_result.get('papers', []))}")
            print(f"  🔗 Citation network papers: {citation_result.get('citation_network_size', 0)}")
            print(f"  📈 Recent citing papers: {len(citation_result.get('recent_citing_papers', []))}")
            
            return True
        else:
            print("❌ Citation analysis failed in integration test")
            return False
            
    except Exception as e:
        print(f"❌ Integration workflow test failed: {str(e)}")
        return False


async def run_all_tests():
    """Run all integration tests."""
    print("🚀 Starting Multi-Database Agents Integration Tests")
    print("=" * 60)
    
    # Test 1: Database initialization
    init_success = await test_database_initialization()
    
    # Only continue if at least one database initialized successfully
    if not any(init_success.values()):
        print("❌ No databases initialized successfully. Stopping tests.")
        return
    
    # Test 2: Multi-database search
    await test_multi_database_search()
    
    # Test 3: Citation discovery
    await test_citation_discovery()
    
    # Test 4: Integration workflow
    integration_success = await test_integration_workflow()
    
    print("\n" + "=" * 60)
    if integration_success:
        print("✅ All integration tests completed successfully!")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")
    
    # Cleanup
    try:
        await google_scholar_service.close()
        await arxiv_service.close()
        print("🧹 Cleanup completed")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())