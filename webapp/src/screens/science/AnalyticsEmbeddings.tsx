// Analytics vs embeddings — transcription de docs/analytics-vs-embedding.md.
import { DocPage, Section, Table, List } from './docs-ui'

export function AnalyticsEmbeddings() {
  return (
    <DocPage
      title="Analytics vs embeddings"
      subtitle="Deux lectures de la même galaxie : ce que chaque piste optimise, les métriques qui les comparent, et le trade-off qui les sépare."
      source="docs/analytics-vs-embedding.md"
    >
      <Section title="Analytics vs embedding — deux lectures de la même galaxie">
        <p>
          Idefix détecte les communautés de canaux par <strong>Leiden</strong> [Traag et al., 2019]
          sur le même graphe, selon deux pistes complémentaires. Ce document explique ce que chaque
          piste optimise, les métriques qui les comparent, et le <strong>trade-off</strong> qui les
          sépare. Chiffres : <code className="font-mono">docs/metrics/analytics_vs_embedding.json</code>{' '}
          (mission russosphere, galaxie 1170 nœuds). Références :{' '}
          <code className="font-mono">docs/references.md</code>.
        </p>
      </Section>

      <Section title="Les deux pistes">
        <Table
          head={['Piste', 'Signal', "Ce qu'elle optimise"]}
          rows={[
            [
              <strong>Analytics</strong>,
              <>structure des liens observés (forwards, mentions, co-citations) + vocabulaire</>,
              <>communautés <strong>structurelles</strong> : qui rediffuse qui</>,
            ],
            [
              <strong>Embedding</strong>,
              <>graphe enrichi d'arêtes de similarité d'embeddings (<code className="font-mono">EMB_SIM</code>, k=5 plus proches voisins, seuil cosinus 0.5, poids = 3·cosinus)</>,
              <>communautés <strong>sémantiques</strong> : qui « parle pareil »</>,
            ],
          ]}
        />
        <p>
          Les arêtes <code className="font-mono">EMB_SIM</code> ne sont jamais persistées : elles
          donnent seulement à Leiden un signal de contenu continu (embeddings locaux{' '}
          <code className="font-mono">paraphrase-multilingual-MiniLM-L12-v2</code>, 384-dim [Reimers
          &amp; Gurevych, 2019 ; Wang et al., 2020]) là où le graphe structurel est creux.
        </p>
      </Section>

      <Section title="Les métriques (et pourquoi chacune)">
        <List>
          <li>
            <strong>Cohésion intra</strong> — cosinus moyen intra-communauté sur les embeddings. Plus
            haut = groupes plus homogènes thématiquement.
          </li>
          <li>
            <strong>Silhouette</strong> [Rousseeuw, 1987] — cohésion vs séparation des clusters dans
            l'espace d'embedding (∈ [−1, 1]).
          </li>
          <li>
            <strong>Modularité</strong> [Newman, 2006] — qualité de la partition sur le{' '}
            <strong>graphe de liens</strong> (fraction d'arêtes intra-communauté au-delà du hasard).
          </li>
          <li>
            <strong>NMI / ARI</strong> [Danon et al., 2005 ; Hubert &amp; Arabie, 1985] — accord entre
            les deux partitions (1 = identiques, ~0 = sans rapport).
          </li>
        </List>
      </Section>

      <Section title="Résultats (russosphere)">
        <Table
          head={['Métrique', 'Analytics', 'Embedding', 'Lecture']}
          rows={[
            ['Cohésion intra', '0.6709', <strong>0.7049</strong>, '+5.1 % — groupes plus cohérents sémantiquement'],
            ['Silhouette (cosine)', '−0.2738', <strong>0.0214</strong>, "s'améliore mais reste faible (clusters peu nets dans l'espace d'embedding)"],
            ['Modularité', <strong>0.7547</strong>, '0.6301', 'baisse — voir trade-off'],
            ['Communautés conservées (≥2 canaux)', '27', '17', "l'embedding fusionne des groupes"],
            ['Communautés brutes (singletons inclus)', '512', '464', 'exposé pour transparence'],
            ['NMI (accord partitions)', '—', '0.887', 'partitions globalement proches'],
            ['ARI (accord partitions)', '—', '0.528', '~la moitié de la structure fine est réorganisée'],
          ]}
        />
      </Section>

      <Section title="Le trade-off (load-bearing)">
        <p className="border-l-2 border-gray-300 pl-4 italic dark:border-gray-700">
          L'embedding <strong>augmente la cohésion sémantique</strong> mais <strong>baisse la
          modularité</strong>.
        </p>
        <p>
          Ce n'est <strong>pas</strong> une régression — ce sont deux objectifs différents :
        </p>
        <List>
          <li>
            la <strong>modularité</strong> récompense les arêtes intra-communauté <strong>du graphe de
            liens</strong> (diffusion observée) ;
          </li>
          <li>
            les arêtes <code className="font-mono">EMB_SIM</code> relient des canaux sémantiquement
            proches <strong>même quand aucun forward ne les lie</strong> — elles <strong>traversent</strong>{' '}
            donc les communautés structurelles, ce qui mécaniquement abaisse la modularité tout en
            remontant la cohésion de contenu.
          </li>
        </List>
        <p>
          NMI élevé (0.887) + ARI moyen (0.528) confirment : la piste embedding garde la
          macro-structure mais <strong>réorganise environ la moitié</strong> des regroupements fins —
          exactement le comportement attendu d'un signal de contenu ajouté à un signal de structure.
        </p>
        <p>
          <strong>Quand utiliser laquelle.</strong> Analytics répond « qui rediffuse qui »
          (cartographie de diffusion, livrable T1). Embedding répond « qui partage la même ligne
          éditoriale » (cohérence thématique). Le commutateur galaxie bascule entre les deux snapshots ;
          le bon défaut dépend de la question posée, pas d'une supériorité absolue.
        </p>
      </Section>

      <Section title="Note de correction">
        <p>
          Une version antérieure du bloc <code className="font-mono">comparison</code> rapportait{' '}
          <code className="font-mono">n_communities</code> = 512/463 (toutes les communautés,{' '}
          <strong>singletons inclus</strong>), incohérent avec le snapshot (27/17, communautés ≥2
          canaux). Corrigé : <code className="font-mono">n_communities</code> = communautés{' '}
          <strong>conservées</strong>, et <code className="font-mono">n_communities_raw</code> expose le
          compte brut (<code className="font-mono">src/embed/community.py::comparison_block</code>).
        </p>
      </Section>
    </DocPage>
  )
}
