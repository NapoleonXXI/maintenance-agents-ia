"""Sidecar humain : consultation + édition (journalisée). stdlib uniquement. Port 8810."""
import html, json, os, sys, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from core import conn, log, init, TOOLS_DIR
PORT = int(os.environ.get("PORT", 8810))
NAV = '<nav><a href="/">Suivi par logement</a> | <a href="/interventions">Interventions</a> | <a href="/journal">Journal</a> | <a href="/messages">Messages</a> | <a href="/outils">Outils créés</a> | <a href="/routage">Routage (auto-organisé)</a></nav>'
CSS = "<style>body{font-family:sans-serif;margin:20px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px;font-size:13px;vertical-align:top}nav{margin-bottom:15px}</style>"
e = lambda v: html.escape("" if v is None else str(v))
def table(rows, cols=None):
    if not rows: return "<p>Aucune donnée.</p>"
    cols = cols or rows[0].keys()
    return "<table><tr>" + "".join(f"<th>{e(c)}</th>" for c in cols) + "</tr>" + "".join(
        "<tr>" + "".join(f"<td>{e(r[c])}</td>" for c in cols) + "</tr>" for r in rows) + "</table>"
class H(BaseHTTPRequestHandler):
    def page(self, title, body, code=200):
        b = f"<!doctype html><meta charset=utf-8><title>{title}</title>{CSS}<h1>{title}</h1>{NAV}{body}".encode()
        self.send_response(code); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query); c = conn()
        if u.path == "/":
            import importlib.util
            p = os.path.join(TOOLS_DIR, "suivi_par_logement.py")
            if os.path.exists(p):
                s = importlib.util.spec_from_file_location("t", p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
                from core import DB; body = "<p>Généré par l'outil <code>tools/suivi_par_logement.py</code> écrit par l'agent Forgeron.</p>" + table(m.run(DB))
            else: body = "<p>Outil de suivi pas encore créé par les agents.</p>"
            return self.page("Suivi par logement", body)
        if u.path == "/interventions":
            rows = c.execute("SELECT * FROM interventions ORDER BY logement_id,id").fetchall()
            body = "<table><tr><th>id</th><th>logement</th><th>description</th><th>catégorie</th><th>priorité</th><th>statut</th><th>parent</th><th>résultat</th><th></th></tr>" + "".join(
                f"<tr><td>{r['id']}</td><td>{r['logement_id']}</td><td>{e(r['description'])}</td><td>{e(r['categorie'])}</td><td>{e(r['priorite'])}</td><td>{e(r['statut'])}</td><td>{e(r['parent_id'])}</td><td>{e(r['resultat'])}</td><td><a href='/edit?id={r['id']}'>modifier</a></td></tr>" for r in rows) + "</table>"
            return self.page("Interventions", body)
        if u.path == "/edit":
            r = c.execute("SELECT * FROM interventions WHERE id=?", (int(q["id"][0]),)).fetchone()
            f = "".join(f"<p>{k} : <input name='{k}' value='{e(r[k])}' size=60></p>" for k in ("description", "categorie", "priorite", "statut", "resultat"))
            return self.page(f"Modifier l'intervention #{r['id']}", f"<form method=post action='/edit?id={r['id']}'><p>Votre nom : <input name=auteur value='Raphaël'></p>{f}<button>Enregistrer (journalisé)</button></form>")
        if u.path == "/journal":
            return self.page("Journal (append-only)", table(c.execute("SELECT * FROM journal ORDER BY id DESC").fetchall()))
        if u.path == "/messages":
            return self.page("Messages envoyés / reçus", table(c.execute("SELECT * FROM messages ORDER BY id DESC").fetchall()))
        if u.path == "/routage":
            return self.page("Routage décidé par les agents", table(c.execute("SELECT * FROM routage").fetchall()))
        if u.path == "/outils":
            rows = c.execute("SELECT * FROM outils").fetchall()
            body = table(rows) + "".join(f"<form method=post action='/retirer?nom={e(r['nom'])}' style='display:inline'><button>{'Retirer' if r['actif'] else 'Réactiver'} {e(r['nom'])}</button></form> " for r in rows) + "".join(f"<h3>{e(r['nom'])}</h3><pre>{e(open(r['chemin']).read())}</pre>" for r in rows)
            return self.page("Outils créés par les agents", body)
        self.page("Introuvable", "", 404)
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        if u.path == "/retirer":
            nom = urllib.parse.parse_qs(u.query)["nom"][0]
            with conn() as c:
                a = c.execute("SELECT actif FROM outils WHERE nom=?", (nom,)).fetchone()[0]
                c.execute("UPDATE outils SET actif=? WHERE nom=?", (0 if a else 1, nom))
            log("Humain:sidecar", "RETIRE_OUTIL" if a else "REACTIVE_OUTIL", f"outil:{nom}")
            self.send_response(303); self.send_header("Location", "/outils"); self.end_headers(); return
        iid = int(urllib.parse.parse_qs(u.query)["id"][0])
        data = {k: v[0] for k, v in urllib.parse.parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode(), keep_blank_values=True).items()}
        auteur = "Humain:" + (data.pop("auteur", "") or "anonyme")
        with conn() as c:
            old = dict(c.execute("SELECT * FROM interventions WHERE id=?", (iid,)).fetchone())
            diff = {k: {"avant": old[k], "apres": v} for k, v in data.items() if k in ("description","categorie","priorite","statut","resultat") and str(old[k] or "") != v}
            for k, d in diff.items(): c.execute(f"UPDATE interventions SET {k}=?, maj_le=datetime('now','localtime') WHERE id=?", (d["apres"], iid))
        if diff: log(auteur, "MODIFIE_MANUELLEMENT", f"intervention:{iid}", diff)
        self.send_response(303); self.send_header("Location", "/interventions"); self.end_headers()
    def log_message(self, *a): pass
if __name__ == "__main__":
    init(); print(f"Sidecar sur http://127.0.0.1:{PORT}"); ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
