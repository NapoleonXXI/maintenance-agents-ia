class Intervention < ApplicationRecord
  LIBELLES = { "nouvelle" => "Nouvelle", "encours" => "En cours", "terminee" => "Terminée" }.freeze
  def self.groupe_statut(st)
    case st when "nouvelle" then "nouvelle" when "cloturee", "suivi_ouvert" then "terminee" else "encours" end
  end
  OUVERTS = %w[nouvelle assignee a_suivre]
  scope :visibles, -> { where.not(statut: "supprimee") }
  scope :ouvertes, -> { where(statut: OUVERTS) }
  def ouverte? = OUVERTS.include?(statut)
end
