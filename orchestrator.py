"""Orchestrateur : boucle demande -> tri -> technicien -> classement -> base."""
import json, os, sys
from core import init, conn, log, DB, load_tool
from agents import *

LOGEMENTS = [(1,"Chambre Hôtel 101","hotel"),(2,"Chambre Hôtel 102","hotel"),(3,"Chambre Hôtel 103","hotel"),
 (4,"Mobil-home Camping A1","camping"),(5,"Mobil-home Camping A2","camping"),(6,"Chalet Camping B1","camping"),
 (7,"Studio Résidence R1","residence"),(8,"Studio Résidence R2","residence"),(9,"Studio Résidence R3","residence"),(10,"Studio Résidence R4","residence")]
DEMANDES = [(1,"Fuite sous l'évier de la salle de bain"),(1,"Ampoule grillée au plafond"),
 (2,"Radiateur froid malgré thermostat"),(3,"Prise électrique qui fait des étincelles, court-circuit"),
 (4,"Réfrigérateur ne refroidit plus"),(4,"WC qui coule en continu"),(5,"Chauffage d'appoint en panne"),
 (6,"Serrure de la porte d'entrée bloquée"),(6,"Plus d'eau chaude à la douche"),(7,"Four ne chauffe pas"),
 (7,"Disjoncteur qui saute le soir"),(8,"Lave-linge fuit, début d'inondation"),(9,"Clim bruyante"),
 (9,"Store cassé"),(10,"Robinet de cuisine qui goutte"),(10,"Plaque de cuisson ne s'allume plus"),
 (2,"Micro-ondes en panne"),(5,"Lumière extérieure ne s'allume plus")]
# 2e vague : un type de panne NOUVEAU et récurrent (volets roulants), inconnu de l'outil de tri initial
VAGUE2 = [(3,"Volet roulant bloqué en position basse"),(5,"Volet roulant ne remonte plus"),(8,"Volet roulant grince et se coince"),(1,"Fuite au robinet du lavabo")]

def main():
    if os.path.exists(DB) and "--reset" in sys.argv: os.remove(DB)
    init()
    with conn() as c: c.executemany("INSERT OR IGNORE INTO logements VALUES(?,?,?)", LOGEMENTS)
    log("Orchestrateur", "DEMARRE_CYCLE", "systeme", {"demandes": len(DEMANDES)})
    smith = Toolsmith(); rec = Reception(); tri = Triage(smith); disp = Dispatcher()
    tech = TechnicienSimule(); arch = Archiviste()
    def cycle(demandes, forced=()):
        queue = [rec.intake(l, d) for l, d in demandes]; rounds = 0
        while queue and rounds < 2:   # demandes + 1 tour de suivi ; le reste reste en attente
            rounds += 1; nxt = []
            for iid in queue:
                tri.triage(iid); t = disp.dispatch(iid)
                follow = arch.record(iid, tech.work(iid, t, force_followup=(rounds == 1 and iid in forced)), rec)
                if follow: nxt.append(follow)
            queue = nxt
        for iid in queue: tri.triage(iid)   # suivis du dernier tour : triés, pas encore envoyés
    cycle(DEMANDES, forced=(3, 9, 12))
    # VAGUE 2 : demandes inconnues. Après la vague, l'équipe s'auto-examine.
    log("Orchestrateur", "DEMARRE_CYCLE", "systeme", {"demandes": len(VAGUE2), "vague": 2})
    cycle(VAGUE2)
    with conn() as c:
        divers = c.execute("SELECT id, description FROM interventions WHERE categorie='divers'").fetchall()
    newcat = smith.adapt([d for _, d in divers], tri.tool)
    if newcat:
        tri.reload()
        for iid, _ in divers:
            tri.triage(iid)   # reclassement rétroactif avec l'outil réécrit
        with conn() as c:
            c.execute("UPDATE routage SET technicien='Tech-Menuisier', cree_par='Répartiteur', cree_le=datetime('now','localtime') WHERE categorie=?", (newcat,))
            if not c.execute("SELECT 1 FROM routage WHERE categorie=?", (newcat,)).fetchone():
                c.execute("INSERT INTO routage VALUES(?,?,?,datetime('now','localtime'))", (newcat, "Tech-Menuisier", "Répartiteur"))
        log("Répartiteur", "REORGANISE", f"routage:{newcat}", {"technicien": "Tech-Menuisier", "raison": "nouvelle catégorie créée par le Forgeron"})
    # l'équipe crée son outil de suivi par logement puis l'exécute
    if not load_tool("suivi_par_logement", "Orchestrateur"):
        smith.build("suivi_par_logement", raison="Besoin d'un tableau de bord d'avancement par logement")
    res = load_tool("suivi_par_logement", "Orchestrateur").run(DB)
    log("Orchestrateur", "EXECUTE_OUTIL", "outil:suivi_par_logement", res)
    _export()
    for r in res: print(f"{r['logement']:>2} {r['nom']:<24} total={r['total']} relayees={r['relayees']} clot={r['cloturees']} att={r['en_attente']} {r['etat']:<8} {r['ouvertes']}")

def _export():
    try:
        import export_static; export_static.export(); log("Orchestrateur", "EXPORTE_PAGES", "docs/")
    except Exception as x: log("Orchestrateur", "ECHEC_EXPORT", "docs/", {"erreur": str(x)})

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
    if not load_tool("suivi_par_logement", "Orchestrateur"):
        smith.build("suivi_par_logement", raison="Besoin d'un tableau de bord d'avancement par logement")
    log("Orchestrateur", "FIN_CYCLE", "systeme", {"traitees": len(ids), "suivis_ouverts": suivis})
    _export(); return len(ids), suivis

if __name__ == "__main__":
    if "--pending" in sys.argv: print(run_pending())
    else: main()
