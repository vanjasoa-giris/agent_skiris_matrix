#!/usr/bin/env python3
"""
Client MCP pour Elektra

Permet à l'agent de se connecter au MCP Server et d'exécuter des outils.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, Optional

import aiohttp
from dotenv import load_dotenv

logger = logging.getLogger("elektra.mcp")

load_dotenv()


class McpClient:
    """Client pour interagir avec le serveur MCP."""

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or os.getenv(
            "MCP_SERVER_URL", "http://localhost:8000"
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.tools_cache: Optional[Dict[str, Any]] = None

    async def __aenter__(self):
        """Contexte async entry."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Contexte async exit."""
        if self.session:
            await self.session.close()

    async def _call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Appelle un tool MCP via l'endpoint /mcp."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        async with self.session.post(
            f"{self.server_url}/mcp",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"MCP Error {response.status}: {error_text}")

            result = await response.json()

            if "error" in result:
                raise Exception(f"MCP Tool Error: {result['error']}")

            return result.get("result", {})

    async def get_tools(self) -> Dict[str, Any]:
        """Récupère la liste des tools disponibles."""
        if self.tools_cache:
            return self.tools_cache

        if not self.session:
            self.session = aiohttp.ClientSession()

        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

        async with self.session.post(
            f"{self.server_url}/mcp",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            result = await response.json()
            self.tools_cache = result.get("result", {})
            return self.tools_cache

    async def run_command(
        self, command: str, cwd: Optional[str] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        """Exécute une commande système."""
        logger.info(f"MCP run_command: {command[:50]}...")
        return await self._call_tool(
            "run_command", {"command": command, "cwd": cwd, "timeout": timeout}
        )

    async def run_npm(
        self, args: str, cwd: Optional[str] = None, timeout: int = 120
    ) -> Dict[str, Any]:
        """Exécute une commande npm."""
        logger.info(f"MCP run_npm: {args}")
        return await self._call_tool(
            "run_npm", {"args": args, "cwd": cwd, "timeout": timeout}
        )

    async def run_python(
        self,
        script: str,
        args: Optional[str] = None,
        cwd: Optional[str] = None,
        timeout: int = 60,
    ) -> Dict[str, Any]:
        """Exécute un script Python."""
        logger.info(f"MCP run_python: {script[:50]}...")
        return await self._call_tool(
            "run_python",
            {"script": script, "args": args, "cwd": cwd, "timeout": timeout},
        )

    async def get_system_info(self) -> Dict[str, Any]:
        """Récupère les informations système."""
        return await self._call_tool("get_system_info", {})

    async def check_docker(self, action: str = "ps") -> Dict[str, Any]:
        """Vérifie l'état de Docker."""
        return await self._call_tool("check_docker", {"action": action})

    async def health_check(self) -> bool:
        """Vérifie que le serveur MCP est joignable."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            async with self.session.get(
                f"{self.server_url}/health", timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


async def create_mcp_client() -> Optional[McpClient]:
    """Crée et teste un client MCP."""
    client = McpClient()

    if await client.health_check():
        logger.info(f"Connecté au MCP Server: {client.server_url}")
        tools = await client.get_tools()
        logger.info(f"Tools disponibles: {list(tools.get('tools', []))}")
        return client
    else:
        logger.warning(f"MCP Server non accessible: {client.server_url}")
        return None
