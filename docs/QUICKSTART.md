# Démarrage rapide — Idéfix

Vous avez 10 minutes et voulez voir Idéfix tourner. Ce guide lance la webapp sur les données d'exemple incluses dans le dépôt — **aucune collecte Telegram, aucune base de données configurée requises pour cette étape.**

---

## Prérequis minimaux

- [Node.js 20+](https://nodejs.org/)
- [Python 3.11+](https://www.python.org/) + [uv](https://docs.astral.sh/uv/)

---

## 1. Cloner et installer

```bash
git clone https://github.com/mlabarrere/Idefix.git
cd Idefix
```

```bash
# Python (pipeline)
uv sync

# Frontend
cd webapp && npm install && cd ..
```

---

## 2. Lancer la webapp

Les données d'exemple sont déjà dans `webapp/public/data/` (missions `russosphere` et `gan`).

```bash
cd webapp
npm run dev
```

Ouvrir **[http://localhost:5173](http://localhost:5173)**.

Vous verrez :
- La galaxie des communautés de la russosphère (~27 nébuleuses reconstruites depuis @France24_fr)
- Le sélecteur de scénarios narratifs avec phases datées
- Le score de suspicion explicable par canal (familles b/c/d/f)

---

## 3. Lancer les tests

```bash
# Backend Python
uv run python -m pytest -x -q

# TypeScript strict (frontend)
cd webapp && npx tsc --noEmit
```

---

## Étape suivante

Pour collecter vos propres données et exécuter le pipeline complet, voir le **[guide d'installation complet](./INSTALL.md)**.

Pour comprendre ce qu'Idéfix fait et pourquoi, voir la **[documentation produit](./PRODUCT.md)**.
