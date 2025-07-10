# FDA NDC to RxNorm Matching Agent

A comprehensive agent for downloading FDA National Drug Code (NDC) data, matching it to RxNorm concepts, and storing the results for clinical applications.

## Features

- **FDA NDC Data Download**: Automatically downloads and processes FDA NDC data from official sources
- **RxNorm Integration**: Matches NDC codes to RxNorm concepts using the RxNorm API
- **Clinical Data Storage**: Stores matched results in a structured format suitable for clinical applications
- **Data Validation**: Ensures data quality and completeness
- **API Interface**: RESTful API for querying matched data
- **Comprehensive Logging**: Detailed logging for monitoring and debugging

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables (see `.env.example`)
4. Run the agent:
   ```bash
   python main.py
   ```

## Usage

### Command Line Interface

```bash
# Download FDA NDC data
python main.py download-ndc

# Match NDC to RxNorm
python main.py match-rxnorm

# Run complete pipeline
python main.py run-pipeline

# Start API server
python main.py serve-api
```

### API Endpoints

- `GET /health` - Health check
- `GET /ndc/{ndc_code}` - Get RxNorm match for specific NDC
- `GET /drugs/{drug_name}` - Search drugs by name
- `POST /batch-match` - Batch match multiple NDCs

## Data Sources

- **FDA NDC Directory**: https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory
- **RxNorm API**: https://rxnav.nlm.nih.gov/

## Clinical Applications

The matched data can be used for:
- Electronic Health Records (EHR) integration
- Clinical decision support systems
- Drug interaction checking
- Medication reconciliation
- Clinical research and analytics

## License

MIT License 