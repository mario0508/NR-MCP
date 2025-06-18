import os
import json
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator
from datetime import datetime
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
NR_GRAPHQL_URL = "https://api.newrelic.com/graphql"
DEFAULT_ACCOUNT_ID = os.getenv("NEW_RELIC_ACCOUNT_ID", "")
API_KEY = os.getenv("NEW_RELIC_API_KEY", "")

# FastAPI app
app = FastAPI(title="NewRelic SSE Agent", description="SSE-enabled NewRelic Query Agent")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QueryRequest(BaseModel):
    query: str = Field(..., description="NRQL query string")
    account_id: str = Field(default="", description="New Relic account ID")
    stream: bool = Field(default=True, description="Enable streaming response")

class QueryResponse(BaseModel):
    status: str
    data: Any = None
    error: str = None
    timestamp: str

class StreamEvent(BaseModel):
    event: str
    data: Dict[str, Any]
    timestamp: str

class NewRelicAgent:
    """NewRelic Agent with SSE support"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.default_account_id = DEFAULT_ACCOUNT_ID
        self.session = None
        
        if not self.api_key:
            raise ValueError("NEW_RELIC_API_KEY environment variable is required")
        
        if not self.default_account_id:
            raise ValueError("NEW_RELIC_ACCOUNT_ID environment variable is required")

    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Content-Type": "application/json",
                "API-Key": self.api_key
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def execute_query(self, query: str, account_id: str = None) -> Dict[str, Any]:
        """Execute NRQL query against New Relic"""
        account_id = account_id or self.default_account_id
        
        graphql_query = f"""
        {{
            actor {{
                account(id: {account_id}) {{
                    nrql(query: "{query}") {{
                        results
                    }}
                }}
            }}
        }}
        """

        payload = {"query": graphql_query}
        
        try:
            response = await self.session.post(NR_GRAPHQL_URL, json=payload)
            response.raise_for_status()
            result = response.json()

            # Check for GraphQL errors
            if "errors" in result:
                logger.error(f"GraphQL errors: {result['errors']}")
                return {
                    "status": "error",
                    "error": f"GraphQL errors: {result['errors']}",
                    "data": None
                }

            # Extract data
            data = result.get("data")
            if not data:
                return {
                    "status": "error",
                    "error": "No 'data' field in response",
                    "data": None
                }

            actor = data.get("actor")
            if not actor:
                return {
                    "status": "error",
                    "error": "No 'actor' field in response",
                    "data": None
                }

            account = actor.get("account")
            if not account:
                return {
                    "status": "error",
                    "error": f"No account data for account ID {account_id}",
                    "data": None
                }

            nrql_result = account.get("nrql")
            if not nrql_result:
                return {
                    "status": "error",
                    "error": "No NRQL result in response",
                    "data": None
                }

            results = nrql_result.get("results", [])
            
            return {
                "status": "success",
                "data": results,
                "error": None,
                "query": query,
                "account_id": account_id,
                "result_count": len(results)
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "data": None
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "data": None
            }

    async def stream_query_results(self, query: str, account_id: str = None) -> AsyncGenerator[str, None]:
        """Stream query results as SSE events"""
        try:
            # Send initial event
            yield self._format_sse_event("query_start", {
                "query": query,
                "account_id": account_id or self.default_account_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Execute query
            result = await self.execute_query(query, account_id)
            
            # Send result event
            yield self._format_sse_event("query_result", result)
            
            # If successful and has data, stream individual results
            if result["status"] == "success" and result["data"]:
                for i, item in enumerate(result["data"]):
                    yield self._format_sse_event("data_item", {
                        "index": i,
                        "item": item,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    # Small delay to make streaming visible
                    await asyncio.sleep(0.1)

            # Send completion event
            yield self._format_sse_event("query_complete", {
                "status": result["status"],
                "timestamp": datetime.utcnow().isoformat()
            })

        except Exception as e:
            logger.error(f"Error in stream_query_results: {str(e)}")
            yield self._format_sse_event("error", {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    def _format_sse_event(self, event: str, data: Dict[str, Any]) -> str:
        """Format data as SSE event"""
        json_data = json.dumps(data)
        return f"event: {event}\ndata: {json_data}\n\n"

# Global agent instance
agent = None

@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    global agent
    try:
        agent = NewRelicAgent()
        logger.info("NewRelic SSE Agent started successfully")
    except Exception as e:
        logger.error(f"Failed to start agent: {str(e)}")
        raise

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "NewRelic SSE Agent",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "api_key_configured": bool(API_KEY),
        "account_id_configured": bool(DEFAULT_ACCOUNT_ID),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/query")
async def execute_query(request: QueryRequest):
    """Execute NRQL query (non-streaming)"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    async with agent as nr_agent:
        result = await nr_agent.execute_query(request.query, request.account_id)
        
        return QueryResponse(
            status=result["status"],
            data=result.get("data"),
            error=result.get("error"),
            timestamp=datetime.utcnow().isoformat()
        )

@app.post("/query/stream")
async def stream_query(request: QueryRequest):
    """Execute NRQL query with SSE streaming"""
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    if not request.stream:
        # Fall back to regular query
        return await execute_query(request)
    
    async def event_generator():
        async with agent as nr_agent:
            async for event in nr_agent.stream_query_results(request.query, request.account_id):
                yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

@app.get("/examples")
async def get_query_examples():
    """Get example NRQL queries"""
    return {
        "examples": [
            {
                "title": "Recent Transactions",
                "query": "SELECT * FROM Transaction SINCE 1 hour ago LIMIT 10",
                "description": "Get recent transactions from the last hour"
            },
            {
                "title": "Error Analysis",
                "query": "SELECT * FROM Transaction WHERE error IS TRUE SINCE 1 hour ago LIMIT 10",
                "description": "Find transactions with errors"
            },
            {
                "title": "Performance Analysis",
                "query": "SELECT average(duration) FROM Transaction FACET name ORDER BY average(duration) DESC LIMIT 5",
                "description": "Get slowest endpoints by average duration"
            },
            {
                "title": "Log Analysis",
                "query": "SELECT * FROM Log WHERE level = 'ERROR' SINCE 30 minutes ago LIMIT 20",
                "description": "Get recent error logs"
            },
            {
                "title": "Infrastructure Metrics",
                "query": "SELECT average(cpuPercent) FROM SystemSample FACET hostname SINCE 1 hour ago",
                "description": "Get CPU usage by host"
            }
        ]
    }

@app.get("/tools")
async def get_available_tools():
    """Get available tools/endpoints"""
    return {
        "tools": [
            {
                "name": "query",
                "endpoint": "/query",
                "method": "POST",
                "description": "Execute NRQL query (non-streaming)",
                "streaming": False
            },
            {
                "name": "stream_query",
                "endpoint": "/query/stream",
                "method": "POST",
                "description": "Execute NRQL query with SSE streaming",
                "streaming": True
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "6000")),
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info"
    )