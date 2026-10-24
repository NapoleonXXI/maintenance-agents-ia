class Intervention < ApplicationRecord
  OUVERTS = %w[nouvelle assignee a_suivre]
  scope :visibles, -> { where.not(statut: "supprimee") }
  scope :ouvertes, -> { where(statut: OUVERTS) }
  def ouverte? = OUVERTS.include?(statut)
end
