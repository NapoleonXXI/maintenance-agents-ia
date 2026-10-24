# Équipe d'agents IA auto-construite – maintenance de 10 logements (prototype)

## Philosophie
Pas de logiciel figé à mettre à jour : le moteur reste fluide. Les agents écrivent, modifient et retirent leurs propres
outils (fichiers Python dans `tools/`), décident eux-mêmes du routage (table `routage`), et tout changement est tracé
dans un journal append-only, visible et modifiable depuis le sidecar humain.

## Deux cœurs
1. **App interne des agents** : `orchestrator.py` (boucle), `agents.py` (agents), `core.py` (SQLite, journal, registre d'outils), `tools/` (code écrit par les agents).
2. **Sidecar humain** : `sidecar.py` (serveur web stdlib, interface en français) → http://127.0.0.1:8810

## Équipe
- **Réception** : enregistre les demandes (et les suivis).
- **Trieur** : classe catégorie/priorité avec l'outil `classifier_categorie` ; s'il n'existe pas, il le fait écrire.
- **Répartiteur** : envoie le message au technicien ; crée lui-même les routes manquantes, se réorganise si une catégorie apparaît.
- **Technicien (simulé)** : renvoie un résultat pseudo-aléatoire (graine fixe), parfois « pièce à commander » ou « provisoire ».
- **Archiviste** : classe le résultat, enregistre, clôture ou ouvre un suivi (commande de pièce simulée).
- **Forgeron** : écrit/réécrit/versionne les outils, analyse les motifs récurrents et adapte l'outil de tri.

## Lancer
```bash
cd /workspace/maintenance-agents-ia
python3 orchestrator.py --reset      # test complet (efface la base)
setsid nohup python3 sidecar.py > sidecar.log 2>&1 &   # PORT=xxxx pour changer
```
Base non versionnée : `python3 orchestrator.py --reset` la reconstruit à partir du dépôt seul. `python3 orchestrator.py --pending` traite les demandes en attente.

Actions humaines du sidecar (journalisées `Humain:<nom>`) : ajouter une intervention, modifier/clôturer, retirer/réactiver un outil, bouton « Lancer l'équipe » sur les interventions en attente.

Pages : `/` suivi par logement, `/interventions` (+ modifier), `/journal`, `/messages`, `/outils` (code, retirer/réactiver), `/routage`.
Toute modification humaine est journalisée (`Humain:<nom>`). Le journal est protégé par des triggers SQLite (UPDATE/DELETE refusés).

## Limites honnêtes
- **Aucun LLM utilisé** : aucune clé d'API dans l'environnement. La « pensée » des agents est à base de règles et de gabarits de code ; l'auto-adaptation est un comptage de mots récurrents, donc rudimentaire (elle a aussi retenu des mots parasites comme « position », « basse »).
- L'enchaînement des étapes reste écrit dans `orchestrator.py` ; seuls les outils, le routage et les catégories évoluent à l'exécution.
- Techniciens, commandes de pièces et messages sont simulés (rien n'est envoyé hors de la machine).
