# Équipe d'agents IA auto-construite – maintenance de 10 logements (prototype)

## Philosophie
Pas de logiciel figé à mettre à jour : le moteur reste fluide. Les agents écrivent, modifient et retirent leurs propres
outils (fichiers Python dans `tools/`), décident eux-mêmes du routage (table `routage`), et tout changement est tracé
dans un journal append-only, visible et modifiable depuis l'app humaine **Pilote**.

## Deux cœurs
1. **App interne des agents** : `orchestrator.py` (boucle), `agents.py` (agents), `core.py` (SQLite, journal, registre d'outils), `tools/` (code écrit par les agents).
2. **Pilote** (app humaine, Ruby on Rails 8, dossier `pilote/`) → http://127.0.0.1:8810. Elle lit et écrit la même base SQLite que les agents (aucune migration Rails) et journalise chaque action humaine sous `Humain:<prénom>`.

## Règle du propriétaire (ordre de Raphaël)
- **Seul le propriétaire crée les interventions** (via Pilote). L'équipe ne crée jamais d'intervention fictive, de test ou de démonstration : aucun scénario n'est rejoué, `--reset` ne fait que préparer une base vide (10 logements + outils de base).
- **Mission principale de l'équipe : l'architecture de l'application** (moteur, outils, routage, Pilote, vue publique), pas la production de données.
- Le 24/10/2026, toutes les interventions factices ont été purgées sur ordre du propriétaire (trace `PURGE` dans le journal).

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
python3 orchestrator.py --reset      # base neuve vide (efface la base, aucune intervention créée)
cd pilote && bundle config set --local path vendor/bundle && bundle install   # une fois
bin/rails server -b 0.0.0.0 -p 8810                                       # Pilote
python3 export_static.py   # régénère docs/ : uniquement les 10 cases (aussi fait automatiquement)
```
Base non versionnée : `python3 orchestrator.py --reset` la reconstruit à partir du dépôt seul. `python3 orchestrator.py --pending` traite les demandes en attente.

Pilote (mobile d'abord, gros boutons, français) :
- accueil : uniquement 10 grandes cases carrées numérotées 1–10 (vert = OK, orange = ouvertes, rouge = urgence) ; tout le reste (nouvelle intervention, Lancer l'équipe, journal, classement, Avancé) est sur la page d'un logement ;
- page logement : « Clôturer », « Priorité urgente », « Modifier », « Supprimer » (suppression logique `supprimee`, confirmation en 2 appuis, état avant conservé au journal) ;
- création en 2 appuis (tuile 1–10 + une ligne de texte) ; prénom demandé une seule fois (cookie) ;
- journal complet filtrable par logement et par acteur ; classement (faites / en cours, logements, activité des agents, catégories) ;
- « Avancé » : code des outils (retirer/réactiver), routage, messages.
Vue publique en lecture seule : https://napoleonxxi.github.io/maintenance-agents-ia/ (générée par `export_static.py`).

Toute modification humaine est journalisée (`Humain:<nom>`). Le journal est protégé par des triggers SQLite (UPDATE/DELETE refusés).

## Limites honnêtes
- **Aucun LLM utilisé** : aucune clé d'API dans l'environnement. La « pensée » des agents est à base de règles et de gabarits de code ; l'auto-adaptation est un comptage de mots récurrents, donc rudimentaire (elle a aussi retenu des mots parasites comme « position », « basse »).
- L'enchaînement des étapes reste écrit dans `orchestrator.py` ; seuls les outils, le routage et les catégories évoluent à l'exécution.
- Techniciens, commandes de pièces et messages sont simulés (rien n'est envoyé hors de la machine).

## Prochaines étapes
- Fonction reportée par Raphaël (« on va créer ça après ») — à préciser.
