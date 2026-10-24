"""Agents (logique déterministe à base de règles : aucune clé d'API LLM disponible)."""
import random, json
from core import conn, log, now, register_tool, load_tool

class Agent:
    nom = "agent"
    def log(self, action, objet, details=None): log(self.nom, action, objet, details)

class Toolsmith(Agent):
    """Écrit le code des outils dont l'équipe a besoin et les enregistre dans le registre."""
    nom = "Forgeron"
    TEMPLATES = {
     "classifier_categorie": ('Classe une demande par mots-clés (catégorie + priorité).', '''
KEYWORDS = {KW}
URGENT = {URG}
def run(description):
    d = description.lower()
    cat = next((c for c, mots in KEYWORDS.items() if any(m in d for m in mots)), "divers")
    prio = "urgente" if any(u in d for u in URGENT) else ("haute" if cat in ("electricite", "chauffage") else "normale")
    return cat, prio
'''),
     "suivi_par_logement": ("Suivi de l'avancement des interventions par logement.", '''
import sqlite3
def run(db_path):
    c = sqlite3.connect(db_path); c.row_factory = sqlite3.Row
    rows = c.execute(\"\"\"SELECT l.id, l.nom,
      SUM(i.statut='cloturee') clot, SUM(i.statut='suivi_ouvert') rel, SUM(i.statut IN ('nouvelle','assignee','a_suivre')) att, COUNT(i.id) tot,
      GROUP_CONCAT(CASE WHEN i.statut IN ('nouvelle','assignee','a_suivre') THEN '#'||i.id||' '||i.categorie||' ('||i.statut||')' END, '; ') ouvertes
      FROM logements l LEFT JOIN interventions i ON i.logement_id=l.id GROUP BY l.id ORDER BY l.id\"\"\").fetchall()
    out = []
    for r in rows:
        etat = "OK" if not r["att"] else "EN COURS"
        out.append(dict(logement=r["id"], nom=r["nom"], total=r["tot"], relayees=r["rel"] or 0, cloturees=r["clot"] or 0,
                        en_attente=r["att"] or 0, etat=etat, ouvertes=r["ouvertes"] or ""))
    return out
'''),
    }
    def adapt(self, interventions_divers, classifier):
        """Auto-adaptation : cherche un motif récurrent dans les demandes non classées et réécrit l'outil de tri."""
        import re, collections
        mots = collections.Counter()
        for d in interventions_divers:
            d = re.sub(r"^(Suivi #\d+ \([^)]*\) : )+", "", d)  # ne garder que la panne d'origine
            for m in set(re.findall(r"[a-zàâéèêîôûç]{4,}", d.lower())) - {"suivi", "reparation_provisoire", "piece_a_commander", "cassé", "bloqué", "bloque", "plus", "pour", "dans"}:
                mots[m] += 1
        recurrents = [m for m, n in mots.items() if n >= 2]
        self.log("ANALYSE_MOTIFS", "outil:classifier_categorie", {"demandes_non_classees": len(interventions_divers), "mots_recurrents": recurrents})
        if not recurrents: return None
        kw = dict(classifier.KEYWORDS); kw["menuiserie_ouvrants"] = sorted(set(recurrents) | {"volet", "store", "fenêtre"})
        self.build("classifier_categorie", raison=f"Motif récurrent non couvert : {recurrents}", kw=kw, urg=classifier.URGENT)
        return "menuiserie_ouvrants"

    def build(self, nom, **params):
        desc, code = self.TEMPLATES[nom]
        code = code.replace("{KW}", repr(params.get("kw"))).replace("{URG}", repr(params.get("urg")))
        code = f'"""Outil généré automatiquement par l\'agent {self.nom}. {desc}"""' + code
        self.log("DECIDE_CREER_OUTIL", f"outil:{nom}", {"raison": params.get("raison")})
        return register_tool(nom, code, self.nom, desc)

class Reception(Agent):
    nom = "Réception"
    def intake(self, logement_id, description, parent_id=None):
        with conn() as c:
            cur = c.execute("INSERT INTO interventions(logement_id,description,statut,parent_id,cree_le,maj_le) VALUES(?,?,?,?,?,?)",
                            (logement_id, description, "nouvelle", parent_id, now(), now()))
            iid = cur.lastrowid
        self.log("CREE_INTERVENTION", f"intervention:{iid}", {"logement": logement_id, "description": description, "parent": parent_id})
        return iid

