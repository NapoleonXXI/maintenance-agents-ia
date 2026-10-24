"""Outil généré automatiquement par l'agent Forgeron. Suivi de l'avancement des interventions par logement."""
import sqlite3
def run(db_path):
    c = sqlite3.connect(db_path); c.row_factory = sqlite3.Row
    rows = c.execute("""SELECT l.id, l.nom,
      SUM(i.statut='cloturee') clot, SUM(i.statut='suivi_ouvert') rel, SUM(i.statut IN ('nouvelle','assignee','a_suivre')) att, COUNT(i.id) tot,
      GROUP_CONCAT(CASE WHEN i.statut IN ('nouvelle','assignee','a_suivre') THEN '#'||i.id||' '||i.categorie||' ('||i.statut||')' END, '; ') ouvertes
      FROM logements l LEFT JOIN interventions i ON i.logement_id=l.id GROUP BY l.id ORDER BY l.id""").fetchall()
    out = []
    for r in rows:
        etat = "OK" if not r["att"] else "EN COURS"
        out.append(dict(logement=r["id"], nom=r["nom"], total=r["tot"], relayees=r["rel"] or 0, cloturees=r["clot"] or 0,
                        en_attente=r["att"] or 0, etat=etat, ouvertes=r["ouvertes"] or ""))
    return out
