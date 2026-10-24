"""Outil généré automatiquement par l'agent Forgeron. Classe une demande par mots-clés (catégorie + priorité)."""
KEYWORDS = {'plomberie': ['fuite', 'robinet', 'wc', 'évier', 'douche', 'eau'], 'electricite': ['prise', 'disjonct', 'lumière', 'ampoule', 'court-circuit'], 'chauffage': ['chauffage', 'radiateur', 'chaudière', 'clim'], 'electromenager': ['frigo', 'réfrigérateur', 'four', 'lave', 'micro-ondes', 'plaque'], 'serrurerie': ['serrure', 'porte', 'clé', 'badge'], 'menuiserie_ouvrants': ['basse', 'fenêtre', 'position', 'roulant', 'store', 'volet']}
URGENT = ['inond', 'court-circuit', 'odeur de gaz', "plus d'eau", 'fumée']
def run(description):
    d = description.lower()
    cat = next((c for c, mots in KEYWORDS.items() if any(m in d for m in mots)), "divers")
    prio = "urgente" if any(u in d for u in URGENT) else ("haute" if cat in ("electricite", "chauffage") else "normale")
    return cat, prio
