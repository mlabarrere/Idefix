// Routeur (hash router : deep-links sans serveur, hébergeable en statique).
// Produit multi-mission SANS portfolio : l'accueil EST la galaxie de la mission
// par défaut ; chaque mission a ses vues (galaxie = index, analyse, paramètres).
// La bibliothèque scientifique (/science) absorbe la méthodologie.
import { createHashRouter, Navigate } from 'react-router-dom'
import { AppShell } from './app/AppShell'
import { GraphView } from './screens/GraphView'
import { Analyse } from './screens/Analyse'
import { Settings } from './screens/Settings'
import { ScienceShell } from './screens/science/ScienceShell'
import { ScienceHome } from './screens/science/ScienceHome'
import { SCIENCE_DOCS } from './screens/science/registry'

export const router = createHashRouter([
  // Accueil = galaxie de la mission par défaut (le produit EST l'outil d'analyse).
  { path: '/', element: <Navigate to="/m/russosphere" replace /> },
  // Ancien portfolio supprimé — /missions redirige vers la galaxie par défaut.
  { path: '/missions', element: <Navigate to="/m/russosphere" replace /> },
  {
    path: '/m/:missionId',
    element: <AppShell />,
    children: [
      // Galaxie = page d'atterrissage de mission ; Analyse en vue secondaire.
      { index: true, element: <GraphView /> },
      { path: 'analyse', element: <Analyse /> },
      { path: 'parametres', element: <Settings /> },
      // Anciens liens → redirections (stabilité des URLs / scénarios traçables).
      { path: 'synthese', element: <Navigate to="../analyse" replace /> },
      { path: 'channels', element: <Navigate to="../analyse" replace /> },
      { path: 'graph', element: <Navigate to=".." replace /> },
      { path: 'episodes', element: <Navigate to=".." replace /> },
      { path: 'methodologie', element: <Navigate to="/science/methodologie" replace /> },
    ],
  },
  {
    path: '/science',
    element: <ScienceShell />,
    children: [
      { index: true, element: <ScienceHome /> },
      ...SCIENCE_DOCS.filter((d) => d.Component).map((d) => {
        const C = d.Component!
        return { path: d.slug, element: <C /> }
      }),
    ],
  },
  { path: '*', element: <Navigate to="/m/russosphere" replace /> },
])
