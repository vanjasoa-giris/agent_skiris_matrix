#!/usr/bin/env python3
"""
Client MCP pour Elektra - Utilise le SDK officiel MCP (mcp[cli]).
Compatible avec le transport Streamable HTTP (SSE).
"""

import logging
import os
import asyncio
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv

logger = logging.getLogger("elektra.mcp")
load_dotenv()

class McpClient:
    """Client MCP utilisant le SDK officiel pour gérer les sessions et le transport SSE."""

    def __init__(self, server_url: Optional[str] = None):
        # On s'assure que l'URL pointe bien vers l'endpoint /mcp du serveur
        url = server_url or os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        if not url.endswith("/mcp"):
            url = f"{url.rstrip('/')}/mcp"
        self.server_url = url
        
        self._exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None

    async def connect(self) -> bool:
        """Établit la connexion SSE et initialise la session MCP via le SDK."""
        try:
            print(f"[MCP] Connexion SSE à {self.server_url}...")
            
            # 1. Établir le transport SSE
            # sse_client retourne un tuple (read_stream, write_stream)
            streams = await self._exit_stack.enter_async_context(sse_client(self.server_url))
            read, write = streams
            
            # 2. Créer la session MCP sur ces flux
            self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            
            # 3. Initialiser la session (handshake obligatoire)
            await self.session.initialize()
            
            print(f"[MCP] Session initialisée avec succès.")
            return True
            
        except Exception as e:
            print(f"[MCP] Échec de connexion au SDK: {e}")
            await self.close()
            return False

    async def close(self):
        """Ferme proprement la session et le transport."""
        await self._exit_stack.aclose()
        self.session = None

    async def list_tools(self) -> List[Any]:
        """Liste les outils disponibles via le SDK."""
        if not self.session:
            return []
        try:
            result = await self.session.list_tools()
            # Le SDK retourne un objet ToolsList qui a un attribut 'tools'
            return result.tools
        except Exception as e:
            logger.error(f"Erreur lors de la liste des outils: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Appelle un outil MCP et retourne le texte du contenu."""
        if not self.session:
            return "❌ Erreur: Client MCP non connecté."
            
        try:
            # Appel via le SDK
            result = await self.session.call_tool(name, arguments)
            
            # Extraction du contenu textuel du résultat
            texts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    texts.append(content.text)
                elif isinstance(content, dict) and content.get('type') == 'text':
                    texts.append(content.get('text', ''))
            
            return "\n".join(texts)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'appel de l'outil {name}: {e}")
            return f"❌ Erreur lors de l'exécution de l'outil: {e}"

    # --- Méthodes de commodité pour correspondre à l'usage dans main.py ---

    async def run_command(self, command: str) -> Dict[str, Any]:
        """Compatibilité avec l'ancienne signature."""
        output = await self.call_tool("run_command", {"command": command})
        return {"stdout": output, "stderr": ""}

    async def run_npm(self, args: str) -> Dict[str, Any]:
        """Compatibilité avec l'ancienne signature."""
        output = await self.call_tool("run_npm", {"args": args})
        return {"stdout": output, "stderr": ""}

    async def run_python(self, script: str) -> Dict[str, Any]:
        """Compatibilité avec l'ancienne signature."""
        output = await self.call_tool("run_python", {"script": script})
        return {"stdout": output, "stderr": ""}

    async def health_check(self) -> bool:
        """Vérifie sommairement la disponibilité du serveur."""
        import httpx
        try:
            # On vérifie la route /health simple de Starlette avant de lancer le SDK
            health_url = self.server_url.replace("/mcp", "/health")
            async with httpx.AsyncClient() as client:
                resp = await client.get(health_url, timeout=5.0)
                return resp.status_code == 200
        except:
            return False

async def create_mcp_client() -> Optional[McpClient]:
    """Factory pour créer et connecter le client SDK."""
    client = McpClient()
    if await client.health_check():
        if await client.connect():
            tools = await client.list_tools()
            print(f"[MCP] Outils détectés: {len(tools)}")
            return client
    
    print(f"[MCP] Le serveur à {client.server_url} ne répond pas.")
    return None
