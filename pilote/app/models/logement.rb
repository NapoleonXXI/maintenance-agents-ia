class Logement < ApplicationRecord
  self.inheritance_column = nil
  has_many :interventions
end
