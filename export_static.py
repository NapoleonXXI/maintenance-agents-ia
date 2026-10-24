"""Export statique en lecture seule de Pilote vers docs/ (GitHub Pages). Même look (pilote/public/pilote.css)."""
import os, glob, json, shutil, datetime, html, sqlite3
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
    # pastille : bleue si au moins une Nouvelle (prioritaire, à traiter), sinon orange si En cours, sinon rien
    nouv = {r[0] for r in c.execute("SELECT DISTINCT logement_id FROM interventions WHERE statut='nouvelle'")}
    enc = {r[0] for r in c.execute("SELECT DISTINCT logement_id FROM interventions WHERE statut NOT IN ('nouvelle','cloturee','suivi_ouvert','supprimee')")}
    past = lambda i: "<span class='pastille-case st-nouvelle'></span>" if i in nouv else ("<span class='pastille-case st-encours'></span>" if i in enc else "")
    cases = "".join(f"<div class='case {'urgent' if urg.get(i) else ('encours' if ouv.get(i) else 'ok')}'>{past(i)}{i}</div>"
                    for (i,) in c.execute("SELECT id FROM logements ORDER BY id"))
    css = open(os.path.join(BASE, "pilote", "public", "pilote.css")).read()   # CSS inliné : rendu fiable même sans pilote.css
    tete = ("<!doctype html><html lang=fr><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>Pilote</title><style>" + css + "</style><link rel=stylesheet href='pilote.css'><body>")
    entete = lambda t: ("<header class=entete><button type=button class=retour aria-label=Retour onclick=\"if(history.length>1&&document.referrer)"
                        "{history.back()}else{location.href='index.html'}\">←</button><h1>" + t + "</h1></header>")
    barre = ("<nav class=barre><a href='index.html' aria-label='Accueil'>🏠</a>"
             "<a href='journal.html'>📋<span>Journal d'interventions</span></a>"
             "<a href='a-venir.html'>⋯<span>À venir</span></a></nav></body></html>")
    with open(os.path.join(OUT, "index.html"), "w") as fh:
        fh.write(f"{tete}<div class=tuiles10>{cases}</div>{barre}")
    # Journal d'interventions : données réelles de la base, embarquées en JSON, filtrées côté client par période
    rows = [dict(r) for r in c.execute("SELECT id, logement_id, description, statut, cree_le FROM interventions "
                                         "WHERE statut != 'supprimee' ORDER BY cree_le DESC")]
    data = json.dumps(rows, ensure_ascii=False).replace("</", "<\\/")
    js = ("<script>const D=" + data + ";const J={jour:1,semaine:7,mois:30};"
          "const N={nouvelle:'Nouvelle',encours:'En cours',terminee:'Terminée'};"
          "const g=s=>s=='nouvelle'?'nouvelle':(s=='cloturee'||s=='suivi_ouvert')?'terminee':'encours';"
          "function v(p){document.querySelectorAll('.per').forEach(a=>a.classList.toggle('actif',a.dataset.p==p));"
          "const t=Date.now()-J[p]*864e5,L=D.filter(i=>new Date(i.cree_le)>=t),z=document.getElementById('z');"
          "z.innerHTML=L.length?'<ul class=liste-int>'+L.map(i=>"
          "'<li class=st-'+g(i.statut)+'><b>Logement '+i.logement_id+'</b> · '+String(i.description).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))+'<br><small>'+i.cree_le.replace('T',' ').slice(0,16)+' · '+N[g(i.statut)]+'</small></li>').join('')+'</ul>'"
          ":'<p class=vide>Aucune intervention</p>';}"
          "document.querySelectorAll('.per').forEach(a=>a.onclick=e=>{e.preventDefault();v(a.dataset.p)});v('jour');</script>")
    per = "".join(f"<a class=per href='#' data-p={k}>{l}</a>" for k, l in (("jour","Jour"),("semaine","Semaine"),("mois","Mois")))
    with open(os.path.join(OUT, "journal.html"), "w") as fh:
        TJ = "Journal d'interventions"
        leg = "<p class=legende><span class='pastille st-nouvelle'></span>Nouvelle <span class='pastille st-encours'></span>En cours <span class='pastille st-terminee'></span>Terminée</p>"
        fh.write(f"{tete}{entete(TJ)}<div class=page-nav><div class=periodes>{per}</div>{leg}<div id=z></div></div>{js}{barre}")
    with open(os.path.join(OUT, "a-venir.html"), "w") as fh:
        fh.write(f"{tete}{entete('À venir')}<div class=page-nav><p class=vide>À venir</p></div>{barre}")
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    return OUT
if __name__ == "__main__": print(export())
