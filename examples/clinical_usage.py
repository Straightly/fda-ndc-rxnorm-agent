#!/usr/bin/env python3
"""
Clinical Usage Example
Demonstrates how to use the FDA NDC to RxNorm Matching Agent for clinical applications
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.agent import FDA_NDC_RxNorm_Agent
from src.models import ClinicalOutput


def clinical_drug_lookup_example():
    """Example: Look up drug information for clinical use"""
    print("🏥 Clinical Drug Lookup Example")
    print("=" * 40)
    
    agent = FDA_NDC_RxNorm_Agent()
    
    # Example NDC codes (these are sample codes)
    sample_ndcs = [
        "00071015527",  # Example NDC
        "00071015528",  # Example NDC
        "00071015529"   # Example NDC
    ]
    
    print(f"Looking up {len(sample_ndcs)} NDC codes...")
    
    clinical_results = []
    
    for ndc in sample_ndcs:
        try:
            # Get match from database or perform new match
            match = agent.db_manager.get_match_by_ndc(ndc)
            
            if not match:
                # Try to find and match the NDC
                ndc_products = agent.ndc_downloader.search_ndc_by_name(ndc, limit=1)
                if ndc_products:
                    match = agent._match_single_ndc(ndc_products[0])
                    if match:
                        agent.db_manager.save_matches([match])
            
            if match:
                # Generate clinical output
                clinical_output = agent.generate_clinical_output([match])[0]
                clinical_results.append(clinical_output)
                
                print(f"✓ NDC {ndc}: {clinical_output.drug_name} (RxCUI: {clinical_output.rxnorm_cui})")
            else:
                print(f"✗ NDC {ndc}: No match found")
                
        except Exception as e:
            print(f"✗ NDC {ndc}: Error - {e}")
    
    return clinical_results


def drug_interaction_check_example():
    """Example: Check for drug interactions"""
    print("\n💊 Drug Interaction Check Example")
    print("=" * 40)
    
    agent = FDA_NDC_RxNorm_Agent()
    
    # Example drug names to check for interactions
    drug_names = ["aspirin", "ibuprofen", "acetaminophen"]
    
    for drug_name in drug_names:
        print(f"\nChecking interactions for: {drug_name}")
        
        try:
            # Search for the drug
            matches = agent.db_manager.search_matches(drug_name, limit=1)
            
            if matches and matches[0].rxnorm_concepts:
                rxcui = matches[0].rxnorm_concepts[0].rxcui
                
                # Get drug interactions
                interactions = agent.rxnorm_client.get_drug_interactions(rxcui)
                
                if interactions:
                    print(f"  Found {len(interactions)} potential interactions:")
                    for interaction in interactions[:3]:  # Show first 3
                        print(f"    - {interaction.get('description', 'No description')}")
                        print(f"      Severity: {interaction.get('severity', 'Unknown')}")
                else:
                    print("  No known interactions found")
            else:
                print(f"  Drug '{drug_name}' not found in database")
                
        except Exception as e:
            print(f"  Error checking interactions: {e}")


def clinical_data_export_example():
    """Example: Export clinical data for EHR integration"""
    print("\n📊 Clinical Data Export Example")
    print("=" * 40)
    
    agent = FDA_NDC_RxNorm_Agent()
    
    # Get high-confidence matches for clinical use
    high_confidence_matches = agent.db_manager.get_high_confidence_matches(
        min_confidence=0.8, 
        limit=100
    )
    
    print(f"Found {len(high_confidence_matches)} high-confidence matches")
    
    # Generate clinical outputs
    clinical_outputs = agent.generate_clinical_output(high_confidence_matches)
    
    # Export to different formats
    output_dir = Path("data/output/clinical")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Export as JSON
    import json
    json_file = output_dir / "clinical_drugs.json"
    with open(json_file, 'w') as f:
        json.dump([output.dict() for output in clinical_outputs], f, indent=2, default=str)
    
    # Export as CSV
    import pandas as pd
    csv_file = output_dir / "clinical_drugs.csv"
    df = pd.DataFrame([output.dict() for output in clinical_outputs])
    df.to_csv(csv_file, index=False)
    
    print(f"✓ Exported {len(clinical_outputs)} clinical records to:")
    print(f"  - JSON: {json_file}")
    print(f"  - CSV: {csv_file}")
    
    # Show sample of exported data
    print("\nSample clinical data:")
    for i, output in enumerate(clinical_outputs[:3]):
        print(f"  {i+1}. {output.drug_name} ({output.ndc_code})")
        print(f"     RxCUI: {output.rxnorm_cui}")
        print(f"     Ingredients: {', '.join(output.ingredients) if output.ingredients else 'None'}")
        print(f"     Confidence: {output.match_confidence:.2f}")


def medication_reconciliation_example():
    """Example: Medication reconciliation using NDC codes"""
    print("\n🔄 Medication Reconciliation Example")
    print("=" * 40)
    
    agent = FDA_NDC_RxNorm_Agent()
    
    # Simulate patient medication list with NDC codes
    patient_medications = [
        {"ndc": "00071015527", "prescribed_date": "2024-01-15", "dose": "10mg daily"},
        {"ndc": "00071015528", "prescribed_date": "2024-01-10", "dose": "500mg twice daily"},
        {"ndc": "00071015529", "prescribed_date": "2024-01-20", "dose": "25mg as needed"}
    ]
    
    print("Reconciling patient medications...")
    
    reconciled_medications = []
    
    for med in patient_medications:
        try:
            # Get clinical information for the NDC
            match = agent.db_manager.get_match_by_ndc(med["ndc"])
            
            if match:
                clinical_output = agent.generate_clinical_output([match])[0]
                
                reconciled_med = {
                    "original_ndc": med["ndc"],
                    "rxnorm_cui": clinical_output.rxnorm_cui,
                    "standardized_name": clinical_output.rxnorm_name,
                    "generic_name": clinical_output.generic_name,
                    "ingredients": clinical_output.ingredients,
                    "drug_classes": clinical_output.drug_classes,
                    "dosage_form": clinical_output.dosage_form,
                    "route": clinical_output.route,
                    "strength": clinical_output.strength,
                    "prescribed_dose": med["dose"],
                    "prescribed_date": med["prescribed_date"],
                    "match_confidence": clinical_output.match_confidence
                }
                
                reconciled_medications.append(reconciled_med)
                
                print(f"✓ {clinical_output.drug_name} -> {clinical_output.rxnorm_name}")
            else:
                print(f"✗ NDC {med['ndc']}: No match found")
                
        except Exception as e:
            print(f"✗ NDC {med['ndc']}: Error - {e}")
    
    # Check for potential drug interactions
    print("\nChecking for potential drug interactions...")
    rxcuis = [med["rxnorm_cui"] for med in reconciled_medications if med["rxnorm_cui"]]
    
    for i, rxcui1 in enumerate(rxcuis):
        for j, rxcui2 in enumerate(rxcuis[i+1:], i+1):
            try:
                interactions = agent.rxnorm_client.get_drug_interactions(rxcui1)
                # Check if rxcui2 appears in interactions
                for interaction in interactions:
                    if any(drug.get("rxcui") == rxcui2 for drug in interaction.get("drugs", [])):
                        print(f"⚠️  Potential interaction between medications {i+1} and {j+1}")
                        print(f"   {interaction.get('description', 'No description')}")
            except Exception as e:
                continue
    
    return reconciled_medications


def main():
    """Run all clinical examples"""
    print("🏥 FDA NDC to RxNorm Matching Agent - Clinical Usage Examples")
    print("=" * 60)
    
    try:
        # Example 1: Drug lookup
        clinical_drug_lookup_example()
        
        # Example 2: Drug interactions
        drug_interaction_check_example()
        
        # Example 3: Clinical data export
        clinical_data_export_example()
        
        # Example 4: Medication reconciliation
        medication_reconciliation_example()
        
        print("\n🎉 All clinical examples completed successfully!")
        print("\nThese examples demonstrate how the agent can be used for:")
        print("- Clinical drug lookups and standardization")
        print("- Drug interaction checking")
        print("- Clinical data export for EHR integration")
        print("- Medication reconciliation")
        
    except Exception as e:
        print(f"\n❌ Error running clinical examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 