// Self-check du prédicat de garde de layout galaxie (voir pull-snapshots.mjs).
// La galaxie exige des coordonnées x/y ; un snapshot Supabase sans coords ne doit
// JAMAIS écraser le fichier précalculé committé. Ce test verrouille cette règle.
import assert from 'node:assert/strict'
import { hasLayoutCoords } from './pull-snapshots.mjs'

// Sans coords → NE PAS écraser (le bug de prod : cercles concentriques).
assert.equal(hasLayoutCoords({ communities: [{ id: 1 }, { id: 2 }] }), false)
assert.equal(hasLayoutCoords({ communities: [{ id: 1, x: 0 }] }), false, 'x sans y ne compte pas')
assert.equal(hasLayoutCoords({}), false)
assert.equal(hasLayoutCoords(null), false)
// Avec coords → écrasement autorisé (payload frais complet).
assert.equal(hasLayoutCoords({ communities: [{ id: 1, x: 12.5, y: -3 }] }), true)
assert.equal(hasLayoutCoords({ communities: [{ id: 1 }, { id: 2, x: 1, y: 2 }] }), true, 'au moins une suffit')

console.log('✓ check-galaxy-guard: garde de coordonnées OK')
