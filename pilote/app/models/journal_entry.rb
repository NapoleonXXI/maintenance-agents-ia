# Journal append-only (triggers SQLite côté base : UPDATE/DELETE refusés). Rails ne fait qu'insérer.
class JournalEntry < ApplicationRecord
  self.table_name = "journal"
  def readonly? = persisted?
  def self.ajouter(acteur, action, objet, details = nil)
    create!(horodatage: Time.now.in_time_zone("Europe/Paris").strftime("%Y-%m-%dT%H:%M:%S"), acteur: acteur,
            action: action, objet: objet, details: details.nil? ? nil : JSON.generate(details))
  end
end
