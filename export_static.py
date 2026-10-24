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
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, "*.html")): os.remove(f)
    shutil.copy(os.path.join(BASE, "pilote", "public", "pilote.css"), OUT)
    maj = datetime.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y %H:%M (heure de Paris)")
    logs = c.execute("SELECT * FROM logements ORDER BY id").fetchall()
    ouv = dict(c.execute(f"SELECT logement_id, COUNT(*) FROM interventions WHERE statut IN {OUV} GROUP BY 1").fetchall())
    urg = dict(c.execute(f"SELECT logement_id, COUNT(*) FROM interventions WHERE statut IN {OUV} AND priorite='urgente' GROUP BY 1").fetchall())
    nav = ("<div class=row><a class='btn sec' href='classement.html'>🏆 Classement</a><a class='btn sec' href='journal.html'>📜 Journal</a>"
           "<a class='btn sec' href='avance.html'>⚙️ Avancé</a></div>")
    tuiles = "".join(
        f"<a class='tuile {'urgent' if urg.get(l['id']) else ('encours' if ouv.get(l['id']) else 'ok')}' href='logement-{l['id']}.html'>"
        f"<span class=num>{l['id']}</span><span class=nom>{e(l['nom'])}</span><span class=ouv>"
        f"{'OK' if not ouv.get(l['id']) else str(ouv[l['id']]) + ' ouverte' + ('s' if ouv[l['id']] > 1 else '')}"
        f"{' · ' + str(urg[l['id']]) + ' urg.' if urg.get(l['id']) else ''}</span></a>" for l in logs)
    pages = {"index.html": ("Accueil", f"<div class=tuiles>{tuiles}</div>{nav}")}
    for l in logs:
        ivs = c.execute(f"SELECT * FROM interventions WHERE logement_id=? AND statut!='supprimee' ORDER BY statut IN {OUV} DESC, id DESC", (l["id"],)).fetchall()
        body = "".join(f"<div class=iv style='{'' if i['statut'] in ('nouvelle','assignee','a_suivre') else 'opacity:.65'}'><b>#{i['id']}</b> {e(i['description'])}<br>"
                       f"<span class=tag>{e(i['statut'])}</span><span class=tag>{e(i['categorie'] or 'non triée')}</span><span class=tag>{e(i['priorite'] or '-')}</span>"
                       f"{'<br><small>Résultat : ' + e(i['resultat']) + '</small>' if i['resultat'] else ''}</div>" for i in ivs) or "<p>Aucune intervention.</p>"
        pages[f"logement-{l['id']}.html"] = (f"Logement {l['id']} – {l['nom']}", body + "<a class='btn sec' href='index.html'>← Accueil</a>")
    V = "statut!='supprimee'"
    n = lambda q: c.execute(q).fetchone()[0]
    kpi = (f"<div class=kpi><div><b>{n(f'SELECT COUNT(*) FROM interventions WHERE statut=\"cloturee\"')}</b>faites</div>"
           f"<div><b>{n(f'SELECT COUNT(*) FROM interventions WHERE statut IN {OUV}')}</b>en cours</div>"
           f"<div><b>{n(f'SELECT COUNT(*) FROM interventions WHERE statut=\"suivi_ouvert\"')}</b>relayées</div></div>")
    rang = c.execute(f"""SELECT l.id, l.nom, SUM(i.statut IN {OUV}) o, SUM(i.statut='cloturee') f FROM logements l
                         LEFT JOIN interventions i ON i.logement_id=l.id AND i.{V} GROUP BY l.id ORDER BY o DESC, f DESC""").fetchall()
    cl = kpi + "<h2>Logements (plus d'ouvertes en tête)</h2>" + "".join(
        f"<a class=rang style='text-decoration:none;color:inherit' href='logement-{r['id']}.html'><span>{k+1}. <b>{r['id']}</b> {e(r['nom'])}</span><span><b>{r['o'] or 0}</b> ouv. · {r['f'] or 0} faites</span></a>" for k, r in enumerate(rang))
    cl += "<h2>Activité des agents (journal)</h2>" + "".join(f"<div class=rang><span>{e(a)}</span><b>{k}</b></div>" for a, k in c.execute("SELECT acteur, COUNT(*) FROM journal GROUP BY 1 ORDER BY 2 DESC"))
    cl += "<h2>Par catégorie</h2>" + "".join(f"<div class=rang><span>{e(a or 'non triée')}</span><b>{k}</b></div>" for a, k in c.execute(f"SELECT categorie, COUNT(*) FROM interventions WHERE {V} GROUP BY 1 ORDER BY 2 DESC"))
    pages["classement.html"] = ("Classement", cl)
    pages["journal.html"] = ("Journal complet (append-only)", f"<p>{n('SELECT COUNT(*) FROM journal')} entrées, plus récentes en tête. Filtres disponibles dans Pilote (Codespace).</p>" + "".join(
        f"<div class=iv><small>{e(r['horodatage'])}</small> · <b>{e(r['acteur'])}</b> · {e(r['action'])} · {e(r['objet'])}"
        f"{'<br><small style=color:#555>' + e(r['details'][:400]) + '</small>' if r['details'] else ''}</div>" for r in c.execute("SELECT * FROM journal ORDER BY id DESC")))
    av = "<h2>Outils écrits par les agents</h2>"
    for o in c.execute("SELECT * FROM outils ORDER BY nom"):
        p = os.path.join(BASE, "tools", os.path.basename(o["chemin"]))
        av += (f"<div class=iv><b>{e(o['nom'])}</b> v{o['version']} · {'actif' if o['actif'] else 'retiré'} · par {e(o['auteur'])}<br><small>{e(o['description'])}</small>"
               f"<details><summary>Code</summary><pre>{e(open(p).read() if os.path.exists(p) else '')}</pre></details></div>")
    av += "<h2>Routage décidé par les agents</h2><div class=scroll><table><tr><th>catégorie</th><th>technicien</th><th>créé par</th><th>le</th></tr>" + "".join(
        f"<tr><td>{e(r[0])}</td><td>{e(r[1])}</td><td>{e(r[2])}</td><td>{e(r[3])}</td></tr>" for r in c.execute("SELECT * FROM routage ORDER BY 1")) + "</table></div>"
    av += "<h2>Messages</h2>" + "".join(f"<div class=iv><small>{e(m['envoye_le'])} · #{m['intervention_id']}</small> <b>{e(m['de'])} → {e(m['vers'])}</b><br>{e(m['contenu'])}</div>" for m in c.execute("SELECT * FROM messages ORDER BY id DESC"))
    pages["avance.html"] = ("Avancé", av + "<a class='btn sec' href='index.html'>← Accueil</a>")
    for f, (t, b) in pages.items():
        with open(os.path.join(OUT, f), "w") as fh: fh.write(page(t, b, maj))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    return OUT
if __name__ == "__main__": print(export())
