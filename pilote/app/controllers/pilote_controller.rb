require "open3"
class PiloteController < ApplicationController
  CHAMPS = %w[description categorie priorite statut resultat]
  before_action :exiger_nom, only: %i[creer maj cloturer urgente supprimer basculer lancer]
  helper_method :nom_humain

  def accueil
    @logements = Logement.order(:id)
    @ouvertes = Intervention.ouvertes.group(:logement_id).count
    @urgentes = Intervention.ouvertes.where(priorite: "urgente").group(:logement_id).count
  end

  def logement
    @logement = Logement.find(params[:id])
    @interventions = @logement.interventions.visibles.order(Arel.sql("statut IN ('nouvelle','assignee','a_suivre') DESC, id DESC"))
  end

  def nouvelle; @logements = Logement.order(:id); end

  def creer
    i = Intervention.create!(logement_id: params[:logement_id].to_i, description: params[:description].to_s.strip,
                             statut: "nouvelle", cree_le: maintenant, maj_le: maintenant)
    tracer("CREE_INTERVENTION", i, { logement: i.logement_id, description: i.description })
    redirect_to logement_path(i.logement_id), notice: "Intervention ##{i.id} créée. Appuyez sur « Lancer l'équipe » pour la traiter."
  end

  def modifier; @i = Intervention.find(params[:id]); end
  def maj;      changer(Intervention.find(params[:id]), params.permit(*CHAMPS).to_h); end
  def cloturer; changer(Intervention.find(params[:id]), "statut" => "cloturee"); end
  def urgente;  changer(Intervention.find(params[:id]), "priorite" => "urgente"); end
  def confirmer_suppression; @i = Intervention.find(params[:id]); end

  def supprimer
    i = Intervention.find(params[:id]); avant = i.attributes
    i.update_columns(statut: "supprimee", maj_le: maintenant)
    tracer("SUPPRIME", i, { avant: avant, note: "suppression logique (statut supprimee)" })
    redirect_to logement_path(i.logement_id), notice: "Intervention ##{i.id} supprimée (tracée au journal)."
  end

  PERIODES = { "jour" => 1.day, "semaine" => 7.days, "mois" => 30.days }.freeze

  # Journal d'interventions : interventions de la période (jour / semaine / mois), plus récentes d'abord
  def journal_interventions
    @periode = PERIODES.key?(params[:periode]) ? params[:periode] : "jour"
    depuis = (Time.zone.now - PERIODES[@periode]).strftime("%Y-%m-%dT%H:%M:%S")
    @interventions = Intervention.visibles.where("cree_le >= ?", depuis).order(cree_le: :desc)
  end

  # Troisième onglet : contenu non encore décidé par le propriétaire
  def a_venir; end

  def journal
    rel = JournalEntry.order(id: :desc)
    rel = rel.where(acteur: params[:acteur]) if params[:acteur].present?
    if params[:logement].present?
      ids = Intervention.where(logement_id: params[:logement].to_i).pluck(:id).map { "intervention:#{_1}" }
      rel = rel.where(objet: ids)
    end
    @acteurs = JournalEntry.distinct.order(:acteur).pluck(:acteur)
    @logements = Logement.order(:id)
    @entrees = rel.limit(2000); @total = rel.count
  end

  def classement
    v = Intervention.visibles
    @faites = v.where(statut: "cloturee").count; @en_cours = v.ouvertes.count; @relayees = v.where(statut: "suivi_ouvert").count
    @par_logement = Logement.order(:id).map { |l| [l, v.ouvertes.where(logement_id: l.id).count, v.where(logement_id: l.id, statut: "cloturee").count] }
                            .sort_by { |_, o, f| [-o, -f] }
    @par_agent = JournalEntry.group(:acteur).order(Arel.sql("COUNT(*) DESC")).count
    @par_categorie = v.group(:categorie).order(Arel.sql("COUNT(*) DESC")).count
  end

  def avance
    @outils = Outil.order(:nom); @routage = Routage.order(:categorie); @messages = Message.order(id: :desc).limit(200)
  end

  def basculer
    o = Outil.find(params[:nom]); nouvel = o.actif.to_i == 1 ? 0 : 1
    o.update_columns(actif: nouvel)
    tracer(nouvel == 1 ? "REACTIVE_OUTIL" : "RETIRE_OUTIL", "outil:#{o.nom}")
    redirect_to avance_path, notice: "Outil #{o.nom} #{nouvel == 1 ? 'réactivé' : 'retiré'}."
  end

  def lancer
    tracer("DECLENCHE_CYCLE", "systeme")
    racine = Rails.root.join("..").to_s
    out, st = Open3.capture2e("python3", "orchestrator.py", "--pending", chdir: racine)
    redirect_to root_path, notice: st.success? ? "Équipe lancée : #{out.strip}" : "Échec du lancement : #{out.lines.last}"
  end

  def nom; end
  def enregistrer_nom
    cookies.permanent[:pilote_nom] = params[:nom].to_s.strip.first(40)
    redirect_to(params[:retour].presence || root_path)
  end

  private
  def nom_humain = cookies[:pilote_nom].presence
  def exiger_nom
    redirect_to nom_path(retour: request.referer), alert: "Indiquez d'abord votre prénom (une seule fois)." unless nom_humain
  end
  def maintenant = Time.now.in_time_zone("Europe/Paris").strftime("%Y-%m-%dT%H:%M:%S")
  def tracer(action, objet, details = nil)
    objet = "intervention:#{objet.id}" if objet.is_a?(Intervention)
    JournalEntry.ajouter("Humain:#{nom_humain}", action, objet, details)
    # export puis publication auto GitHub Pages en arrière-plan (AUTO_PUBLISH=0 pour désactiver)
    acteur = "Humain:#{nom_humain}"
    Process.detach(spawn("sh", "-c", "python3 export_static.py && python3 publier.py \"$0\" \"Publication auto après action Pilote ($1)\"",
                         acteur, action, chdir: Rails.root.join("..").to_s, out: File::NULL, err: File::NULL))
  end
  def changer(i, valeurs)
    diff = valeurs.select { |k, val| CHAMPS.include?(k) && i[k].to_s != val.to_s }.to_h { |k, val| [k, { avant: i[k], apres: val }] }
    i.update_columns(diff.transform_values { _1[:apres] }.merge(maj_le: maintenant)) if diff.any?
    tracer(diff.any? ? "MODIFIE_MANUELLEMENT" : "MODIFICATION_SANS_CHANGEMENT", i, diff)
    redirect_to logement_path(i.logement_id), notice: diff.any? ? "Intervention ##{i.id} mise à jour." : "Aucun changement."
  end
end
