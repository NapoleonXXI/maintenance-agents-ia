# Protocole de l'équipe Grok Bot – maintenance-agents-ia

Les cinq agents Grok Bot (Réception, Trieur, Répartiteur, Archiviste, Forgeron) partagent cet ordinateur.
Dossier : /workspace/maintenance-agents-ia — dépôt : github.com/NapoleonXXI/maintenance-agents-ia (gh authentifié).

## Règle du propriétaire (ordre de Raphaël)
- **Seul le propriétaire crée les interventions** (via Pilote). L'équipe ne crée jamais d'intervention fictive, de test ou de démonstration : aucun scénario n'est rejoué, `--reset` ne fait que préparer une base vide (10 logements + outils de base).
- **Mission principale de l'équipe : l'architecture de l'application** (moteur, outils, routage, Pilote, vue publique), pas la production de données.
- Le 24/10/2026, toutes les interventions factices ont été purgées sur ordre du propriétaire (trace `PURGE` dans le journal).

## Accès
- Lire / exécuter : `python3 orchestrator.py --pending` (traite les demandes du propriétaire), `--reset` (base neuve vide — ne jamais lancer sur la base réelle : efface le journal), `python3 tools/<outil>.py`.
- Base : `maintenance.db` (SQLite). Journal en ajout seul : toute action y est inscrite avec le nom de l'agent.
- App humaine « Pilote » (Ruby on Rails, dossier `pilote/`) : `cd pilote && bin/rails server -b 0.0.0.0 -p 8810`. Elle lit/écrit la même base `maintenance.db`.

## Qui écrit quoi
- Forgeron : seul à créer/modifier/retirer le code dans `tools/` et le cœur ; versionne, journalise, puis `git add -A && git commit -m "Forgeron: ..." && git push`.
- Réception, Trieur, Répartiteur, Archiviste : utilisent les outils existants ; s'il manque un outil ou qu'il est faux, ils le demandent au Forgeron.

## Transmission entre agents
1. Message direct Grok Bot (SendToAgent) au coéquipier suivant : Réception -> Trieur -> Répartiteur -> technicien -> Archiviste ; tout agent -> Forgeron pour un besoin d'outil.
2. Chaque transmission est aussi inscrite dans le journal de `maintenance.db`.
3. Avant d'agir : `git pull`. Un seul agent modifie le code à la fois (le Forgeron).

## Garde-fous
Rien ne sort de la machine (techniciens simulés) et rien n'est supprimé (dépôt, base) sans accord explicite de Raphaël.
