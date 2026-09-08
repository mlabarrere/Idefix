import { Loader2 } from "lucide-react"
import { useTranslation } from 'react-i18next'

// Spinner — indicateur de chargement inline. Reprend le libellé « Chargement… »
// et la même mise en page/classes ; l'anneau CSS manuel est remplacé par
// l'icône lucide `Loader2` (animate-spin), cohérente avec le substrat shadcn/ui.
export function Spinner() {
  const { t } = useTranslation()
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
      <Loader2 className="h-3 w-3 animate-spin text-slate-500" />
      {t('common.loading')}
    </div>
  )
}
