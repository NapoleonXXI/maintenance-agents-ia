"""Publication automatique de docs/ sur GitHub Pages après un cycle de l'équipe ou une action Pilote.

Règles : ne committe QUE docs/, seulement si docs/ a changé (jamais de commit vide), push normal sur la
branche courante (jamais de force push). Toute erreur est journalisée sans faire planter le run.
Désactivation : AUTO_PUBLISH=0.
"""
import os, sys, fcntl, subprocess
from core import log
BASE = os.path.dirname(os.path.abspath(__file__))

def _git(*args, timeout=60):
    return subprocess.run(["git", *args], cwd=BASE, capture_output=True, text=True, timeout=timeout)

def publier(acteur="Orchestrateur", message="Publication auto après cycle"):
    if os.environ.get("AUTO_PUBLISH", "1") == "0":
        return "desactive"
    try:
        with open(os.path.join(BASE, ".git", "publier.lock"), "w") as verrou:
            fcntl.flock(verrou, fcntl.LOCK_EX)            # une seule publication à la fois
            branche = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            if not _git("status", "--porcelain", "--", "docs").stdout.strip():
                # docs/ identique. Relance seulement un push précédemment échoué, si les commits en attente ne touchent que docs/.
                fichiers = _git("diff", "--name-only", f"origin/{branche}..HEAD").stdout.split()
                if not fichiers or any(not f.startswith("docs/") for f in fichiers):
                    return "inchange"
                p = _git("push", "origin", branche, timeout=120)
                if p.returncode != 0:
                    log(acteur, "ECHEC_PUBLICATION", "docs/", {"etape": "push (relance)", "erreur": p.stderr[-500:]}); return "echec"
                log(acteur, "PUBLIE_PAGES", "docs/", {"relance": True, "branche": branche}); return "publie"
            _git("add", "--", "docs")
            c = _git("commit", "-m", message, "--only", "--", "docs")   # uniquement docs/, même si d'autres fichiers sont indexés
            if c.returncode != 0:
                log(acteur, "ECHEC_PUBLICATION", "docs/", {"etape": "commit", "erreur": (c.stderr or c.stdout)[-500:]}); return "echec"
            sha = _git("rev-parse", "--short", "HEAD").stdout.strip()
            p = _git("push", "origin", branche, timeout=120)  # jamais --force
            if p.returncode != 0:
                log(acteur, "ECHEC_PUBLICATION", "docs/", {"etape": "push", "commit": sha, "erreur": p.stderr[-500:]}); return "echec"
            log(acteur, "PUBLIE_PAGES", "docs/", {"commit": sha, "branche": branche}); return "publie"
    except Exception as x:
        try: log(acteur, "ECHEC_PUBLICATION", "docs/", {"erreur": str(x)[-500:]})
        except Exception: pass
        return "echec"

if __name__ == "__main__":
    print(publier(*(sys.argv[1:3])))
