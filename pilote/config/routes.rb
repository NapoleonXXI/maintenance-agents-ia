Rails.application.routes.draw do
  root "pilote#accueil"
  get  "logements/:id" => "pilote#logement", as: :logement
  get  "nouvelle" => "pilote#nouvelle"
  post "interventions" => "pilote#creer"
  get  "interventions/:id/modifier" => "pilote#modifier", as: :modifier
  post "interventions/:id" => "pilote#maj", as: :maj
  post "interventions/:id/cloturer" => "pilote#cloturer", as: :cloturer
  post "interventions/:id/urgente" => "pilote#urgente", as: :urgente
  get  "interventions/:id/supprimer" => "pilote#confirmer_suppression", as: :confirmer_suppression
  post "interventions/:id/supprimer" => "pilote#supprimer", as: :supprimer
  get  "journal" => "pilote#journal"
  get  "journal-interventions" => "pilote#journal_interventions", as: :journal_interventions
  get  "a-venir" => "pilote#a_venir", as: :a_venir
  get  "classement" => "pilote#classement"
  get  "avance" => "pilote#avance"
  post "outils/:nom/basculer" => "pilote#basculer", as: :basculer
  post "lancer" => "pilote#lancer"
  get  "nom" => "pilote#nom"
  post "nom" => "pilote#enregistrer_nom"
end
