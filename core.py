"""Noyau : base SQLite + journal append-only + registre d'outils."""
import sqlite3, json, datetime, importlib.util, os, hashlib
BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "maintenance.db")
TOOLS_DIR = os.path.join(BASE, "tools")

def now(): return datetime.datetime.now().isoformat(timespec="seconds")

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

SCHEMA = """
CREATE TABLE IF NOT EXISTS logements(id INTEGER PRIMARY KEY, nom TEXT, type TEXT);
CREATE TABLE IF NOT EXISTS interventions(id INTEGER PRIMARY KEY AUTOINCREMENT, logement_id INT,
  description TEXT, categorie TEXT, priorite TEXT, statut TEXT, parent_id INT,
  resultat TEXT, classification TEXT, cree_le TEXT, maj_le TEXT);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT, intervention_id INT,
  de TEXT, vers TEXT, contenu TEXT, envoye_le TEXT);
CREATE TABLE IF NOT EXISTS outils(nom TEXT PRIMARY KEY, chemin TEXT, auteur TEXT, description TEXT,
  sha256 TEXT, cree_le TEXT, version INT DEFAULT 1, actif INT DEFAULT 1);
CREATE TABLE IF NOT EXISTS routage(categorie TEXT PRIMARY KEY, technicien TEXT, cree_par TEXT, cree_le TEXT);
CREATE TABLE IF NOT EXISTS journal(id INTEGER PRIMARY KEY AUTOINCREMENT, horodatage TEXT, acteur TEXT,
  action TEXT, objet TEXT, details TEXT);
CREATE TRIGGER IF NOT EXISTS journal_no_update BEFORE UPDATE ON journal BEGIN SELECT RAISE(ABORT,'journal append-only'); END;
CREATE TRIGGER IF NOT EXISTS journal_no_delete BEFORE DELETE ON journal BEGIN SELECT RAISE(ABORT,'journal append-only'); END;
"""
def init():
    with conn() as c: c.executescript(SCHEMA)

def log(acteur, action, objet, details=None):
    with conn() as c:
        c.execute("INSERT INTO journal(horodatage,acteur,action,objet,details) VALUES(?,?,?,?,?)",
                  (now(), acteur, action, objet, json.dumps(details, ensure_ascii=False) if details is not None else None))

def register_tool(nom, code, auteur, description):
    """Mécanisme d'auto-construction : un agent écrit un fichier Python, il est enregistré."""
    path = os.path.join(TOOLS_DIR, nom + ".py")
    compile(code, path, "exec")  # validation syntaxique avant écriture
    with open(path, "w") as f: f.write(code)
    sha = hashlib.sha256(code.encode()).hexdigest()
    with conn() as c:
        old = c.execute("SELECT version, sha256 FROM outils WHERE nom=?", (nom,)).fetchone()
        v = (old["version"] + 1) if old else 1
        c.execute("INSERT OR REPLACE INTO outils VALUES(?,?,?,?,?,?,?,1)", (nom, path, auteur, description, sha, now(), v))
    log(auteur, "MODIFIE_OUTIL" if old else "ECRIT_OUTIL", f"outil:{nom}",
        {"chemin": path, "version": v, "sha256": sha, "sha256_avant": old["sha256"] if old else None, "lignes": code.count("\n")})
    return path

def load_tool(nom, acteur):
    with conn() as c: r = c.execute("SELECT chemin FROM outils WHERE nom=? AND actif=1", (nom,)).fetchone()
    if not r: return None
    spec = importlib.util.spec_from_file_location(nom, r["chemin"]); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); log(acteur, "CHARGE_OUTIL", f"outil:{nom}"); return m

def retire_tool(nom, acteur, raison):
    with conn() as c: c.execute("UPDATE outils SET actif=0 WHERE nom=?", (nom,))
    log(acteur, "RETIRE_OUTIL", f"outil:{nom}", {"raison": raison})
