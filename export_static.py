"""Export statique en lecture seule du sidecar vers docs/ (GitHub Pages)."""
import os, datetime, importlib.util
from zoneinfo import ZoneInfo
from core import conn, DB, TOOLS_DIR, BASE
from sidecar import table, e, CSS
OUT = os.path.join(BASE, "docs")
CODESPACE = "https://github.com/codespaces/new?repo=NapoleonXXI%2Fmaintenance-agents-ia&ref=main"
PAGES = [("index.html", "Suivi par logement"), ("interventions.html", "Interventions"), ("journal.html", "Journal"),
         ("messages.html", "Messages"), ("outils.html", "Outils créés"), ("routage.html", "Routage (auto-organisé)")]

def export():
    os.makedirs(OUT, exist_ok=True)
    maj = datetime.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M (heure de Paris)")
    nav = "<nav>" + " | ".join(f'<a href="{f}">{t}</a>' for f, t in PAGES) + "</nav>"
    note = (f"<p style='background:#f4f4f4;padding:8px'>Vue publique en lecture seule – dernière mise à jour : <b>{maj}</b>. "
            f"Les actions (ajouter, modifier, clôturer, lancer l'équipe) se font dans le sidecar du "
            f"<a href='{CODESPACE}'>Codespace</a>.</p>")
    c = conn(); body = {}
    spec = importlib.util.spec_from_file_location("t", os.path.join(TOOLS_DIR, "suivi_par_logement.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    body["index.html"] = "<p>Généré par l'outil <code>tools/suivi_par_logement.py</code> écrit par l'agent Forgeron.</p>" + table(m.run(DB))
    body["interventions.html"] = table(c.execute("SELECT * FROM interventions ORDER BY logement_id,id").fetchall())
    body["journal.html"] = table(c.execute("SELECT * FROM journal ORDER BY id DESC").fetchall())
    body["messages.html"] = table(c.execute("SELECT * FROM messages ORDER BY id DESC").fetchall())
    rows = c.execute("SELECT * FROM outils").fetchall()
    body["outils.html"] = table(rows) + "".join(f"<h3>{e(r['nom'])}</h3><pre>{e(open(r['chemin']).read())}</pre>" for r in rows)
    body["routage.html"] = table(c.execute("SELECT * FROM routage").fetchall())
    for f, t in PAGES:
        with open(os.path.join(OUT, f), "w") as fh:
            fh.write(f"<!doctype html><meta charset=utf-8><title>{t}</title>{CSS}<h1>{t}</h1>{nav}{note}{body[f]}")
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    return OUT
if __name__ == "__main__": print(export())
