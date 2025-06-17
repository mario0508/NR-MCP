# NewRelic SSE Agent

A Server-Sent Events (SSE) enabled agent for querying NewRelic data using NRQL queries. This project converts the original MCP NewRelic server into a containerized SSE-supported web service.

## 🚀 Features

- **SSE Streaming**: Real-time streaming of query results using Server-Sent Events
- **REST API**: Traditional REST endpoints for non-streaming queries
- **Docker Support**: Fully containerized with Docker and Docker Compose
- **Health Monitoring**: Built-in health checks and monitoring endpoints
- **Web Client**: HTML test client for testing SSE functionality
- **Production Ready**: Optimized for production with proper logging, error handling, and security

## 📋 Prerequisites

- Docker and Docker Compose
- NewRelic account with API access
- NewRelic API Key (User Key)
- NewRelic Account ID

## 🛠️ Setup

### 1. Clone and Setup

```bash
# Create project directory
mkdir newrelic-sse-agent
cd newrelic-sse-agent

# Copy all the provided files into this directory
# - app.py
# - Dockerfile
# - docker-compose.yml
# - requirements.txt
# - static/test-client.html (create static directory)
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```bash
# .env file
NEW_RELIC_API_KEY=your-newrelic-api-key-here
NEW_RELIC_ACCOUNT_ID=your-account-id-here
PORT=8000
ENVIRONMENT=production
```

### 3. Directory Structure

```
newrelic-sse-agent/
├── app.py                 # Main SSE agent application
├── Dockerfile             # Docker container configuration
├── docker-compose.yml     # Docker Compose setup
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
├── static/
│   └── test-client.html   # SSE test client
├── templates/             # (Optional) HTML templates
├── logs/                  # Log files directory
└── README.md             # This file
```

### 4. Build and Run

#### Using Docker Compose (Recommended)

```bash
# Build and start the service
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f newrelic-sse-agent

# Stop services
docker-compose down
```

#### Using Docker directly

```bash
# Build the image
docker build -t newrelic-sse-agent .

# Run the container
docker run -d \
  --name newrelic-sse-agent \
  -p 8000:8000 \
  -e NEW_RELIC_API_KEY=your-api-key \
  -e NEW_RELIC_ACCOUNT_ID=your-account-id \
  newrelic-sse-agent
```

#### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export NEW_RELIC_API_KEY="your-api-key"
export NEW_RELIC_ACCOUNT_ID="your-account-id"

# Run the application
python app.py
```

## 📡 API Endpoints

### Health and Status

- `GET /` - Basic health check
- `GET /health` - Detailed health information
- `GET /examples` - Get example NRQL queries
- `GET /tools` - List available tools/endpoints

### Query Endpoints

#### Non-Streaming Query
```bash
POST /query
Content-Type: application/json

{
  "query": "SELECT * FROM Transaction SINCE 1 hour ago LIMIT 10",
  "account_id": "optional-account-id",
  "stream": false
}
```

#### SSE Streaming Query
```bash
POST /query/stream
Content-Type: application/json

{
  "query": "SELECT * FROM Transaction SINCE 1 hour ago LIMIT 10",
  "account_id": "optional-account-id", 
  "stream": true
}
```

## 🌐 SSE Events

The streaming endpoint emits the following event types:

- `query_start` - Query execution begins
- `query_result` - Complete query result
- `data_item` - Individual data items (streamed)
- `query_complete` - Query execution finished
- `error` - Error occurred

## 🧪 Testing

### Using the Web Client

1. Open your browser to `http://localhost:8000/static/test-client.html`
2. Enter your NRQL query
3. Click "Start SSE Stream" to test streaming
4. Or click "Execute Query" for non-streaming requests

### Using curl

#### Health Check
```bash
curl http://localhost:8000/health
```

#### Non-Streaming Query
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT * FROM Transaction SINCE 1 hour ago LIMIT 5",
    "stream": false
  }'
```

#### SSE Streaming
```bash
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "query": "SELECT * FROM Transaction SINCE 1 hour ago LIMIT 5",
    "stream": true
  }'
```

## 📊 Example NRQL Queries

### Application Performance
```sql
-- Recent transactions
SELECT * FROM Transaction SINCE 1 hour ago LIMIT 10

