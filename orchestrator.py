"""Orchestrateur : boucle demande (créée par le propriétaire) -> tri -> technicien -> classement -> base."""
import json, os, sys
from core import init, conn, log, DB, load_tool
from agents import *

LOGEMENTS = [(1,"Chambre Hôtel 101","hotel"),(2,"Chambre Hôtel 102","hotel"),(3,"Chambre Hôtel 103","hotel"),
 (4,"Mobil-home Camping A1","camping"),(5,"Mobil-home Camping A2","camping"),(6,"Chalet Camping B1","camping"),
 (7,"Studio Résidence R1","residence"),(8,"Studio Résidence R2","residence"),(9,"Studio Résidence R3","residence"),(10,"Studio Résidence R4","residence")]
# Aucune intervention fictive : seules les demandes saisies par le propriétaire (Pilote) sont traitées.

def main():
    """Prépare la base (schéma, 10 logements, outils de base). Ne crée AUCUNE intervention."""
    if os.path.exists(DB) and "--reset" in sys.argv: os.remove(DB)
    init()
    with conn() as c: c.executemany("INSERT OR IGNORE INTO logements VALUES(?,?,?)", LOGEMENTS)
    smith = Toolsmith(); Triage(smith)   # le Trieur fait écrire son outil s'il manque
    if not load_tool("suivi_par_logement", "Orchestrateur"):
        smith.build("suivi_par_logement", raison="Besoin d'un tableau de bord d'avancement par logement")
    log("Orchestrateur", "INITIALISE", "systeme", {"logements": len(LOGEMENTS), "interventions_creees": 0})
    _export()

def _export(publication=False, acteur="Orchestrateur"):
    try:
        import export_static; export_static.export(); log("Orchestrateur", "EXPORTE_PAGES", "docs/")
    except Exception as x: log("Orchestrateur", "ECHEC_EXPORT", "docs/", {"erreur": str(x)}); return
    if publication:   # publication auto GitHub Pages (AUTO_PUBLISH=0 pour désactiver)
        import publier; publier.publier(acteur, "Publication auto après cycle de l'équipe")

def run_pending(declencheur="Orchestrateur"):
    """Traite les interventions en statut 'nouvelle' (ex. ajoutées à la main). Un seul tour ; les suivis restent en attente."""
    init()
    with conn() as c: ids = [r[0] for r in c.execute("SELECT id FROM interventions WHERE statut='nouvelle' ORDER BY id")]
    log("Orchestrateur", "DEMARRE_CYCLE", "systeme", {"mode": "en_attente", "declencheur": declencheur, "interventions": ids})
    smith = Toolsmith(); rec = Reception(); tri = Triage(smith); disp = Dispatcher(); arch = Archiviste()
    import random; tech = TechnicienSimule(seed=random.randrange(10**6))
    suivis = []
    for iid in ids:
        with conn() as c: deja = c.execute("SELECT categorie FROM interventions WHERE id=?", (iid,)).fetchone()[0]
        if not deja: tri.triage(iid)   # ne pas écraser un tri existant (ex. priorité corrigée par l'humain)
        f = arch.record(iid, tech.work(iid, disp.dispatch(iid)), rec)
        if f: tri.triage(f); suivis.append(f)
    with conn() as c: divers = c.execute("SELECT id, description FROM interventions WHERE categorie='divers' AND statut!='supprimee'").fetchall()
    if len(divers) >= 2 and smith.adapt([d for _, d in divers], tri.tool):   # auto-adaptation sur les vraies demandes
        tri.reload(); [tri.triage(i) for i, _ in divers]
    if not load_tool("suivi_par_logement", "Orchestrateur"):
        smith.build("suivi_par_logement", raison="Besoin d'un tableau de bord d'avancement par logement")
    log("Orchestrateur", "FIN_CYCLE", "systeme", {"traitees": len(ids), "suivis_ouverts": suivis})
    _export(publication=True, acteur=declencheur); return len(ids), suivis

if __name__ == "__main__":
    if "--pending" in sys.argv: print(run_pending())
    else: main()   # --reset : base neuve, sans intervention