class Triage(Agent):
    nom = "Trieur"
    def __init__(self, smith):
        self.tool = load_tool("classifier_categorie", self.nom)
        if not self.tool:  # l'équipe s'auto-équipe si l'outil manque
            smith.build("classifier_categorie", raison="Trieur sans outil de classification",
              kw={"plomberie": ["fuite", "robinet", "wc", "évier", "douche", "eau"],
                  "electricite": ["prise", "disjonct", "lumière", "ampoule", "court-circuit"],
                  "chauffage": ["chauffage", "radiateur", "chaudière", "clim"],
                  "electromenager": ["frigo", "réfrigérateur", "four", "lave", "micro-ondes", "plaque"],
                  "serrurerie": ["serrure", "porte", "clé", "badge"]},
              urg=["inond", "court-circuit", "odeur de gaz", "plus d'eau", "fumée"])
            self.tool = load_tool("classifier_categorie", self.nom)
    def reload(self): self.tool = load_tool("classifier_categorie", self.nom)
    def triage(self, iid):
        with conn() as c:
            d = c.execute("SELECT description FROM interventions WHERE id=?", (iid,)).fetchone()[0]
            cat, prio = self.tool.run(d)
            c.execute("UPDATE interventions SET categorie=?,priorite=?,maj_le=? WHERE id=?", (cat, prio, now(), iid))
        self.log("TRIE_INTERVENTION", f"intervention:{iid}", {"categorie": cat, "priorite": prio})

class Dispatcher(Agent):
    nom = "Répartiteur"
    CONNU = {"plomberie": "Tech-Plombier", "electricite": "Tech-Électricien", "chauffage": "Tech-Chauffagiste",
             "electromenager": "Tech-Électroménager", "serrurerie": "Tech-Polyvalent", "divers": "Tech-Polyvalent"}
    def dispatch(self, iid):
        with conn() as c:
            i = c.execute("SELECT * FROM interventions WHERE id=?", (iid,)).fetchone()
            newroute = None
            r = c.execute("SELECT technicien FROM routage WHERE categorie=?", (i["categorie"],)).fetchone()
            if r: tech = r[0]
            else:  # le Répartiteur s'organise lui-même : nouvelle route décidée à l'exécution
                tech = self.CONNU.get(i["categorie"], "Tech-Polyvalent")
                c.execute("INSERT INTO routage VALUES(?,?,?,?)", (i["categorie"], tech, self.nom, now()))
                newroute = i["categorie"]
            msg = f"[{i['priorite'].upper()}] Logement {i['logement_id']} – {i['categorie']} : {i['description']}"
            c.execute("INSERT INTO messages(intervention_id,de,vers,contenu,envoye_le) VALUES(?,?,?,?,?)", (iid, self.nom, tech, msg, now()))
            c.execute("UPDATE interventions SET statut='assignee',maj_le=? WHERE id=?", (now(), iid))
        if newroute: self.log("CREE_ROUTE", f"routage:{newroute}", {"technicien": tech})
        self.log("ENVOIE_MESSAGE", f"intervention:{iid}", {"vers": tech, "contenu": msg})
        return tech

class TechnicienSimule(Agent):
    """Technicien SIMULÉ (pas un agent de l'équipe) : renvoie un résultat pseudo-aléatoire graine fixe."""
    nom = "Technicien(simulé)"
    def __init__(self, seed=42): self.rng = random.Random(seed)
    def work(self, iid, tech, force_followup=False):
        r = self.rng.random()
        if force_followup or r < 0.15: res = "Diagnostic fait, pièce à commander, repasser."
        elif r < 0.22: res = "Réparation provisoire, contrôle nécessaire sous 48h."
        else: res = "Réparé et testé, fonctionne."
        with conn() as c:
            c.execute("INSERT INTO messages(intervention_id,de,vers,contenu,envoye_le) VALUES(?,?,?,?,?)", (iid, tech, "Répartiteur", res, now()))
        log(tech + " (simulé)", "RETOUR_TECHNICIEN", f"intervention:{iid}", {"resultat": res})
        return res

class Archiviste(Agent):
    nom = "Archiviste"
    def record(self, iid, res, reception):
        if "commander" in res: cls, statut = "piece_a_commander", "a_suivre"
        elif "provisoire" in res: cls, statut = "reparation_provisoire", "a_suivre"
        else: cls, statut = "resolu", "cloturee"
        with conn() as c:
            c.execute("UPDATE interventions SET resultat=?,classification=?,statut=?,maj_le=? WHERE id=?", (res, cls, statut, now(), iid))
            i = c.execute("SELECT * FROM interventions WHERE id=?", (iid,)).fetchone()
        self.log("CLASSE_ET_ENREGISTRE", f"intervention:{iid}", {"classification": cls, "statut": statut})
        if statut == "a_suivre":
            if cls == "piece_a_commander": self.log("COMMANDE_PIECE", f"intervention:{iid}", {"note": "commande simulée"})
            fid = reception.intake(i["logement_id"], f"Suivi #{iid} ({cls}) : {i['description']}", parent_id=iid)
            with conn() as c: c.execute("UPDATE interventions SET statut='suivi_ouvert',maj_le=? WHERE id=?", (now(), iid))
            self.log("MODIFIE_STATUT", f"intervention:{iid}", {"statut": "suivi_ouvert", "suivi": fid})
            return fid
