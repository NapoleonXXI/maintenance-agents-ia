"""Export statique en lecture seule de Pilote vers docs/ (GitHub Pages). Même look (pilote/public/pilote.css)."""
import os, glob, shutil, datetime, html, sqlite3
from zoneinfo import ZoneInfo
BASE = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(BASE, "maintenance.db"); OUT = os.path.join(BASE, "docs")
CODESPACE = "https://github.com/codespaces/new?repo=NapoleonXXI%2Fmaintenance-agents-ia&ref=main"
OUV = "('nouvelle','assignee','a_suivre')"
e = lambda v: html.escape("" if v is None else str(v))

def page(titre, body, maj):
    return (f"<!doctype html><html lang=fr><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Pilote – {e(titre)}</title><link rel=stylesheet href='pilote.css'>"
            f"<header><a href='index.html'>🧭 Pilote</a> <small>· {e(titre)}</small></header><main>"
            f"<p class=note>Pilote – vue publique en lecture seule · dernière mise à jour : <b>{maj}</b>. Pour agir (nouvelle intervention, "
            f"clôturer, supprimer, lancer l'équipe), ouvrez Pilote dans le <a href='{CODESPACE}'>Codespace</a>.</p>{body}</main></html>")

def export():
    """Page publique : uniquement les 10 cases carrées numérotées (couleur = état), rien d'autre."""
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "*.html")): os.remove(f)
    shutil.copy(os.path.join(BASE, "pilote", "public", "pilote.css"), OUT)
    ouv = dict(c.execute(f"SELECT logement_id, COUNT(*) FROM interventions WHERE statut IN {OUV} GROUP BY 1").fetchall())
    urg = dict(c.execute(f"SELECT logement_id, COUNT(*) FROM interventions WHERE statut IN {OUV} AND priorite='urgente' GROUP BY 1").fetchall())
    cases = "".join(f"<div class='case {'urgent' if urg.get(i) else ('encours' if ouv.get(i) else 'ok')}'>{i}</div>"
                    for (i,) in c.execute("SELECT id FROM logements ORDER BY id"))
    with open(os.path.join(OUT, "index.html"), "w") as fh:
        fh.write("<!doctype html><html lang=fr><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                 f"<title>Pilote</title><link rel=stylesheet href='pilote.css'><body><div class=tuiles10>{cases}</div></body></html>")
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    return OUT
if __name__ == "__main__": print(export())
