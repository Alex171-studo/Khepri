# Khepri : Assistant IA de Vente & Automatisation E-commerce

**Démo en ligne :** [https://khepri-store.vercel.app/](https://khepri-store.vercel.app/)

---

## 📌 Présentation du Projet

Khepri est un assistant de vente intelligent et agentique conçu pour automatiser à 100 % le parcours d'achat e-commerce, depuis la demande initiale du client jusqu'au paiement final et à la mise à jour des stocks.

Contrairement à un simple chatbot de FAQ, Khepri agit comme un véritable conseiller commercial virtuel capable de :

- Comprendre l'intention de l'utilisateur grâce à un LLM et un prompt engineering adapté.
- Rechercher des produits dans un catalogue de manière sémantique (RAG).
- Gérer un panier d'achat dynamique et le calcul des montants.
- Générer des liens de paiement sécurisés FedaPay.
- Conserver l'historique complet des échanges en base de données.

---

## 🛠️ Architecture Technique & Workflow

Le système repose sur un pipeline distribué associant orchestration de workflows, bases de données vectorielles et intégration d'APIs.

### 1. Traitement du langage & Persistance du contexte

- **LLM & Agentic Routing :** L'agent analyse l'intention du message (demande d'information, ajout au panier, validation de commande).
- **LangGraph + PostgreSQL (Checkpointing) :** La mémoire de conversation est sauvegardée sous forme de checkpoints dans Supabase via un identifiant unique.

### 2. Recherche Produits par RAG (Retrieval-Augmented Generation)

- **Base Vectorielle (Qdrant) :** Les produits du catalogue sont vectorisés. Une recherche par similarité vectorielle est effectuée pour recommander l'article le plus pertinent, même si l'utilisateur n'utilise pas les mots exacts.

### 3. Gestion des Stocks & Base Métier

- **Airtable API :** Base de données relationnelle assurant la synchronisation du catalogue actif et des quantités en stock en temps réel.

### 4. Tunnel de Paiement & Callback

- **FedaPay API :** Dès la validation de la commande, l'agent génère un lien de paiement unique.
- **Page de confirmation :** Une fois le paiement effectué, le client est redirigé vers une page dédiée de confirmation.

---

## 💡 Exemple de Parcours Client

1. **Recherche :** Le client écrit : _« Salut, je cherche un sac à main tendance »_.
2. **Recommandation (RAG) :** Khepri interroge Qdrant et répond : _« J'ai un sac à main femme tendance à 18 000 FCFA. Il en reste 20 en stock. »_
3. **Mise au panier :** Le client répond : _« J'en veux un »_.
4. **Récapitulatif :** Khepri calcule le total : _« C'est noté pour 1 sac à main femme tendance à 18 000 FCFA. Total provisoire : 18 000 FCFA. Souhaitez-vous valider la commande ? »_
5. **Paiement :** L'utilisateur valide, Khepri génère le lien FedaPay sécurisé pour finaliser l'achat.

---

## 🧰 Stack Technologique

| Composant                 | Technologie Utilisée                               | Rôle                                                            |
| :------------------------ | :------------------------------------------------- | :-------------------------------------------------------------- |
| **Orchestration / Agent** | Python, LangChain, LangGraph, n8n         | Logique agentique, routage d'actions et automatisation |
| **RAG & Vector Search**   | Qdrant, OpenAI Embeddings                 | Recherche sémantique dans le catalogue                 |
| **Gestion Stocks**        | Airtable API                              | Synchronisation du catalogue et du stock en temps réel |
| **Paiement**              | FedaPay API                               | Génération dynamique des liens de transaction          |
| **Base de données**       | PostgreSQL (Supabase)                              | Persistance de la mémoire conversationnelle (`thread_id`)       |
| **Déploiement Front**     | Vercel                      | Interface utilisateur web responsive                            |
| **Canaux d'entrée**       | Web Interface, WhatsApp API, Telegram API | Multi-canaux                                           |