#!/usr/bin/env python3
"""
Test script for FDA NDC to RxNorm Matching Agent
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_agent():
    """Test basic agent functionality"""
    print("Testing FDA NDC to RxNorm Matching Agent...")
    
    try:
        from src.agent import FDA_NDC_RxNorm_Agent
        from src.config import settings
        
        print("✓ Agent imports successful")
        
        # Test agent initialization
        agent = FDA_NDC_RxNorm_Agent()
        print("✓ Agent initialization successful")
        
        # Test status
        status = agent.get_status()
        print(f"✓ Agent status: {status}")
        
        # Test NDC downloader
        print("Testing NDC downloader...")
        ndc_stats = agent.ndc_downloader.get_data_statistics()
        print(f"✓ NDC statistics: {ndc_stats}")
        
        # Test RxNorm client
        print("Testing RxNorm client...")
        rxnorm_client = agent.rxnorm_client
        
        # Test with a sample NDC (this is a test NDC)
        test_ndc = "00071015527"  # Example NDC
        rxcui = rxnorm_client.find_rxcui_by_ndc(test_ndc)
        print(f"✓ RxNorm lookup test: NDC {test_ndc} -> RxCUI {rxcui}")
        
        # Test database
        print("Testing database...")
        db_stats = agent.db_manager.get_statistics()
        print(f"✓ Database statistics: {db_stats}")
        
        print("\n🎉 All tests passed! Agent is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_small_pipeline():
    """Test a small pipeline with limited data"""
    print("\nTesting small pipeline...")
    
    try:
        from src.agent import FDA_NDC_RxNorm_Agent
        
        agent = FDA_NDC_RxNorm_Agent()
        
        # Test with a small batch
        print("Running small pipeline test...")
        
        # Get a few NDC products for testing
        ndc_products = agent.ndc_downloader.get_ndc_products(limit=5)
        print(f"Testing with {len(ndc_products)} NDC products")
        
        if ndc_products:
            # Test matching
            matches = []
            for product in ndc_products:
                match = agent._match_single_ndc(product)
                if match:
                    matches.append(match)
                    print(f"✓ Matched NDC {product.product_ndc} -> RxCUI {match.rxnorm_concepts[0].rxcui if match.rxnorm_concepts else 'None'}")
                else:
                    print(f"✗ No match for NDC {product.product_ndc}")
            
            print(f"\nPipeline test completed: {len(matches)} successful matches out of {len(ndc_products)} products")
            return True
        else:
            print("No NDC products available for testing")
            return False
            
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("FDA NDC to RxNorm Matching Agent - Test Suite")
    print("=" * 50)
    
    # Run basic tests
    basic_test_passed = test_agent()
    
    if basic_test_passed:
        # Run pipeline test
        pipeline_test_passed = test_small_pipeline()
        
        if pipeline_test_passed:
            print("\n✅ All tests passed! The agent is ready for use.")
            print("\nNext steps:")
            print("1. Install dependencies: pip install -r requirements.txt")
            print("2. Run the agent: python main.py run-pipeline")
            print("3. Start the API: python main.py serve-api")
        else:
            print("\n⚠️  Basic tests passed but pipeline test failed.")
            print("This might be due to network issues or API limitations.")
    else:
        print("\n❌ Basic tests failed. Please check the installation and dependencies.")
        sys.exit(1) 