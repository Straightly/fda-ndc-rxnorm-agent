# Deployment Guide

## GitHub Repository Setup

### 1. Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the "+" icon → "New repository"
3. Repository settings:
   - **Name**: `fda-ndc-rxnorm-agent`
   - **Description**: `FDA NDC to RxNorm Matching Agent for Clinical Applications`
   - **Visibility**: Public (recommended for open source)
   - **Do NOT** initialize with README, .gitignore, or license
4. Click "Create repository"

### 2. Push Code to GitHub

After creating the repository, run these commands:

```bash
# Add remote origin (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/fda-ndc-rxnorm-agent.git

# Push to GitHub
git push -u origin main
```

Or use the provided script:
```bash
# Edit the script to add your GitHub username
nano push_to_github.sh

# Run the script
./push_to_github.sh
```

### 3. Repository Configuration

After pushing, configure your repository:

1. **Add Topics**: Go to repository settings and add topics like:
   - `fda`
   - `ndc`
   - `rxnorm`
   - `clinical`
   - `healthcare`
   - `python`
   - `api`

2. **Add Description**: Update the repository description with:
   ```
   Comprehensive agent for downloading FDA NDC data, matching to RxNorm concepts, 
   and providing clinical-ready outputs for healthcare applications.
   ```

3. **Enable Issues**: Go to Settings → Features and enable Issues

## Local Development Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/fda-ndc-rxnorm-agent.git
cd fda-ndc-rxnorm-agent
```

### 2. Install Dependencies

```bash
# Run the installation script
./install.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit configuration
nano .env
```

### 4. Test Installation

```bash
# Run test suite
python test_agent.py
```

## Production Deployment

### Option 1: Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py", "serve-api"]
```

Build and run:
```bash
docker build -t fda-ndc-rxnorm-agent .
docker run -p 8000:8000 fda-ndc-rxnorm-agent
```

### Option 2: Cloud Deployment

#### Heroku

1. Create `Procfile`:
```
web: python main.py serve-api
```

2. Deploy:
```bash
heroku create fda-ndc-rxnorm-agent
git push heroku main
```

#### AWS/GCP/Azure

1. Use container services (ECS, GKE, AKS)
2. Set up environment variables
3. Configure health checks
4. Set up monitoring and logging

### Option 3: Local Production

```bash
# Run the complete pipeline
python main.py run-pipeline

# Start API server
python main.py serve-api

# Access API documentation
open http://localhost:8000/docs
```

## CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/ci.yml`:

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python test_agent.py
    
    - name: Run linting
      run: |
        pip install flake8 black
        flake8 src/
        black --check src/
```

## Monitoring and Maintenance

### 1. Health Checks

The API provides health check endpoint:
```bash
curl http://localhost:8000/health
```

### 2. Logging

Configure logging in `.env`:
```
LOG_LEVEL=INFO
LOG_FILE=./data/logs/agent.log
```

### 3. Database Maintenance

```bash
# Clean up old matches
python -c "from src.database import DatabaseManager; db = DatabaseManager(); db.cleanup_old_matches(days_old=30)"

# Export data
python -c "from src.database import DatabaseManager; db = DatabaseManager(); db.export_matches('backup.json', 'json')"
```

### 4. Updates

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
sudo systemctl restart fda-ndc-rxnorm-agent
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` files
2. **API Keys**: Use secure storage for any API keys
3. **Database**: Use strong passwords for production databases
4. **Network**: Configure firewalls and VPNs as needed
5. **Updates**: Keep dependencies updated regularly

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **Database Errors**: Check database URL and permissions
3. **API Errors**: Verify RxNorm API connectivity
4. **Memory Issues**: Reduce batch size for large datasets

### Support

- Check the README.md for detailed usage instructions
- Review the test suite for examples
- Open an issue on GitHub for bugs or feature requests 