// Modèle de graphe — transcription de docs/graph-model.md (référence développeur).
import { DocPage, Section, SubSection, Table, List, Note } from './docs-ui'

export function ModeleGraphe() {
  return (
    <DocPage
      title="Modèle de graphe"
      subtitle="Référence développeur — couche de données et modèle de graphe channel-centric du démonstrateur Idéfix (traçage des propagateurs de désinformation sur Telegram, périmètre France)."
      source="docs/graph-model.md"
    >
      <Note>
        Document destiné aux développeurs. Décrit la couche de données et le modèle de graphe{' '}
        <em>channel-centric</em> du démonstrateur Idéfix (traçage des propagateurs de désinformation
        sur Telegram, périmètre France — voir <code className="font-mono">CLAUDE.md</code>).
        <br />
        Pour le <strong>détail</strong> du modèle (sémantique fine des arêtes, fenêtres de
        coordination, justification méthodologique), se reporter à{' '}
        <code className="font-mono">_bmad-output/planning-artifacts/graph-model-and-methodology-2026-06-05.md</code>.
        Le présent fichier est le <strong>résumé opérationnel</strong> côté code.
      </Note>

      <Section title="1. Stack et conventions">
        <List>
          <li>
            <strong>Python 3.14</strong>, environnement virtuel <code className="font-mono">.venv</code>{' '}
            (<code className="font-mono">./.venv/Scripts/python.exe</code> sous Windows).
          </li>
          <li>
            <strong>PostgreSQL natif</strong> = <em>source de vérité</em> (toutes les tables, voir §2).
            Pas de Docker (bloqué sur cette machine — <code className="font-mono">CLAUDE.md</code> §12).
          </li>
          <li>
            <strong>Graphe en mémoire via <code className="font-mono">igraph</code> /{' '}
            <code className="font-mono">networkx</code></strong>, construit à la volée depuis
            PostgreSQL. <strong>PAS de Neo4j, PAS de Kùzu</strong> (pas de serveur, pas de Java, pas de
            wheel py3.14 disponible).
          </li>
          <li>
            <strong>Pas de Docker, pas de Streamlit</strong> (sauf l'utilitaire ponctuel de session).
            Frontend = <code className="font-mono">webapp/</code> React/Vite statique, sans backend.
          </li>
          <li>
            <strong>Toujours préfixer le shell de{' '}
            <code className="font-mono">$env:PYTHONUTF8="1"</code></strong> (PowerShell) pour garantir
            l'encodage UTF-8 des sorties (titres de canaux, caractères accentués). Sous bash :{' '}
            <code className="font-mono">PYTHONUTF8=1 ...</code>.
          </li>
        </List>
        <p>Exemple d'invocation type :</p>
        <Note>
          <code className="font-mono">$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/detect_clusters.py</code>
        </Note>
      </Section>

      <Section title="2. Données — schéma PostgreSQL">
        <p>
          Le schéma canonique est créé par les migrations Alembic (<code className="font-mono">alembic
          upgrade head</code>). Quatre tables baseline :
        </p>
        <Table
          head={['Table', 'Rôle', 'Colonnes notables']}
          rows={[
            [
              <code className="font-mono">channels</code>,
              'Canaux observés (catalogue + découvertes snowball)',
              <><code className="font-mono">channel_id</code> (PK, BIGINT, stable à travers les rebrands de handle), <code className="font-mono">username</code>, <code className="font-mono">title</code>, <code className="font-mono">member_count</code>, <code className="font-mono">tier</code> (<code className="font-mono">hot</code>/<code className="font-mono">warm</code>/<code className="font-mono">cold</code>), <code className="font-mono">is_in_catalogue</code>, <code className="font-mono">extra</code> (JSONB — porte notamment <code className="font-mono">fr_score</code>)</>,
            ],
            [
              <code className="font-mono">messages</code>,
              'Messages backfillés',
              <><code className="font-mono">message_id</code>, <code className="font-mono">channel_id</code> (FK), <code className="font-mono">timestamp</code>, <code className="font-mono">text</code>, <code className="font-mono">language</code>, <code className="font-mono">forward_from_channel_id</code>, <code className="font-mono">forward_from_message_id</code>, <code className="font-mono">forward_delay_seconds</code>, <code className="font-mono">views</code>, <code className="font-mono">forwards</code>, <code className="font-mono">media_type</code>, <code className="font-mono">media_hash</code>, <code className="font-mono">urls</code> (JSONB), <code className="font-mono">is_deleted</code> ; unicité <code className="font-mono">(channel_id, message_id)</code></>,
            ],
            [
              <code className="font-mono">episodes</code>,
              'Registre des épisodes/revendications',
              <><code className="font-mono">episode_id</code> (PK), <code className="font-mono">title</code>, <code className="font-mono">thematic_category</code>, <code className="font-mono">target_entity</code> (déf. <code className="font-mono">FR_integrity</code>), <code className="font-mono">claim_text</code>, <code className="font-mono">claim_variants</code>, <code className="font-mono">bge_m3_embedding</code>, <code className="font-mono">status</code></>,
            ],
            [
              <code className="font-mono">evidence_dossiers</code>,
              'Dossiers de preuve produits',
              <><code className="font-mono">dossier_id</code>, <code className="font-mono">episode_id</code> (FK), <code className="font-mono">attribution_tier</code> (T1/T2), <code className="font-mono">severity_tier</code>, <code className="font-mono">methodology_version_hash</code>, <code className="font-mono">scores</code> (JSONB), <code className="font-mono">evidence_channels</code>, <code className="font-mono">coverage_callout</code> (caveat <em>single-platform blindness</em>, obligatoire)</>,
            ],
          ]}
        />
        <SubSection title="Particularités à connaître côté code">
          <List>
            <li>
              <strong><code className="font-mono">messages.text</code></strong> porte le contenu.
              Mentions et URLs ne sont <strong>pas</strong> des colonnes premières de premier ordre :
              elles sont <strong>dérivées du texte</strong> via{' '}
              <code className="font-mono">src/normalizer/handlers.py</code> (voir §4).
            </li>
            <li>
              <strong><code className="font-mono">messages.urls</code></strong> (JSONB) est souvent{' '}
              <strong>vide</strong> — les canaux citent fréquemment des domaines en clair dans le texte
              plutôt qu'en entité Telegram. Ne pas s'y fier seul ; re-dériver depuis{' '}
              <code className="font-mono">text</code> via <code className="font-mono">extract_urls</code>.
            </li>
            <li>
              <strong><code className="font-mono">messages.forward_from_channel_id</code></strong> +{' '}
              <code className="font-mono">forward_delay_seconds</code> portent la lignée de{' '}
              <em>forward</em> — la primitive de propagation Telegram (étoile de profondeur 1, délais
              multi-jours à longue traîne). C'est l'arête <code className="font-mono">FORWARD</code> du
              graphe.
            </li>
            <li>
              <strong><code className="font-mono">channels.extra.fr_score</code></strong> (float, écrit
              par <code className="font-mono">tag_france.py</code> /{' '}
              <code className="font-mono">snowball_crawl.py</code>) est le score brut de
              pertinence-France au niveau canal. <strong>Axiome #1 : on tague, on ne filtre pas</strong>{' '}
              — <code className="font-mono">fr_score</code> module la sévérité, il n'exclut pas un canal
              du graphe.
            </li>
          </List>
        </SubSection>
      </Section>

      <Section title="3. Modèle de graphe channel-centric">
        <p>
          L'unité du graphe est le <strong>canal</strong> (et, en complément, le <strong>domaine</strong>{' '}
          web cité). Les messages sont des supports d'arêtes, pas des nœuds de premier ordre dans le
          modèle de scoring.
        </p>
        <p>
          <strong>Nœuds</strong> : <code className="font-mono">Channel</code> (+{' '}
          <code className="font-mono">Domain</code> pour la couche adverse Pravda/Doppelganger).
        </p>
        <p>
          <strong>Arêtes</strong> (multiplex — plusieurs types entre deux canaux peuvent coexister) :
        </p>
        <Table
          head={['Arête', 'Sémantique', 'Dérivée de']}
          rows={[
            [
              <code className="font-mono">FORWARD</code>,
              'A re-forwarde un message de B (origine → relayeur), pondérée par occurrence + délai',
              <><code className="font-mono">messages.forward_from_channel_id</code> + <code className="font-mono">forward_delay_seconds</code></>,
            ],
            [
              <code className="font-mono">MENTIONS</code>,
              'A @-mentionne le canal B dans son texte',
              <code className="font-mono">extract_mentions(text)</code>,
            ],
            [
              <code className="font-mono">CITES_DOMAIN</code>,
              'A cite un domaine web (hors plateformes/raccourcisseurs)',
              <><code className="font-mono">extract_urls</code> + <code className="font-mono">canonical_domain</code> + <code className="font-mono">is_platform_host</code></>,
            ],
            [
              <code className="font-mono">CO_FORWARD</code>,
              'A et B re-forwardent les mêmes origines (motif de coordination)',
              "co-occurrence d'origines de forward",
            ],
            [
              <code className="font-mono">COPYPASTA</code>,
              'A et B publient un texte quasi-identique',
              'similarité de texte (différé)',
            ],
            [
              <code className="font-mono">CO_URL</code>,
              'A et B citent les mêmes URLs dans une fenêtre Δt',
              'co-citation fenêtrée',
            ],
            [
              <code className="font-mono">MEDIA_REUSE</code>,
              'A et B réutilisent le même média (pHash/dHash)',
              <code className="font-mono">media_hash</code>,
            ],
          ]}
        />
        <p>
          Les arêtes de <strong>coordination</strong> (<code className="font-mono">CO_FORWARD</code>,{' '}
          <code className="font-mono">CO_URL</code>, <code className="font-mono">COPYPASTA</code>,{' '}
          <code className="font-mono">MEDIA_REUSE</code>) sont <strong>fenêtrées dans le temps (Δt,
          multi-jours)</strong> : la convergence de <em>plusieurs</em> signaux faibles dans la fenêtre
          est le signal, pas un signal isolé (<code className="font-mono">CLAUDE.md</code> §7). Le détail
          des seuils (D3lta : copypasta 0.693 / rewording 0.715 / translation 0.85) et des fenêtres est
          dans le doc méthodologie référencé en tête.
        </p>
        <Note>
          Le graphe de forward « réel » exploité aujourd'hui (<code className="font-mono">build_graph.py</code>,{' '}
          <code className="font-mono">detect_clusters.py</code>,{' '}
          <code className="font-mono">score_channels.py</code>) n'utilise pour l'instant que l'arête{' '}
          <code className="font-mono">FORWARD</code> agrégée origine → relayeur (self-loops exclus). Les
          autres types d'arêtes sont spécifiés mais pas encore tous matérialisés (voir §5).
        </Note>
      </Section>

      <Section title="4. Extracteurs — src/normalizer/handlers.py">
        <p>
          Toutes les dérivations texte → signal de graphe vivent ici. Fonctions pures, testables sans
          réseau (voir <code className="font-mono">tests/normalizer/test_extract.py</code>).
        </p>
        <Table
          head={['Fonction', 'Entrée → Sortie', 'Notes']}
          rows={[
            [
              <code className="font-mono">extract_mentions(text)</code>,
              <>texte → <code className="font-mono">list[str]</code> de usernames (minuscule, sans <code className="font-mono">@</code>, dédupliqués)</>,
              <>regex anti-e-mail / anti <code className="font-mono">t.me/@handle</code> ; usernames 5–32 car.</>,
            ],
            [
              <code className="font-mono">extract_urls(text)</code>,
              <>texte → <code className="font-mono">list[str]</code> d'URLs légèrement canonicalisées (<code className="font-mono">scheme://netloc/path</code>)</>,
              'ponctuation traînante retirée, déduplication',
            ],
            [
              <code className="font-mono">canonical_domain(url)</code>,
              <>URL → host registrable minuscule (<code className="font-mono">www.</code> retiré, port/userinfo retirés) ou <code className="font-mono">None</code></>,
              'heuristique netloc (pas de public-suffix list)',
            ],
            [
              <code className="font-mono">is_platform_host(domain)</code>,
              <>domaine → <code className="font-mono">bool</code></>,
              <><code className="font-mono">True</code> pour t.me/x.com/youtube/raccourcisseurs → exclus du signal <code className="font-mono">CITES_DOMAIN</code></>,
            ],
            [
              <code className="font-mono">compute_media_hash(file_path)</code>,
              <>chemin fichier → pHash hex ou <code className="font-mono">None</code></>,
              <><strong>nécessite le fichier média téléchargé</strong> ; <code className="font-mono">imagehash.phash</code></>,
            ],
            [
              <code className="font-mono">detect_language(text)</code>,
              <>texte → code ISO 639-1 ou <code className="font-mono">None</code></>,
              <><code className="font-mono">langdetect</code> ; <code className="font-mono">None</code> si texte {'<'} 20 car.</>,
            ],
            [
              <code className="font-mono">clean_text(text)</code>,
              'texte → texte sans markdown gras/souligné',
              'normalisation légère',
            ],
          ]}
        />
        <SubSection title="Exemples d'usage">
          <Note>
            <code className="font-mono">
              {'from src.normalizer.handlers import (extract_mentions, extract_urls, canonical_domain, is_platform_host,)'}
            </code>
            <br />
            <br />
            <code className="font-mono">{'text = "Relayez @Vbachir — preuves sur https://news-pravda.com/fr/article.html"'}</code>
            <br />
            <br />
            <code className="font-mono">{'extract_mentions(text)        # -> ["vbachir"]'}</code>
            <br />
            <code className="font-mono">{'urls = extract_urls(text)     # -> ["https://news-pravda.com/fr/article.html"]'}</code>
            <br />
            <code className="font-mono">{'dom = canonical_domain(urls[0])   # -> "news-pravda.com"'}</code>
            <br />
            <code className="font-mono">{'is_platform_host(dom)         # -> False  => garde l\'arête CITES_DOMAIN'}</code>
            <br />
            <code className="font-mono">{'is_platform_host("t.me")      # -> True   => exclue du signal adverse'}</code>
          </Note>
          <Note>
            <code className="font-mono">{'# Empreinte média : suppose le fichier déjà téléchargé sur disque'}</code>
            <br />
            <code className="font-mono">{'from src.normalizer.handlers import compute_media_hash'}</code>
            <br />
            <code className="font-mono">{'h = compute_media_hash("data/media/abc123.jpg")  # -> "f0e1..." ou None'}</code>
          </Note>
        </SubSection>
      </Section>

      <Section title="5. À construire (pas encore fait)">
        <p>Spécifié dans le modèle, non encore matérialisé en base/code :</p>
        <List>
          <li>
            <strong>Table <code className="font-mono">edges</code></strong> persistant le graphe
            multiplex (au-delà du forward agrégé recalculé à la volée).
          </li>
          <li>
            <strong>Dérivation multiplex</strong> des arêtes <code className="font-mono">MENTIONS</code> /{' '}
            <code className="font-mono">CITES_DOMAIN</code> / <code className="font-mono">CO_FORWARD</code> /{' '}
            <code className="font-mono">CO_URL</code> / <code className="font-mono">COPYPASTA</code> /{' '}
            <code className="font-mono">MEDIA_REUSE</code> à partir du texte et des médias.
          </li>
          <li>
            <strong>Score de suspicion par canal</strong> consolidant les cinq familles (claim
            proximity / cascade role / coordination / recidivism / GenAI-origin) au niveau canal — la
            direction de classification <strong>niveau canal</strong> retenue (voir{' '}
            <code className="font-mono">scripts/build_channel_digests.py</code>).
          </li>
        </List>
        <p>
          Le crawl <code className="font-mono">scripts/snowball_crawl.py --waves N --cap M</code>{' '}
          <strong>grossit le graphe</strong> en backfillant la frontière des canaux les plus{' '}
          <em>forwardés</em> non encore ingérés (capillarité en profondeur sur N vagues).{' '}
          <strong>Un seul processus, sérialisé, un seul compte +33</strong> — ne jamais paralléliser
          MTProto (règle dure d'hygiène de compte).
        </p>
      </Section>

      <Section title="6. Comment lancer les choses">
        <Note>
          <code className="font-mono">{'# Tests des couches concernées'}</code>
          <br />
          <code className="font-mono">{'$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe -m pytest tests/labeling tests/normalizer -q'}</code>
          <br />
          <br />
          <code className="font-mono">{'# Initialiser / migrer le schéma DB (idempotent)'}</code>
          <br />
          <code className="font-mono">{'$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe -m alembic upgrade head'}</code>
          <br />
          <br />
          <code className="font-mono">{'# Grossir le graphe (Telegram, sérialisé, compte +33)'}</code>
          <br />
          <code className="font-mono">{'$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/snowball_crawl.py --waves 3 --cap 20'}</code>
          <br />
          <br />
          <code className="font-mono">{'# (Re)tagger la pertinence-France des canaux'}</code>
          <br />
          <code className="font-mono">{'$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/tag_france.py'}</code>
          <br />
          <br />
          <code className="font-mono">{'# Détection de grappes coordonnées (lecture seule, igraph)'}</code>
          <br />
          <code className="font-mono">{'$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/detect_clusters.py'}</code>
          <br />
          <code className="font-mono">{'$env:PYTHONUTF8="1"; ./.venv/Scripts/python.exe scripts/detect_clusters.py --seed @Dugin_Aleksandr --hops 5'}</code>
        </Note>
        <p>
          Voir <code className="font-mono">scripts/README.md</code> pour l'inventaire complet des
          scripts et leur contact (ou non) avec Telegram.
        </p>
      </Section>
    </DocPage>
  )
}
