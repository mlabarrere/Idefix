// Coquille produit SaaS : sidebar fixe à gauche (marque + switcher de mission +
// navigation en sections libellées « Mission » / « Ressources » + paramètres et
// contrôles en bas), zone de travail à droite (galaxie/vues routées plein cadre).
// La mission vient de l'URL (/m/:missionId). Plus de portfolio : l'accueil EST la
// galaxie ; le changement de mission passe uniquement par le switcher.
import { Select as SelectPrimitive } from 'radix-ui'
import { Orbit, LayoutDashboard, FlaskConical, Settings as SettingsIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink, Navigate, Outlet, useNavigate, useParams } from 'react-router-dom'
import { Select, SelectContent, SelectTrigger } from '@/components/ui/select'
import { MISSIONS, getMission, missionStatus } from '../data/missions'
import { HeaderControls } from './HeaderControls'
import { BrandMark, Signature, SidebarSection, SidebarItem } from '@/components/patterns'
import { SelectionProvider } from '../state/SelectionContext'
import { SnapshotModeProvider } from '../state/SnapshotMode'

export function AppShell() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { missionId } = useParams<{ missionId: string }>()
  const mission = getMission(missionId)

  // Mission inconnue -> galaxie de la mission par défaut (plus de portfolio).
  if (!mission) return <Navigate to="/m/russosphere" replace />

  const base = `/m/${mission.id}`

  return (
    <SelectionProvider missionId={mission.id}>
      <SnapshotModeProvider>
        <div className="flex h-full">
          {/* ── Sidebar ── */}
          <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-card/50 sm:flex">
            <div className="flex items-center px-4 py-3">
              <NavLink to={base} aria-label="Idéfix">
                <BrandMark />
              </NavLink>
            </div>

            {/* Switcher de mission (shadcn Select / Radix). */}
            <div className="px-3 pb-1">
              <Select value={mission.id} onValueChange={(id) => navigate(`/m/${id}`)}>
                <SelectTrigger
                  size="sm"
                  className="w-full justify-between gap-1.5 rounded-md border-border bg-transparent px-2 text-foreground shadow-none"
                >
                  <span className="flex min-w-0 items-center gap-1.5">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: mission.color }} />
                    <span className="truncate">{t(`mission.${mission.id}.label`)}</span>
                  </span>
                </SelectTrigger>
                <SelectContent position="popper" align="start" sideOffset={4} className="w-64">
                  {MISSIONS.map((m) => (
                    <SelectPrimitive.Item
                      key={m.id}
                      value={m.id}
                      disabled={!m.available}
                      textValue={t(`mission.${m.id}.label`)}
                      className="flex cursor-pointer items-center gap-2 rounded-sm px-3 py-1.5 text-sm text-foreground outline-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 data-[highlighted]:bg-accent"
                    >
                      <SelectPrimitive.ItemText>
                        <span className="flex items-center gap-2">
                          <span className="h-2.5 w-2.5 rounded-full" style={{ background: m.color }} />
                          {t(`mission.${m.id}.label`)}
                        </span>
                      </SelectPrimitive.ItemText>
                      {!m.available && (
                        <span className="ml-auto text-xs text-muted-foreground">
                          {missionStatus(m) === 'soon' ? t('nav.statusSoon') : t('nav.statusPlanned')}
                        </span>
                      )}
                    </SelectPrimitive.Item>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Navigation en sections (style Catalyst). */}
            <nav className="flex flex-col px-3">
              {mission.available && (
                <SidebarSection heading={t('nav.mission')}>
                  <SidebarItem to={base} end icon={Orbit}>
                    {t('nav.galaxie')}
                  </SidebarItem>
                  <SidebarItem to={`${base}/analyse`} icon={LayoutDashboard}>
                    {t('nav.analyse')}
                  </SidebarItem>
                </SidebarSection>
              )}
              <SidebarSection heading={t('nav.resources')}>
                <SidebarItem to="/science" icon={FlaskConical}>
                  {t('nav.science')}
                </SidebarItem>
              </SidebarSection>
            </nav>

            {/* Bas de sidebar : paramètres, contrôles, signature. */}
            <div className="mt-auto flex flex-col gap-0.5 border-t border-border px-3 py-3">
              <SidebarItem to={`${base}/parametres`} icon={SettingsIcon}>
                {t('nav.settings')}
              </SidebarItem>
              <div className="flex items-center justify-between px-1 pt-2">
                <HeaderControls />
                <Signature className="hidden lg:inline" />
              </div>
            </div>
          </aside>

          {/* ── Zone de travail ── */}
          <div className="flex min-w-0 flex-1 flex-col">
            {/* Barre compacte mobile (sidebar masquée < sm) : marque + switcher. */}
            <div className="flex shrink-0 items-center gap-3 border-b border-border px-4 py-2 sm:hidden">
              <NavLink to={base} aria-label="Idéfix">
                <BrandMark />
              </NavLink>
              <span className="truncate text-sm font-medium text-foreground">
                {t(`mission.${mission.id}.label`)}
              </span>
            </div>

            <main className="min-h-0 flex-1 overflow-hidden">
              {mission.available ? (
                <Outlet context={{ missionId: mission.id }} />
              ) : (
                <div className="p-8 text-sm text-muted-foreground">
                  {missionStatus(mission) === 'soon' ? t('nav.emptySoon') : t('nav.emptyPlanned')}
                </div>
              )}
            </main>
          </div>
        </div>
      </SnapshotModeProvider>
    </SelectionProvider>
  )
}
