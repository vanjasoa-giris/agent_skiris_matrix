# 🤖 Elektra Agent Matrix

Elektra Agent Matrix est un bot conversationnel pour la plateforme **Matrix**, spécialisé dans l'assistance DevOps. Il utilise l'IA de **Mistral** pour générer des réponses et se connecte à un serveur **MCP** (Model Context Protocol) pour exécuter des commandes techniques en temps réel.

## 🌟 Fonctionnalités

- **Intégration Matrix** : Communique directement dans vos salons Matrix (répond aux mentions "elektra").
- **Intelligence Artificielle** : Propulsé par Mistral AI (modèle `mistral-small-latest` par défaut).
- **Client MCP intégré** : Capacité d'exécuter des commandes système, npm, ou scripts Python via un serveur MCP distant.
- **Formatage Riche** : Support complet du Markdown (code blocks, gras, listes) converti en HTML pour Matrix.
- **Orchestration & Résilience** : Gestion de sessions et mécanisme de retry automatique pour l'IA.

## 🏗️ Architecture

```text
[Utilisateur Matrix] <---> [Elektra Agent Matrix] <---> [Mistral AI API]
                                    |
                                    +---> [Serveur MCP (elektra-mcp-server)]
```

## 📋 Configuration (.env)

Créez un fichier `.env` à la racine avec les variables suivantes :

```env
# Connexion Matrix
MATRIX_URL=https://matrix.org
MATRIX_USER=@votre_bot:matrix.org
MATRIX_PASS=votre_mot_de_passe

# Mistral AI
MISTRAL_API_KEY=votre_cle_api
MISTRAL_MODEL=mistral-small-latest

# Connexion au Serveur MCP (Requis pour les outils DevOps)
MCP_SERVER_URL=http://localhost:8000/mcp

# Configuration Agent
AGENT_SYSTEM_PROMPT="Tu es Elektra, une assistante DevOps experte."
LOG_LEVEL=WARNING
```

## 🚀 Installation & Lancement

### Via Docker (Recommandé)
```bash
docker build -t elektra-matrix-bot .
docker run --env-file .env elektra-matrix-bot
```

### Installation Locale (Développement)
1. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
2. Lancez le bot :
   ```bash
   python -m src.main
   ```

## 📁 Structure du Projet

- `src/main.py` : Point d'entrée et orchestrateur du bot Matrix.
- `src/agent.py` : Logique de l'IA (Mistral) et gestion de l'historique.
- `src/mcp_client.py` : Client pour la communication avec le serveur MCP via SSE/HTTP.
- `src/formatter.py` : Conversion du Markdown en HTML compatible Matrix.
- `src/orchestrator.py` : Gestion avancée des nœuds LLM (Load Balancing/Resilience).

## 🛡️ Sécurité
- Le bot s'exécute en tant qu'utilisateur non-root dans Docker.
- Les secrets ne doivent jamais être committés (utilisez le fichier `.env`).
