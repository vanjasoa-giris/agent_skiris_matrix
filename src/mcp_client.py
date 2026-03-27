#!/usr/bin/env python3
"""
Client MCP pour Elektra - Utilise le même SDK que le serveur

Permet à l'agent de se connecter au MCP Server via Streamable HTTP.
"""

import logging
import os
from typing import Any, Dict, Optional

from mcp.client.session import ClientSession
from mcp.client.streamable_http import StreamableHTTPTransport
from dotenv import load_dotenv

logger = logging.getLogger("elektra.mcp")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")

load_dotenv()


class McpClient:
    """Client MCP officiel utilisant Streamable HTTP (même SDK que le serveur)."""

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or os.getenv(
            "MCP_SERVER_URL", "http://localhost:8000"
        )
        self._transport: Optional[StreamableHTTPTransport] = None
        self._session: Optional[ClientSession] = None

    async def connect(self) -> bool:
        """Établit la connexion au serveur MCP."""
        try:
            self._transport = StreamableHTTPTransport(url=f"{self.server_url}/mcp")
            async with self._transport as session:
                self._session = session
                return True
        except Exception as e:
            print(f"❌ Connexion MCP échouée: {e}")
            return False

    async def list_tools(self) -> list:
        """Liste les tools disponibles."""
        if not self._session:
            return []
        result = await self._session.list_tools()
        return result.tools if hasattr(result, "tools") else []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Appelle un tool MCP."""
        if not self._session:
            raise Exception("Pas de connexion MCP")
        return await self._session.call_tool(name, arguments)

    async def run_command(
        self, command: str, cwd: Optional[str] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        """Exécute une commande système."""
        return await self.call_tool(
            "run_command", {"command": command, "cwd": cwd, "timeout": timeout}
        )

    async def run_npm(
        self, args: str, cwd: Optional[str] = None, timeout: int = 120
    ) -> Dict[str, Any]:
        """Exécute une commande npm."""
        return await self.call_tool(
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
        return await self.call_tool(
            "run_python",
            {"script": script, "args": args, "cwd": cwd, "timeout": timeout},
        )

    async def get_system_info(self) -> Dict[str, Any]:
        """Récupère les informations système."""
        return await self.call_tool("get_system_info", {})

    async def check_docker(self, action: str = "ps") -> Dict[str, Any]:
        """Vérifie l'état de Docker."""
        return await self.call_tool("check_docker", {"action": action})

    async def elektra_chat(self, message: str, session_id: str = "default") -> str:
        """Envoie un message à Elektra."""
        result = await self.call_tool(
            "elektra_chat", {"message": message, "session_id": session_id}
        )
        if hasattr(result, "content"):
            return str(
                result.content[0].text
                if hasattr(result.content[0], "text")
                else result.content[0]
            )
        return str(result)

    async def health_check(self) -> bool:
        """Vérifie que le serveur MCP est joignable."""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.server_url}/health", timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except:
            return False


async def create_mcp_client() -> Optional[McpClient]:
    """Crée et teste un client MCP."""
    client = McpClient()

    if await client.health_check():
        if await client.connect():
            tools = await client.list_tools()
            print(f"✅ MCP Connecté - Tools: {len(tools)}")
            return client

    print(f"⚠️ MCP Server non accessible: {client.server_url}")
    return None
