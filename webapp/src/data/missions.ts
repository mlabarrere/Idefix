// Registre de missions côté UI (miroir de src/missions/* du backend). Statique
// pour le P1 ; pourra être chargé depuis data/missions.json plus tard.

// Les textes (label/description/caveat) NE sont PAS ici : ce sont des clés i18n
// `mission.<id>.label|description|caveat` (traduites dans les 6 locales). Ici on
// ne garde que la structure : id, couleur, capacités. Rendu via t(...) aux sites.
export interface MissionDescriptor {
  id: string
  color: string
  implemented: boolean // le moteur sait traiter cette mission
  available: boolean // un bundle de données est déployé (sinon : pas de cul-de-sac, on n'y entre pas)
}

// 'active' = données dispo ; 'soon' = moteur prêt, données à venir ; 'planned' = non implémentée.
export type MissionStatus = 'active' | 'soon' | 'planned'
export const missionStatus = (m: MissionDescriptor): MissionStatus =>
  m.available ? 'active' : m.implemented ? 'soon' : 'planned'

export const MISSIONS: MissionDescriptor[] = [
  { id: 'russosphere', color: '#C9880A', implemented: true, available: true },
  { id: 'gan', color: '#38bdf8', implemented: true, available: true },
  { id: 'dircom_minarm', color: '#94a3b8', implemented: false, available: false },
]

export const getMission = (id?: string): MissionDescriptor | undefined =>
  MISSIONS.find((m) => m.id === id)
