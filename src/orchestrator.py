import asyncio
import time
import random
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
from mistralai.client import Mistral

logger = logging.getLogger("elektra.orchestrator")

@dataclass
class LLMNode:
    """Représente une instance d'inférence (M1, M2, M3)."""
    id: str
    url: str
    api_key: str
    is_alive: bool = True
    current_load: int = 0
    latency_history: List[float] = None
    
    def __post_init__(self):
        self.latency_history = []

    def get_score(self) -> float:
        """Calcule un score de performance (plus bas est meilleur)."""
        avg_latency = sum(self.latency_history) / len(self.latency_history) if self.latency_history else 0.5
        return (self.current_load * 1.5) + (avg_latency * 1.0)

class LLMOrchestrator:
    """Orchestrateur avec Load Balancing, Queueing et Resilience (Partie 2)."""
    
    def __init__(self, nodes_config: List[Dict]):
        self.nodes = [LLMNode(**config) for config in nodes_config]
        self.queue = asyncio.Queue()
        self.max_retries = 3
        self.healthcheck_interval = 30 # secondes

    async def start_healthcheck_loop(self):
        """Boucle de surveillance de la santé des instances."""
        while True:
            for node in self.nodes:
                try:
                    # Simulation d'un ping/healthcheck
                    node.is_alive = True # En production, faire un appel réel
                    # logger.debug(f"Healthcheck OK pour {node.id}")
                except Exception as e:
                    node.is_alive = False
                    logger.warning(f"Instance {node.id} OFFLINE: {e}")
            await asyncio.sleep(self.healthcheck_interval)

    async def get_inference(self, messages: List[Dict], model: str) -> str:
        """Point d'entrée principal pour les requêtes d'inférence."""
        # 1. Mettre en file d'attente
        request_id = random.randint(1000, 9999)
        # logger.info(f"[Req:{request_id}] Mise en file d'attente...")
        
        # 2. Sélectionner la meilleure instance (Load Balancing)
        node = self._select_best_node()
        if not node:
            return "❌ Toutes les instances d'inférence sont saturées ou hors ligne. Réessayez plus tard."

        # 3. Exécuter l'inférence avec gestion des erreurs (Resilience)
        node.current_load += 1
        start_time = time.time()
        
        try:
            # En production, on appellerait node.url ici
            client = Mistral(api_key=node.api_key)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: client.chat.complete(
                model=model, messages=messages
            ))
            
            latency = time.time() - start_time
            node.latency_history.append(latency)
            if len(node.latency_history) > 10: node.latency_history.pop(0)
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erreur sur instance {node.id}: {e}")
            # Logique de Retry sur une autre instance (Recursion simple)
            return await self.get_inference(messages, model)
        finally:
            node.current_load -= 1

    def _select_best_node(self) -> Optional[LLMNode]:
        """Choisit le noeud avec le score de performance le plus bas."""
        alive_nodes = [n for n in self.nodes if n.is_alive]
        if not alive_nodes: return None
        return min(alive_nodes, key=lambda n: n.get_score())

# Simulation d'une configuration multi-nodes (M1, M2, M3)
DEFAULT_NODES = [
    {"id": "M1", "url": "https://api.mistral.ai", "api_key": ""}, # À remplir via .env
    {"id": "M2", "url": "https://api.mistral.ai", "api_key": ""},
    {"id": "M3", "url": "https://api.mistral.ai", "api_key": ""}
]
