# Protocole de l'équipe Grok Bot – maintenance-agents-ia

Les cinq agents Grok Bot (Réception, Trieur, Répartiteur, Archiviste, Forgeron) partagent cet ordinateur.
Dossier : /workspace/maintenance-agents-ia — dépôt : github.com/NapoleonXXI/maintenance-agents-ia (gh authentifié).

## Accès
- Lire / exécuter : `python3 orchestrator.py` (test complet, `--reset` efface la base), `python3 tools/<outil>.py`.
- Base : `maintenance.db` (SQLite). Journal en ajout seul : toute action y est inscrite avec le nom de l'agent.
- Sidecar humain : `python3 sidecar.py` (port 8810).

## Qui écrit quoi
- Forgeron : seul à créer/modifier/retirer le code dans `tools/` et le cœur ; versionne, journalise, puis `git add -A && git commit -m "Forgeron: ..." && git push`.
- Réception, Trieur, Répartiteur, Archiviste : utilisent les outils existants ; s'il manque un outil ou qu'il est faux, ils le demandent au Forgeron.

## Transmission entre agents
1. Message direct Grok Bot (SendToAgent) au coéquipier suivant : Réception -> Trieur -> Répartiteur -> technicien -> Archiviste ; tout agent -> Forgeron pour un besoin d'outil.
2. Chaque transmission est aussi inscrite dans le journal de `maintenance.db`.
3. Avant d'agir : `git pull`. Un seul agent modifie le code à la fois (le Forgeron).

## Garde-fous
Rien ne sort de la machine (techniciens simulés) et rien n'est supprimé (dépôt, base) sans accord explicite de Raphaël.
