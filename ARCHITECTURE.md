# Architecture (prototype)

```
 demande ─▶ Réception ─▶ Trieur ─▶ Répartiteur ─▶ Technicien (simulé)
                          │outil         │table routage        │
                          ▼              ▼                     ▼
                  tools/*.py (écrits  messages            Archiviste ─▶ clôture ou suivi
                  par le Forgeron)                                     (nouvelle intervention liée)
                 tout ─▶ journal (append-only, SQLite)  ◀── sidecar humain (lecture + actions)
```

## Deux cœurs
- **Cœur agents** : `core.py` (base, journal, registre d'outils versionné, retrait), `agents.py` (Réception, Trieur,
  Répartiteur, Archiviste, Forgeron + technicien simulé), `orchestrator.py` (test complet ou traitement des demandes en attente).
- **Cœur humain** : `sidecar.py`, serveur web stdlib en français, port 8810.

## Base SQLite (`maintenance.db`, non versionnée, reconstruite par le dépôt)
`logements`, `interventions` (statuts : nouvelle, assignee, a_suivre, suivi_ouvert, cloturee ; `parent_id` relie un suivi),
`messages`, `outils` (version, actif), `routage` (catégorie → technicien, décidé par les agents),
`journal` (triggers SQLite refusant UPDATE/DELETE).

## Auto-construction
Le Forgeron écrit un fichier dans `tools/`, le compile, l'enregistre (sha256, version) ; les agents le chargent via
le registre. Réécriture = nouvelle version journalisée ; un outil retiré (`actif=0`) n'est plus chargé.
Les fichiers de `tools/` présents dans le dépôt sont ceux générés par le dernier test : ils sont réécrits à chaque `--reset`.

## Commandes
- `python3 orchestrator.py --reset` : reconstruit la base depuis zéro et rejoue le test (2 vagues + adaptation).
- `python3 orchestrator.py --pending` : l'équipe traite les interventions en statut `nouvelle`.
- `python3 sidecar.py` : app humaine.
