import asyncio
import logging
import os
import re
import sys
from typing import Dict, List, Optional

from dotenv import load_dotenv
from nio import AsyncClient, MatrixRoom, RoomMessageText, LoginResponse, LoginError
from mistralai.client import Mistral

# Import de nos nouvelles classes (Refactoring: Extract Class)
from .formatter import ResponseFormatter
from .mcp_client import McpClient

# Configuration logging - Only ERROR and important messages
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("elektra.matrix")

# Charger les variables d'environnement
load_dotenv()

# --- Refactoring: Extraction de l'Agent IA ---


class ElektraAgent:
    """Agent IA encapsulé avec accès aux outils MCP."""

    def __init__(
        self, api_key: str, model: str, mcp_client: Optional[McpClient] = None
    ):
        self.client = Mistral(api_key=api_key)
        self.model = model
        self.prompt = os.getenv(
            "AGENT_SYSTEM_PROMPT", "Tu es Elektra, assistante DevOps."
        )
        self._history: Dict[str, List[dict]] = {}
        self.mcp_client = mcp_client

    async def chat(self, message: str, session_id: str) -> str:
        """Logique de génération de réponse IA."""
        history = self._history.get(session_id, [])

        # Construire les messages avec outil MCP si disponible
        messages = [
            {"role": "system", "content": self.prompt},
            *history,
            {"role": "user", "content": message},
        ]

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.complete(model=self.model, messages=messages),
            )
            answer = response.choices[0].message.content

            # Vérifier si réponse nécessite exécution de commande
            if self.mcp_client:
                answer = await self._handle_mcp_tools(answer)

            # Mise à jour de l'historique (Refactoring: Extract Method)
            self._update_history(session_id, message, answer)
            return answer
        except Exception as e:
            logger.error(f"Erreur IA: {e}")
            return "❌ Erreur technique lors de la réflexion."

    async def _handle_mcp_tools(self, answer: str) -> str:
        """Détecte et exécute les commandes via MCP."""
        # Patterns pour détecter les commandes à exécuter
        command_pattern = r"```(?:bash|shell|cmd)(.*?)```"
        npm_pattern = r"npm\s+(.*?)(?:\n|$)"
        python_pattern = r"python\s+(-c\s+.*?)(?:\n|$)"

        # Extraire les commandes du contexte
        commands = re.findall(command_pattern, answer, re.DOTALL)
        commands += re.findall(npm_pattern, answer)
        commands += re.findall(python_pattern, answer)

        if not commands:
            return answer

        # Exécuter via MCP
        results = []
        for cmd in commands:
            cmd = cmd.strip()
            print(f"⚡ Exécution: {cmd[:50]}...")

            try:
                if cmd.startswith("npm "):
                    result = await self.mcp_client.run_npm(cmd[4:])
                elif cmd.startswith("python ") or cmd.startswith("-c "):
                    result = await self.mcp_client.run_python(cmd)
                else:
                    result = await self.mcp_client.run_command(cmd)
                results.append(
                    f"```\n{result.get('stdout', '')}\n{result.get('stderr', '')}\n```"
                )
            except Exception as e:
                results.append(f"❌ Erreur: {e}")

        # Ajouter les résultats à la réponse
        return answer + "\n\n**Résultats:**\n" + "\n".join(results)

    def _update_history(self, session_id: str, user_msg: str, ai_msg: str):
        history = self._history.get(session_id, [])
        history.extend(
            [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": ai_msg},
            ]
        )
        self._history[session_id] = history[-10:]


# --- Refactoring: Client Matrix (Orchestrateur) ---


class ElektraMatrixBot:
    """Client Matrix propre (Refactoring: Single Responsibility)."""

    def __init__(self, agent: ElektraAgent):
        self.url = os.getenv("MATRIX_URL", "https://matrix.org")
        self.user = os.getenv("MATRIX_USER")
        self.password = os.getenv("MATRIX_PASS")
        self.agent = agent
        self.client = AsyncClient(self.url, self.user)

    async def start(self):
        """Initialise la connexion et lance la boucle (Refactoring: Extract Method)."""
        if not await self._login():
            return

        print(f"⚡ Elektra démarré et en attente...")
        await self._sync_loop()

    async def _login(self) -> bool:
        """Gère l'authentification (Refactoring: Extract Method)."""
        resp = await self.client.login(self.password)

        if isinstance(resp, LoginResponse):
            print(f"✅ Connecté: {resp.user_id}")
            return True

        logger.error(f"Échec de connexion : {resp}")
        return False

    async def _sync_loop(self):
        """Boucle de synchronisation (Refactoring: Extract Method)."""
        try:
            while True:
                sync_resp = await self.client.sync(timeout=30000, full_state=True)
                await self._process_sync_response(sync_resp)
                await asyncio.sleep(0.1)
        finally:
            await self.client.close()

    async def _process_sync_response(self, sync_resp):
        """Analyse les salons rejoints."""
        if not sync_resp or not sync_resp.rooms.join:
            return

        for room_id, room_info in sync_resp.rooms.join.items():
            for event in room_info.timeline.events:
                if isinstance(event, RoomMessageText):
                    await self._handle_message(self.client.rooms[room_id], event)

    async def _handle_message(self, room: MatrixRoom, event: RoomMessageText):
        """Traite un message reçu (Refactoring: Guard Clauses)."""
        # Guard: ne pas répondre à soi-même
        if event.sender == self.client.user_id:
            return

        # Guard: ne répondre que si mentionné
        if "elektra" not in event.body.lower():
            return

        print(f"📩 Requête de {event.sender}")
        prompt = re.sub(r"(?i)\belektra\b", "", event.body).strip() or "Salut !"
        response_text = await self.agent.chat(prompt, room.room_id)

        # Formatage et envoi (Refactoring: Delegate to Formatter)
        content = ResponseFormatter.format(response_text)
        await self.client.room_send(
            room_id=room.room_id, message_type="m.room.message", content=content
        )
        print(f"✅ Réponse envoyée")


async def main():
    # Injection de dépendance (Refactoring: Dependency Injection)
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if not mistral_key:
        print("MISTRAL_API_KEY manquante.")
        sys.exit(1)

    # Initialiser le client MCP (optionnel)
    mcp_client = None
    mcp_url = os.getenv("MCP_SERVER_URL")
    if mcp_url:
        from .mcp_client import McpClient
        mcp_client = McpClient(mcp_url)
        print(f"🔗 Connexion MCP: {mcp_url}...")
        # On tente la connexion. Si elle échoue, on continue sans MCP.
        if not await mcp_client.connect():
            mcp_client = None

    agent = ElektraAgent(
        mistral_key, os.getenv("MISTRAL_MODEL", "mistral-small-latest"), mcp_client
    )
    bot = ElektraMatrixBot(agent)

    try:
        await bot.start()
    except KeyboardInterrupt:
        print("⏹️ Arrêt du bot...")
    finally:
        if mcp_client:
            await mcp_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
