import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * `cn` — fusion de classes utilitaires Tailwind.
 * clsx résout les entrées conditionnelles, twMerge dédoublonne les conflits
 * (ex. `px-2 px-4` → `px-4`). Convention shadcn/ui standard.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
