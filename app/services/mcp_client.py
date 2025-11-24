"""
MCP Integration Layer for OntExtract

Provides single abstraction for all external MCP server communication
with automatic fallback to HTTP REST API if MCP unavailable.

Architecture:
- Primary: JSON-RPC MCP protocol (if server available)
- Fallback: HTTP REST API to OntServe web server
- Transparent: Application code doesn't need to know which is being used
"""

import os
import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Exception raised for MCP client errors"""
    pass


class MCPClient:
    """
    Abstraction layer for MCP server communication.

    Provides transparent failover:
    1. Try MCP server (JSON-RPC over HTTP)
    2. Fallback to OntServe web API (HTTP REST)

    Usage:
        client = MCPClient()
        result = await client.call_mcp("sparql_query", {"query": "..."})
    """

    def __init__(
        self,
        mcp_url: str = None,
        http_fallback_url: str = None,
        timeout: int = 30,
        max_retries: int = 2
    ):
        """
        Initialize MCP client with fallback.

        Args:
            mcp_url: MCP server URL (JSON-RPC)
            http_fallback_url: OntServe web server URL (REST)
            timeout: Request timeout in seconds
            max_retries: Number of retry attempts before fallback
        """
        self.mcp_url = mcp_url or os.environ.get('ONTSERVE_MCP_URL', 'http://localhost:8083')
        self.http_fallback_url = http_fallback_url or os.environ.get('ONTSERVE_WEB_URL', 'http://localhost:5003')
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = None
        self._request_id = 1
        self._use_mcp = None  # Determined on first request
        self._cache = {}  # Simple in-memory cache
        self._cache_ttl = timedelta(hours=1)

        logger.info(f"MCP client initialized - MCP: {self.mcp_url}, Fallback: {self.http_fallback_url}")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with connection pooling."""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
                keepalive_timeout=60
            )
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            )
        return self.session

    async def check_mcp_available(self) -> bool:
        """
        Check if MCP server is available.

        Returns:
            True if MCP server responds, False otherwise
        """
        try:
            session = await self._get_session()
            # Try a simple MCP method
            async with session.post(self.mcp_url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "list_tools",
                "params": {}
            }, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
        except Exception as e:
            logger.debug(f"MCP server check failed: {e}")
            return False

    async def _call_mcp_server(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call MCP server using JSON-RPC protocol.

        Args:
            method: MCP method name
            params: Method parameters

        Returns:
            Method result

        Raises:
            MCPClientError: On communication or server error
        """
        session = await self._get_session()

        request_data = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }
        self._request_id += 1

        logger.debug(f"MCP request: {method}")

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with session.post(self.mcp_url, json=request_data) as response:
                    if response.status == 200:
                        result = await response.json()

                        if "error" in result:
                            raise MCPClientError(f"MCP server error: {result['error']}")

                        return result.get("result", {})
                    else:
                        error_text = await response.text()
                        raise MCPClientError(f"HTTP {response.status}: {error_text}")

            except aiohttp.ClientError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    break
            except Exception as e:
                last_error = e
                break

        raise MCPClientError(f"MCP request failed after {self.max_retries} attempts: {last_error}")

    async def _call_http_api(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback to HTTP REST API.

        Args:
            method: Method name (mapped to HTTP endpoint)
            params: Parameters (mapped to query/body)

        Returns:
            API response

        Raises:
            MCPClientError: On API error
        """
        session = await self._get_session()

        # Map MCP methods to HTTP endpoints
        endpoint_map = {
            "list_ontology_classes": "/editor/api/ontologies/{ontology}/classes",
            "sparql_query": "/editor/api/ontologies/{ontology}/sparql",
            "get_ontology_metadata": "/editor/api/ontologies/{ontology}/metadata",
        }

        ontology = params.get("ontology", "semantic-change-ontology")
        endpoint_template = endpoint_map.get(method)

        if not endpoint_template:
            raise MCPClientError(f"No HTTP fallback for MCP method: {method}")

        endpoint = endpoint_template.format(ontology=ontology)
        url = f"{self.http_fallback_url}{endpoint}"

        logger.debug(f"HTTP fallback request: {method} -> {url}")

        try:
            # Different methods use different HTTP verbs
            if method == "sparql_query":
                async with session.post(url, json={"query": params.get("query")}) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise MCPClientError(f"HTTP {response.status}: {error_text}")
            else:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        raise MCPClientError(f"HTTP {response.status}: {error_text}")

        except aiohttp.ClientError as e:
            raise MCPClientError(f"HTTP API call failed: {e}")

    async def call_mcp(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call MCP method with automatic fallback.

        Args:
            method: MCP method name
            params: Method parameters

        Returns:
            Method result

        Raises:
            MCPClientError: If both MCP and fallback fail
        """
        # Determine communication method on first call
        if self._use_mcp is None:
            self._use_mcp = await self.check_mcp_available()
            if self._use_mcp:
                logger.info("Using MCP server for ontology communication")
            else:
                logger.info("MCP server unavailable, using HTTP REST fallback")

        # Check cache first
        cache_key = f"{method}:{json.dumps(params, sort_keys=True)}"
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                logger.debug(f"Cache hit for {method}")
                return cached_data

        # Try primary method
        result = None
        primary_error = None

        if self._use_mcp:
            try:
                result = await self._call_mcp_server(method, params)
            except MCPClientError as e:
                primary_error = e
                logger.warning(f"MCP call failed: {e}, trying HTTP fallback")
                self._use_mcp = False  # Switch to fallback for future calls

        # Try fallback if primary failed or not using MCP
        if result is None:
            try:
                result = await self._call_http_api(method, params)
            except MCPClientError as e:
                # Both methods failed
                error_msg = f"Both MCP and HTTP failed. MCP: {primary_error}, HTTP: {e}"
                raise MCPClientError(error_msg)

        # Cache successful result
        if result is not None:
            self._cache[cache_key] = (result, datetime.now())

        return result

    async def close(self):
        """Close HTTP session and cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None

    @asynccontextmanager
    async def managed_session(self):
        """
        Context manager for automatic session cleanup.

        Usage:
            async with client.managed_session():
                result = await client.call_mcp(...)
        """
        try:
            yield self
        finally:
            await self.close()


# Global MCP client instance (singleton pattern)
_global_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """
    Get global MCP client instance.

    Returns:
        Singleton MCPClient instance
    """
    global _global_mcp_client
    if _global_mcp_client is None:
        _global_mcp_client = MCPClient()
    return _global_mcp_client


async def warmup_mcp_client():
    """
    Warmup MCP client (check availability, populate cache).
    Call this on application startup.
    """
    client = get_mcp_client()
    try:
        available = await client.check_mcp_available()
        logger.info(f"MCP client warmup complete - Available: {available}")
    except Exception as e:
        logger.warning(f"MCP client warmup failed: {e}")
