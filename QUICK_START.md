# Quick Start Guide - Growth Flywheel 2.5

## Using the New Components

### Frontend Components

#### 1. Project Management

```tsx
import { ProjectList } from '@/components/dashboard/ProjectList';
import { CreateProjectDialog } from '@/components/dashboard/CreateProjectDialog';
import { ProjectCard } from '@/components/dashboard/ProjectCard';

// In your component
function ProjectsPage() {
  const [showDialog, setShowDialog] = useState(false);
  const [selectedProject, setSelectedProject] = useState(null);

  return (
    <>
      <ProjectList
        onCreateClick={() => setShowDialog(true)}
        onEditClick={(project) => {
          setSelectedProject(project);
          setShowDialog(true);
        }}
        onViewClick={(project) => navigate(`/projects/${project.id}`)}
      />

      <CreateProjectDialog
        isOpen={showDialog}
        onClose={() => {
          setShowDialog(false);
          setSelectedProject(null);
        }}
        editProject={selectedProject}
        onSuccess={() => {
          // Refresh project list
        }}
      />
    </>
  );
}
```

#### 2. Reference Management

```tsx
import { ReferenceUpload } from '@/components/reference/ReferenceUpload';
import { ReferenceList } from '@/components/reference/ReferenceList';
import { ReferenceAnalysis } from '@/components/reference/ReferenceAnalysis';

function ReferencePage() {
  const [selectedReference, setSelectedReference] = useState(null);

  return (
    <div>
      <ReferenceUpload
        projectId={projectId}
        onUploadSuccess={(files) => {
          // Refresh reference list
        }}
        maxFiles={10}
        maxSizeMB={50}
      />

      <ReferenceList
        projectId={projectId}
        onViewAnalysis={(ref) => setSelectedReference(ref)}
      />

      {selectedReference && (
        <ReferenceAnalysis
          referenceId={selectedReference.id}
          referenceName={selectedReference.name}
        />
      )}
    </div>
  );
}
```

#### 3. Export Functionality

```tsx
import { ExportDialog } from '@/components/common/ExportDialog';

function SessionPage() {
  const [showExport, setShowExport] = useState(false);

  return (
    <>
      <button onClick={() => setShowExport(true)}>
        Export Session
      </button>

      <ExportDialog
        isOpen={showExport}
        onClose={() => setShowExport(false)}
        exportType="session"
        itemId={sessionId}
        itemName={`Session ${sessionId}`}
      />
    </>
  );
}
```

### Backend API Usage

#### 1. Export Endpoints

```python
# Export session as JSON
GET /api/v1/export/sessions/1/export?format=json&include_messages=true

# Export session as Markdown
GET /api/v1/export/sessions/1/export?format=markdown&include_evaluation=true

# Export session as PDF
GET /api/v1/export/sessions/1/export?format=pdf

# Export project
GET /api/v1/export/projects/1/export?format=json&include_sessions=true

# Export analytics
GET /api/v1/export/analytics/export?format=csv
```

#### 2. Using Export Service

```python
from app.services.export_service import export_service, ExportFormat

# Export session
session_data = {...}
exported_data = await export_service.export_session(
    session_data,
    ExportFormat.JSON,
    include_messages=True,
    include_evaluation=True
)

# Export project
project_data = {...}
exported_data = await export_service.export_project(
    project_data,
    ExportFormat.MARKDOWN,
    include_sessions=True
)

# Export analytics
analytics_data = {...}
exported_data = await export_service.export_analytics(
    analytics_data,
    ExportFormat.CSV
)
```

### Running Tests

```bash
# Run all tests
cd backend
pytest

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_agents.py -v

# Run specific test
pytest tests/unit/test_agents.py::TestSalesCoachAgent::test_provide_feedback -v
```

### Deployment

#### Docker Compose

```bash
# Start all services
cd deployment/docker
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

#### Kubernetes

```bash
# Deploy to cluster
kubectl apply -f deployment/kubernetes/deployment.yaml

# Check status
kubectl get pods -l app=salesboost
kubectl get services -l app=salesboost

# View logs
kubectl logs -f deployment/salesboost-backend

# Scale deployment
kubectl scale deployment salesboost-backend --replicas=5

# Check autoscaler
kubectl get hpa
```

### Monitoring

#### Prometheus Queries

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Active sessions
active_sessions_total
```

#### Grafana Dashboards

1. Access Grafana: http://localhost:3001
2. Login with admin credentials
3. Import dashboards from `deployment/monitoring/dashboards/`

### Environment Setup

#### Backend .env

```bash
ENV_STATE=development
DEBUG=true
LOG_LEVEL=INFO

DATABASE_URL=postgresql://user:pass@localhost:5432/salesboost
REDIS_URL=redis://localhost:6379

OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

#### Frontend .env

```bash
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://...
VITE_SUPABASE_KEY=...
```

### Common Tasks

#### Add Export Route to Main App

```python
# In backend/main.py
def _register_api_routes(app: FastAPI) -> None:
    # ... existing routes ...

    # Export endpoints
    _safe_include("app.api.endpoints.export", "/api/v1/export", tags=["export"])
```

#### Create New Export Format

```python
# In export_service.py
class ExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"  # New format

# Add export method
def _export_excel(self, data: Dict[str, Any]) -> bytes:
    import openpyxl
    # Implementation
    pass
```

#### Add New Test

```python
# In tests/unit/test_agents.py
@pytest.mark.asyncio
async def test_new_feature(self, agent):
    """Test new feature."""
    result = await agent.new_feature()
    assert result is not None
```

### Troubleshooting

#### Frontend Build Issues

```bash
# Clear cache
rm -rf node_modules dist
npm install
npm run build

# Check TypeScript errors
npm run check
```

#### Backend Import Errors

```bash
# Verify Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/backend"

# Install dependencies
pip install -r requirements.txt
```

#### Docker Issues

```bash
# Remove all containers and volumes
docker-compose down -v

# Rebuild without cache
docker-compose build --no-cache

# Check container logs
docker-compose logs backend
```

### Performance Tips

1. **Frontend**:
   - Use React.memo for expensive components
   - Implement virtual scrolling for large lists
   - Lazy load components with React.lazy

2. **Backend**:
   - Enable Redis caching
   - Use connection pooling
   - Implement request batching

3. **Database**:
   - Add indexes on frequently queried columns
   - Use database connection pooling
   - Implement query result caching

### Security Checklist

- [ ] Environment variables not committed
- [ ] API keys stored in secrets
- [ ] HTTPS enabled in production
- [ ] CORS configured properly
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] XSS protection headers
- [ ] Authentication required for sensitive endpoints
- [ ] Regular security updates

### Next Steps

1. Register export routes in main.py
2. Run test suite to verify implementation
3. Deploy to staging environment
4. Configure monitoring dashboards
5. Set up CI/CD secrets
6. Perform load testing
7. Deploy to production

## Support

- Documentation: See DEPLOYMENT_GUIDE.md
- Issues: GitHub Issues
- Tests: Run `pytest -v` for detailed output