-- Error analysis
SELECT * FROM Transaction WHERE error IS TRUE SINCE 1 hour ago LIMIT 10

-- Slowest endpoints
SELECT average(duration) FROM Transaction FACET name ORDER BY average(duration) DESC LIMIT 5

-- Transaction throughput
SELECT count(*) FROM Transaction FACET name TIMESERIES SINCE 1 hour ago
```

### Infrastructure Monitoring
```sql
-- CPU usage by host
SELECT average(cpuPercent) FROM SystemSample FACET hostname SINCE 1 hour ago

-- Memory usage
SELECT average(memoryUsedPercent) FROM SystemSample FACET hostname SINCE 1 hour ago

-- Disk I/O
SELECT average(diskReadBytesPerSecond), average(diskWriteBytesPerSecond) FROM SystemSample FACET hostname SINCE 1 hour ago
```

### Log Analysis
```sql
-- Error logs
SELECT * FROM Log WHERE level = 'ERROR' SINCE 30 minutes ago LIMIT 20

-- Log patterns
SELECT count(*) FROM Log FACET message SINCE 1 hour ago ORDER BY count DESC LIMIT 10

-- Application logs
SELECT * FROM Log WHERE appName = 'your-app' SINCE 1 hour ago LIMIT 10
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|----------|
| `NEW_RELIC_API_KEY` | NewRelic User API Key | Yes | - |
| `NEW_RELIC_ACCOUNT_ID` | NewRelic Account ID | Yes | - |
| `PORT` | Server port | No | 8000 |
| `ENVIRONMENT` | Environment (development/production) | No | production |

### Docker Compose Profiles

- `default` - Basic agent service
- `production` - Includes Nginx reverse proxy
- `caching` - Includes Redis for caching

```bash
# Run with specific profile
docker-compose --profile production up

# Run with multiple profiles
docker-compose --profile production --profile caching up
```

## 🔒 Security

- Non-root user in container
- API key passed via environment variables
- CORS headers configurable
- Input validation on all endpoints
- Rate limiting ready (can be added with middleware)

## 📈 Monitoring

### Health Checks
The service includes built-in health checks:
- Container health check via Docker
- HTTP health endpoint at `/health`
- Logging to stdout/stderr

### Metrics
Monitor these key metrics:
- Response times
- Error rates
- Active SSE connections
- Query execution times
- Memory and CPU usage

## 🐛 Troubleshooting

### Common Issues

1. **API Key Issues**
   ```bash
   # Check if API key is set
   curl http://localhost:8000/health
   ```

2. **Connection Issues**
   ```bash
   # Check container logs
   docker-compose logs newrelic-sse-agent
   
   # Check network connectivity
   docker exec newrelic-sse-agent curl -I https://api.newrelic.com
   ```

3. **Query Issues**
   - Verify NRQL syntax
   - Check account ID matches your NewRelic account
   - Ensure data exists in the queried time range

### Debug Mode

Run in development mode for verbose logging:
```bash
# In docker-compose.yml, change:
ENVIRONMENT=development

# Or locally:
export ENVIRONMENT=development
python app.py
```

## 🚀 Production Deployment

### Using Docker Compose with Nginx

1. Configure SSL certificates in `./ssl/` directory
2. Customize `nginx.conf` for your domain
3. Run with production profile:
   ```bash
   docker-compose --profile production up -d
   ```

### Scaling

For high-traffic scenarios:
1. Use multiple container instances
2. Add load balancer (Nginx/HAProxy)
3. Implement Redis caching
4. Monitor resource usage

### Environment-Specific Configurations

Create environment-specific docker-compose files:
- `docker-compose.prod.yml`
- `docker-compose.staging.yml`
- `docker-compose.dev.yml`

## 📝 Development

### Adding New Features

1. Modify `app.py` for new endpoints
2. Update `requirements.txt` for new dependencies
3. Rebuild Docker image
4. Test with the web client

### Contributing

1. Fork the repository
2. Create feature branch
3. Add tests
4. Submit pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- Check logs: `docker-compose logs -f`
- Health check: `curl http://localhost:8000/health`
- Test client: `http://localhost:8000/static/test-client.html`
- NewRelic API docs: https://docs.newrelic.com/docs/apis/rest-api-v2/

---

**Happy querying! 🎉**