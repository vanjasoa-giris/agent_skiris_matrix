#!/usr/bin/env python3
"""
Client MCP pour Elektra - Utilise HTTP simple pour appeler les tools

Note: Le SDK MCP a des problèmes de compatibilité avec httpx.
Cette implémentation utilise httpx directement pour appeler les tools.
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

logger = logging.getLogger("elektra.mcp")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s - %(message)s")

load_dotenv()


class McpClient:
    """Client MCP utilisant HTTP simple (plus stable que le SDK)."""

    def __init__(self, server_url: Optional[str] = None):
        self.server_url = server_url or os.getenv(
            "MCP_SERVER_URL", "http://localhost:8000"
        )
        self._client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> bool:
        """Établit la connexion au serveur MCP."""
        try:
            self._client = httpx.AsyncClient()
            # Test avec un health check
            resp = await self._client.get(f"{self.server_url}/health")
            if resp.status_code == 200:
                print(f"[MCP] Connecte: {self.server_url}")
                return True
            return False
        except Exception as e:
            print(f"[MCP] Erreur connexion: {e}")
            return False

    async def close(self):
        """Ferme le client."""
        if self._client:
            await self._client.aclose()

    async def _call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Appelle un tool MCP via JSON-RPC."""
        if not self._client:
            raise Exception("Pas de connexion MCP")

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }

        resp = await self._client.post(
            f"{self.server_url}/mcp", json=payload, timeout=60.0
        )
        if resp.status_code != 200:
            raise Exception(f"MCP Error {resp.status_code}: {resp.text}")

        result = resp.json()
        if "error" in result:
            raise Exception(f"MCP Tool Error: {result['error']}")

        return result.get("result", {})

    async def list_tools(self) -> list:
        """Liste les tools disponibles."""
        if not self._client:
            return []

        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

        resp = await self._client.post(
            f"{self.server_url}/mcp", json=payload, timeout=30.0
        )
        result = resp.json()
        tools = result.get("result", {}).get("tools", [])
        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Appelle un tool MCP."""
        result = await self._call_tool(name, arguments)

        # Extraire le content
        if isinstance(result, dict) and "content" in result:
            texts = []
            for item in result["content"]:
                if item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return "\n".join(texts)
        return result

    async def run_command(
        self, command: str, cwd: Optional[str] = None, timeout: int = 30
    ) -> Dict[str, Any]:
        """Exécute une commande système."""
        return await self._call_tool(
            "run_command", {"command": command, "cwd": cwd, "timeout": timeout}
        )

    async def run_npm(
        self, args: str, cwd: Optional[str] = None, timeout: int = 120
    ) -> Dict[str, Any]:
        """Exécute une commande npm."""
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

    async def elektra_chat(self, message: str, session_id: str = "default") -> str:
        """Envoie un message à Elektra."""
        result = await self._call_tool(
            "elektra_chat", {"message": message, "session_id": session_id}
        )

        # Extraire le texte de la réponse
        if isinstance(result, dict) and "content" in result:
            texts = []
            for item in result["content"]:
                if item.get("type") == "text":
                    texts.append(item.get("text", ""))
            return "\n".join(texts)
        return str(result)

    async def health_check(self) -> bool:
        """Vérifie que le serveur MCP est joignable."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.server_url}/health", timeout=5.0)
                return resp.status_code == 200
        except:
            return False


async def create_mcp_client() -> Optional[McpClient]:
    """Crée et teste un client MCP."""
    client = McpClient()

    if await client.health_check():
        if await client.connect():
            tools = await client.list_tools()
            tool_names = [t.get("name", "") for t in tools]
            print(f"[MCP] Tools: {len(tool_names)}")
            return client

    print(f"[MCP] Non accessible: {client.server_url}")
    return None
