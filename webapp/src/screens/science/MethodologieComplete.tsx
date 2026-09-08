// Méthodologie (document canonique) — transcription de METHODOLOGY.md.
import { DocPage, Section, SubSection, Table, List, Limit, Note, Mono } from './docs-ui'

export function MethodologieComplete() {
  return (
    <DocPage
      title="Méthodologie (document canonique)"
      subtitle="Système d'analyse de propagation et de coordination pour canaux Telegram publics : il reconstruit la diffusion observable, fait émerger les canaux d'ensemencement précoces, détecte les comportements coordonnés et produit des dossiers classés et explicables pour analystes humains — jamais un détecteur de fausses nouvelles."
      source="METHODOLOGY.md"
    >
      <Note>
        <strong>Version :</strong> 0.3.0-poc · <strong>Date :</strong> 2026-06-29 ·{' '}
        <strong>Statut :</strong> PoC (pré-publication — pas encore versé au registre public) ·{' '}
        <strong>Remplace :</strong> 0.2.0-poc (2026-06-10).
      </Note>

      <Note>
        Ce document doit être publié <strong>3 mois</strong> avant toute mise en production d'une
        sortie de détection live (exigence de résistance EIP). Cible : novembre 2026.
      </Note>

      <Section title="Registre des changements">
        <SubSection title="0.2.0 → 0.3.0">
          <p>
            Une <strong>famille de score de cohérence sémantique (f)</strong> bâtie sur des
            embeddings de phrases locaux est désormais câblée dans le score de suspicion, comblant
            l'écart où les embeddings de canaux étaient calculés pour la détection de communautés
            mais jamais consommés par le scoring (§3.1, §3.4). La{' '}
            <strong>découverte d'épisodes est désormais automatique</strong> (clustering de densité
            avec un bloc sémantique « pourquoi ») plutôt qu'un registre maintenu à la main (§4bis).
            La <strong>gate multi-source est désormais traçable</strong> : l'ensemble exact des
            familles déclenchées est matérialisé par canal (<code className="font-mono">gate_families</code>,
            §3.2). Une <strong>piste de validation non circulaire</strong> a été construite — une
            baseline organique-FR externe, un gold d'épisode externe, et un ROC-AUC de discrimination
            par embedding — pour traiter les écarts de circularité et de corpus organique manquant qui
            bornaient les revendications de la v0.2.0 (§8). Les instantanés de communauté sont
            désormais <strong>relus</strong> par le pipeline pour l'analyse de dérive temporelle, et
            non seulement poussés (§9).
          </p>
        </SubSection>
        <SubSection title="0.1.0 → 0.2.0">
          <p>
            Le cœur de détection réellement livré est un{' '}
            <strong>score de suspicion par canal explicable</strong>, et non le réseau de neurones de
            graphe GraphSAGE+LSTM décrit en 0.1.0. Le GNN est repositionné comme cible ultérieure
            (§7). La plateforme est devenue <strong>multi-mission</strong> (§6). L'état de validation
            est documenté honnêtement face à quatre expériences de falsification (§8). Les
            revendications d'infrastructure (Neo4j, Docker Compose) sont corrigées vers la pile
            réellement implémentée (§9).
          </p>
        </SubSection>
      </Section>

      <Section title="1. Vue d'ensemble du système">
        <p>
          Idéfix est un <strong>système d'analyse de propagation et de coordination</strong> pour les
          canaux Telegram publics. Il reconstruit la diffusion observable, fait émerger les canaux
          d'ensemencement précoces, détecte les comportements coordonnés, et produit des dossiers
          classés et explicables pour analystes humains. Ce n'est <strong>pas</strong> un détecteur
          de fausses nouvelles : il n'étiquette jamais un post individuel comme vrai ou faux, et sa
          sortie est une file d'examen priorisée avec des preuves par signal, jamais un verdict.
        </p>
        <p>
          <strong>Plateforme :</strong> canaux Telegram publics uniquement (MTProto). La couverture
          mono-plateforme est la limitation porteuse de ce système et est divulguée dans chaque
          sortie (§5).
        </p>
        <p>
          <strong>Modèle opérationnel : arm-only.</strong> Les sorties sont acheminées vers les
          destinataires institutionnels désignés (VIGINUM et Arcom pour la mission par défaut ; la
          cellule OPSEC concernée pour la mission GAN). Le système n'exécute jamais d'action de
          plateforme et ne publie jamais d'attribution lui-même.
        </p>
        <p>
          <strong>Missions :</strong> le moteur est agnostique au thème ; la portée analytique est
          fixée par mission (§6). La mission par défaut surveille la désinformation coordonnée
          attaquant l'image, l'intégrité ou la souveraineté de la France. La pertinence thématique{' '}
          <strong>module la sévérité ; elle ne filtre jamais l'inclusion</strong> (§3.3).
        </p>
      </Section>

      <Section title="2. Architecture de détection (telle qu'implémentée)">
        <p>
          Le cœur de détection livré est un{' '}
          <strong>score de suspicion par canal explicable</strong> (<code className="font-mono">src/scorer/channel_suspicion.py</code>).
          L'unité d'analyse est le <strong>canal</strong>, pas le message. Le pipeline est entièrement
          hors-ligne :
        </p>
        <Mono>
          ingestion MTProto → normalisation → dérivation des arêtes de forward → tagging thématique →
          scoring de suspicion (familles structurelles + famille sémantique f) → découverte
          d'épisodes → analyse de communautés / porosité → export JSON statique → magasin
          d'instantanés (push/pull)
        </Mono>
        <SubSection title="Couche 1 — Construction du graphe">
          <List>
            <li>
              Graphe multiplex centré-canal en mémoire (NetworkX/igraph), adossé à une table{' '}
              <code className="font-mono">edges</code> PostgreSQL.
            </li>
            <li>
              Familles d'arêtes : <strong>propagation</strong> (arêtes FORWARD, orientées origine →
              relayeur, portant les comptes de forward et <code className="font-mono">delay_seconds</code>),{' '}
              <strong>influence</strong> (citations de domaine, mentions),{' '}
              <strong>coordination</strong> (co-forwarding fenêtré dans le temps, similarité de
              texte, co-URL — les horodatages discriminent la coordination de la coïncidence).
            </li>
            <li>
              La primitive de propagation de Telegram est l'étoile de forward à profondeur 1 avec des
              délais multi-jours à queue lourde ; l'analyse agrège donc sur des fenêtres multi-jours
              et à travers les épisodes plutôt qu'au sein de cascades isolées.
            </li>
          </List>
        </SubSection>
        <SubSection title="Couche 2 — Score de suspicion explicable">
          <List>
            <li>
              Familles de score (§3) calculées sur la projection de forward et les arêtes de
              coordination, combinées par une somme pondérée transparente, puis modulées par des
              boosts de sévérité bornés (§3.3).
            </li>
            <li>
              Chaque composante du score de chaque canal est préservée dans la sortie (poids, valeurs
              par famille, statut de déclenchement, détail des boosts) afin qu'un analyste puisse
              justifier tout classement à partir du seul dossier.
            </li>
          </List>
        </SubSection>
        <SubSection title="Couche 3 — Sortie institutionnelle">
          <List>
            <li>
              Bundles de preuves JSON précalculés avec déclaration de tier d'attribution (T1/T2
              uniquement — §4).
            </li>
            <li>
              Callout de couverture obligatoire (divulgation de l'aveuglement mono-plateforme — §5).
            </li>
            <li>
              Chaîne de custody : hash de version de la méthodologie (SHA-256 de ce document),
              horodatages, identifiants stables.
            </li>
            <li>
              Les canaux sont suivis par ID de canal (stable à travers les rebrandings de handle) ;
              la confiance est rétrogradée en « dégradée/périmée » lorsqu'un canal n'a pas été
              interrogé depuis 14 jours ou plus.
            </li>
          </List>
        </SubSection>
      </Section>

      <Section title="3. Le score de suspicion">
        <SubSection title="3.1 Familles de score">
          <Table
            head={['Famille', 'Statut (PoC v0)', 'Méthode']}
            rows={[
              [
                '(a) Proximité de revendication',
                <strong>Réservée (N/A en v0)</strong>,
                <>Pas de registre de revendications câblé pour l'instant. Match sémantique à une revendication enregistrée (BGE-M3), seam injectable.</>,
              ],
              [
                '(b) Rôle en cascade',
                <strong>Active</strong>,
                <>Composite Bridge-Score (in-degree, vecteur propre, clustering) sur le graphe de forward ; archétypes : seeding-source / forward-hub / cross-channel bridge / reactivator. Les canaux isolés ne sont jamais comptés comme déclenchés (garde-fou centralité dégénérée).</>,
              ],
              [
                '(c) Coordination',
                <strong>Active</strong>,
                <>Arêtes de coordination fenêtrées dans le temps (fenêtre par défaut 72 h) : co-forwarding, texte quasi-identique, co-URL ; le renforcement multi-type élève la valeur.</>,
              ],
              [
                '(d) Récidive inter-épisodes',
                <strong>Active</strong>,
                <>Forward-influence (forwards gagnés) + récurrence de canal-source — ni nombre d'abonnés, ni heuristiques de bot.</>,
              ],
              [
                '(e) Probabilité d’origine GenAI',
                <strong>Réservée (N/A en v0)</strong>,
                <>Détecteur non câblé. Seam pour détecteurs audio/vidéo/texte-LLM.</>,
              ],
              [
                '(f) Cohérence sémantique',
                <strong>Active (opt-in)</strong>,
                <>Signal d'embedding de phrases local (<code className="font-mono">src/scorer/embedding_signals.py</code>) : distance de l'embedding moyen d'un canal à un centroïde de baseline organique-FR, combinée à la proximité aux embeddings de canaux adverses connus. Signal de <em>contenu</em>, structurellement indépendant des familles dérivées du graphe (b)/(c)/(d) — voir §3.4.</>,
              ],
            ]}
          />
        </SubSection>
        <SubSection title="3.2 Combinaison (poids de la mission par défaut)">
          <p>
            Le score de base est une somme pondérée des familles <strong>déclenchées</strong>,
            renormalisée sur les poids des familles présentes : (b) 0.30 · (c) 0.25 · (d) 0.30, avec
            (a) 0.15 et (e) 0.15 réservées et exclues tant qu'elles sont N/A. La famille sémantique
            (f) est opt-in (activée avec <code className="font-mono">build_scores.py --embeddings</code>)
            et, lorsqu'elle est présente, entre dans la même somme renormalisée comme une famille
            déclenchée additionnelle ; elle est exclue — exactement comme une famille réservée —
            lorsque les embeddings ne sont pas calculés, de sorte que le score structurel-seul est
            inchangé. Les bandes de confiance (lo/hi) se propagent à travers la même combinaison. Les
            poids sont une configuration par mission (§6), publiée dans le cadre de cette
            méthodologie.
          </p>
          <p>
            <strong>Gate multi-source :</strong> un canal ne franchit la gate que lorsqu'au{' '}
            <strong>moins 2 familles distinctes</strong> sont déclenchées (seuil de déclenchement
            0.3). Les signaux uniques sont traités comme non fiables par construction. Parce que (f)
            est un signal de <em>contenu</em> indépendant des familles de graphe, un canal blanchi par
            structure-plus-sémantique porte une corroboration véritablement indépendante, et non deux
            vues du même graphe. La gate est <strong>traçable</strong> : l'ensemble exact des clés de
            familles déclenchées est matérialisé par canal (<code className="font-mono">gate_families</code>,
            migration <code className="font-mono">0008</code>) aux côtés du booléen{' '}
            <code className="font-mono">met</code>, de sorte que toute assignation de tier peut être
            auditée depuis l'enregistrement stocké. La gate pilote aussi l'assignation de tier (§4) :
            gate atteinte ⇒ T2 (récurrence comportementale), sinon T1.
          </p>
        </SubSection>
        <SubSection title="3.3 Modulation de sévérité — bornée, à la hausse uniquement, jamais un filtre">
          <p>
            Trois signaux <strong>élèvent</strong> la sévérité d'un canal déjà suspect. Ils sont
            multiplicatifs sur le score de base, bornés, et ils ne <strong>gatent ni ne filtrent
            jamais</strong> l'inclusion :
          </p>
          <Table
            head={['Modulateur', 'Borne', 'Base']}
            rows={[
              [
                'Reforward-depuis-suspect',
                '≤ +20 %',
                <>Fraction des forwards entrants provenant de canaux suspects-prior.</>,
              ],
              [
                'Citation de domaine adverse',
                '≤ +15 % (sature à 5 citations)',
                <>Citation d'infrastructure adverse documentée (ex. réseau Pravda, amplificateurs Doppelganger).</>,
              ],
              [
                'Ciblage thématique',
                '≤ +20 %',
                <>Score de pertinence thématique cross-langue (ciblage-France pour la mission par défaut, ciblage-GAN pour la mission GAN).</>,
              ],
            ]}
          />
          <p>
            <strong>MÉTA-CONTRAINTE (porteuse) :</strong> le lien adverse et la pertinence thématique
            modulent la <em>sévérité</em>, jamais l'<em>inclusion</em>. Le système fait émerger{' '}
            <strong>toute</strong> activité coordonnée dans le corpus ; aucun canal n'est exclu de la
            file pour être hors-thème ou pour manquer de lien adverse. Parce que la modulation est
            multiplicative, un canal à suspicion structurelle nulle reste à zéro quelle que soit sa
            pertinence thématique — la presse légitime discutant de la France n'est pas promue.
            Inversement, la densité de mots-clés français (<code className="font-mono">fr_score</code>)
            est un champ d'affichage uniquement et n'est jamais utilisée comme filtre ou ancrage : un
            canal adverse opérant en russe ou en anglais avec une faible densité de mots-clés
            français peut et doit pouvoir se classer en tête.
          </p>
          <p>
            <strong>Artefact de symétrie :</strong> chaque bundle scoré publie la part de la{' '}
            <em>population scorée complète</em> (et non la page affichée) liée à de l'infrastructure
            adverse documentée versus organique, comme ratio de transparence permanent.
          </p>
        </SubSection>
        <SubSection title="3.4 Famille de cohérence sémantique (f)">
          <p>
            La famille (f) (<code className="font-mono">src/scorer/embedding_signals.py</code>) donne
            au score un signal de <strong>contenu</strong> structurellement indépendant du graphe.
            Chaque canal est représenté par la moyenne des embeddings de phrases locaux de ses
            messages les plus longs (<code className="font-mono">sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2</code>,
            384-dim, FR/RU/EN ; déterministe, mis en cache hors-ligne — les ré-exécutions ne coûtent
            rien). La valeur de la famille combine deux distances, toutes deux en configuration par
            mission :
          </p>
          <List>
            <li>
              <strong>distance à la baseline</strong>{' '}
              <code className="font-mono">1 − cos(canal, centroïde organique-FR)</code> — à quel point
              le canal se lit loin d'un panier de médias français légitimes
              (<code className="font-mono">embedding_baseline_channels</code>) ;
            </li>
            <li>
              <strong>proximité à l'adversaire</strong>{' '}
              <code className="font-mono">max_i cos(canal, adversaire_i)</code> — à quel point il se
              lit comme un canal adverse documenté
              (<code className="font-mono">embedding_adversary_channels</code>).
            </li>
          </List>
          <p>
            La valeur est une somme pondérée bornée, clampée à [0, 1], avec les distances
            contributrices et l'identifiant de l'adversaire le plus proche préservés dans le bloc de
            preuve du canal — de sorte qu'un classement piloté par (f) soit justifiable depuis le seul
            dossier (ex. « se lit comme @X, @Y, @Z — tous des canaux adverses documentés — et à 0.85
            de la baseline de la presse française »). La famille <strong>se dégrade gracieusement</strong> :
            si les embeddings ou les ancres baseline/adversaire de la mission sont indisponibles, (f)
            est simplement absente et le score structurel est renvoyé inchangé. C'est un signal de{' '}
            <em>corroboration indépendant de la sévérité</em>, pas un filtre : il peut aider un canal à
            franchir la gate multi-source (§3.2) mais n'en exclut jamais un.
          </p>
          <Note>
            <strong>Bouton de calibration.</strong> Les listes d'ancres baseline/adversaire et les
            poids de distance sont calibrés contre la piste de validation (§8.3), et non fixés dans le
            code comme vérité-terrain. Les ancres actuelles sont une amorce ; le chemin de montée en
            puissance est de les sourcer depuis le corpus de baseline organique-FR
            (<code className="font-mono">data/eval/baseline_organic_fr.json</code>) plutôt que depuis
            une poignée de handles codés en dur.
          </Note>
        </SubSection>
      </Section>

      <Section title="4. Tiers d'attribution">
        <Table
          head={['Tier', 'Revendication', 'Preuve', 'Posture']}
          rows={[
            [
              'T1 — Diffusion observable',
              'Premier canal de seeding visible, forward-hubs, forme de fan-out',
              'Données de canal public MTProto + reconstruction de graphe',
              <strong>Livrable primaire</strong>,
            ],
            [
              'T2 — Récurrence comportementale',
              'Mêmes canaux/motifs à travers les épisodes, corroboration multi-famille',
              'Agrégation multi-épisode + la gate multi-source (§3.2)',
              <strong>Livrable secondaire</strong>,
            ],
            [
              'T3 — Attribution monde-réel',
              'Une personne, une organisation, un État, un sponsor',
              'Corroboration hors-plateforme',
              <strong>HORS PÉRIMÈTRE — jamais revendiqué par ce système</strong>,
            ],
          ]}
        />
        <p>
          L'assignation de tier est mécanique et auditable : un canal est étiqueté T2 uniquement
          lorsque la gate multi-source est atteinte ; sinon T1. Toute sortie confondant les tiers est
          un défaut. « Premier canal de seeding visible » signifie premier visible{' '}
          <em>au sein du corpus Telegram</em> — jamais « originateur » au sens fort.
        </p>
        <SubSection title="4bis. Découverte d'épisodes">
          <p>
            Un <strong>épisode</strong> est un événement de diffusion cohérent — un ensemble de canaux
            propageant le même matériel sur une fenêtre bornée. En v0.2.0 les épisodes étaient un
            registre maintenu à la main (un unique exemple documenté) ; le pipeline de découverte
            existait mais n'était jamais câblé à la sortie. En v0.3.0 les épisodes sont{' '}
            <strong>découverts automatiquement</strong> (<code className="font-mono">scripts/mine_episodes.py</code>)
            et fusionnés avec toute entrée curée
            (<code className="font-mono">src/dossier/evidence.py::load_episodes</code>), de sorte que
            le registre n'est plus un goulot d'étranglement.
          </p>
          <p>
            La découverte pivote sur des artefacts de diffusion partagés — médias réutilisés
            (<code className="font-mono">file_unique_id</code>), URL en correspondance exacte, et
            republication par forward — et étiquette chaque cluster candidat par TF-IDF sur son
            vocabulaire. Chaque épisode découvert porte en plus un{' '}
            <strong>bloc sémantique « pourquoi »</strong> (<code className="font-mono">pourquoi_embedding</code>)
            dérivé des embeddings de la famille (f) : cohésion intra-cluster, distance moyenne du
            cluster à la baseline organique-FR, et les principaux outliers du cluster. C'est
            exactement la justification par épisode dont un analyste a besoin pour lire un cluster
            découvert comme un événement coordonné plutôt qu'une coïncidence. La découverte n'affirme
            jamais un tier au-delà de ce que la gate par canal (§3.2) supporte.
          </p>
        </SubSection>
      </Section>

      <Section title="5. Limites de couverture (divulguées dans chaque sortie)">
        <Note>
          « Ce dossier observe uniquement la couche d'ensemencement Telegram. Une opération atteignant
          la France principalement via d'autres plateformes sans étape Telegram ne sera PAS détectée. »
        </Note>
        <p>
          Ce callout est un champ obligatoire et validé de chaque bundle exporté. Limites permanentes
          additionnelles :
        </p>
        <List>
          <li>
            Le graphe est une <strong>projection partielle</strong> : les relais cross-plateformes,
            les captures d'écran, les médias re-recadrés et les canaux privés sont invisibles.
          </li>
          <li>
            Les canaux sous blocage légal français sont invisibles à un compte collecteur ancré dans
            l'UE ; cet angle mort est accepté pour le PoC (ces canaux sont déjà actionnés par le levier
            judiciaire).
          </li>
          <li>
            La détection de suppression s'exécute par diff de polling (≤ 15 min de latence sur les
            canaux chauds) — aucun firehose de plateforme n'existe.
          </li>
          <li>
            Les callouts par mission étendent cette divulgation (ex. la mission GAN énonce que
            l'empreinte mesurée est l'empreinte <em>observable-sur-Telegram</em>, jamais l'empreinte
            totale — §6.2).
          </li>
        </List>
      </Section>

      <Section title="6. Architecture multi-mission">
        <p>
          Idéfix est <strong>un moteur, N missions</strong>. Une mission est une{' '}
          <em>configuration</em> (univers de sources, lexique, poids de ciblage, profil de scoring,
          dashboard, export), jamais un fork de code. Les familles structurelles (b)/(c)/(d) sont
          agnostiques au thème ; les missions diffèrent par les seeds, lexiques, signaux de
          pertinence, poids, et toute famille de score additionnelle. La contrainte
          sévérité-pas-inclusion du §3.3 est générique et lie chaque mission.
        </p>
        <SubSection title="6.1 Mission par défaut — désinformation coordonnée ciblant la France (russosphere)">
          <p>
            La configuration décrite au §3 : portée thématique restreinte aux narratifs attaquant
            l'image, l'intégrité ou la souveraineté de la France ; signal de pertinence = ciblage-
            France cross-langue ; sorties armées vers VIGINUM/Arcom.
          </p>
        </SubSection>
        <SubSection title="6.2 Mission pilote — empreinte informationnelle GAN (gan)">
          <p>
            Mesure l'<strong>empreinte informationnelle observable-sur-Telegram</strong> du Groupe
            Aéronaval français (<em>Charles de Gaulle</em>) avec un objectif de minimisation OPSEC, et
            détecte la capture/amplification adverse de cette empreinte.
          </p>
          <List>
            <li>
              <strong>Tous les scores spécifiques à la mission sont nommés{' '}
              <code className="font-mono">telegram_*</code></strong> — un verrou de périmètre délibéré :
              le système mesure l'empreinte observable-sur-Telegram, jamais l'empreinte totale (AIS,
              fuites de fitness-trackers, X, presse, satellite et ship-spotting peuvent alimenter
              Telegram mais ne sont pas collectés).
            </li>
            <li>
              Familles additionnelles : <code className="font-mono">telegram_visibility</code>,{' '}
              <code className="font-mono">telegram_velocity</code>,{' '}
              <code className="font-mono">telegram_source_diversity</code>,{' '}
              <code className="font-mono">telegram_disclosure_precision</code> (rubrique EEFI graduée
              sur le texte des messages — les grades de sévérité sont une décision de calibration
              détenue par le sponsor, amorcés v0), <code className="font-mono">telegram_propagation</code>,{' '}
              <code className="font-mono">telegram_adverse_attention</code>. Les familles structurelles
              (b)/(c)/(d) sont conservées à poids réduit.
            </li>
            <li>
              <strong>Prior de crédibilité neutre :</strong> les canaux discutant d'un actif ami ne
              portent aucune présomption de suspicion (pas d'assignation de suspect-prior dans cette
              mission).
            </li>
            <li>
              Tiers : T1 = empreinte observable + premier divulgateur ; T2 = moniteur récurrent ; T3
              hors périmètre, comme partout.
            </li>
          </List>
        </SubSection>
        <SubSection title="6.3 Mission planifiée — diffusion des messages DIRCOM (dircom_minarm)">
          <p>
            Trace la réutilisation, la transformation et la distorsion de la communication officielle
            DIRCOM (ministère des Armées) sur Telegram. En v0.3.0 la mission est{' '}
            <strong>packagée</strong> (<code className="font-mono">src/missions/dircom_minarm/</code> :
            lexique, univers de sources, profils de scoring/dashboard/export, ancres sémantiques) et
            auto-découverte par le registre, mais maintenue à{' '}
            <code className="font-mono">implemented=False</code> de sorte qu'elle apparaisse dans le
            switcher tout en refusant la sélection live tant qu'un crawl ne l'a pas peuplée. Listée
            pour la transparence de la feuille de route ; basculer le flag l'active dès que les données
            existent. Au-delà des trois missions nommées, une mission{' '}
            <code className="font-mono">france_ukraine</code> (narratifs ciblant la France dans le
            conflit ukrainien) est également implémentée sous le même moteur.
          </p>
        </SubSection>
      </Section>

      <Section title="7. Relation avec MisinfoTeleGraph — le GNN comme cible ultérieure">
        <p>
          La version 0.1.0 de ce document décrivait un réseau de neurones de graphe GraphSAGE+LSTM
          (réplique de MisinfoTeleGraph, arXiv:2506.22529) comme cœur de détection.{' '}
          <strong>Ce n'est pas ce qui est livré, et ce document ne le revendique plus.</strong>
        </p>
        <List>
          <li>
            <strong>Livré aujourd'hui :</strong> le score de suspicion explicable du §3. Il a été
            choisi délibérément : à l'échelle de corpus du PoC, un GNN supervisé est prématuré (aucun
            ensemble gold équilibré au niveau canal n'existe), et un score explicable est auditable de
            bout en bout — une exigence pour l'usage institutionnel.
          </li>
          <li>
            <strong>Cible ultérieure :</strong> le classifieur GraphSAGE+LSTM reste la feuille de
            route une fois que (i) l'ingestion passe à l'échelle et (ii) un ensemble d'annotation
            équilibré au niveau canal existe. Les familles de score du §3 sont conçues pour devenir
            les features d'entrée de ce modèle ; la méthodologie de MisinfoTeleGraph informe le schéma
            de graphe et le design d'évaluation aujourd'hui, pas le classifieur déployé.
          </li>
          <li>
            L'étiquetage faible par message contre des corpus de fact-check a été piloté puis{' '}
            <strong>abandonné</strong> (le gold par message était ~97 % « vrai » — non informatif) ;
            la supervision, quand elle viendra, sera au niveau canal.
          </li>
        </List>
        <p>
          Les seuils de détection de coordination (VIGINUM D3lta) et les rôles de cascade Bridge-Score
          cités en 0.1.0 survivent sous forme adaptée à l'intérieur des familles (c) et (b)
          respectivement.
        </p>
      </Section>

      <Section title="8. État de validation (divulgation honnête)">
        <p>
          Le score a été soumis à une batterie de falsification désormais{' '}
          <strong>calculée sur des scores réels</strong> (russosphere, 3 699 canaux scorés
          matérialisés dans <code className="font-mono">channel_scores</code> ; graphe de forward 3 680
          nœuds / 6 889 arêtes). Tous les chiffres ci-dessous sont <strong>reproductibles</strong> —
          committés sous <code className="font-mono">docs/metrics/</code> et régénérables via{' '}
          <code className="font-mono">scripts/prep_eval_inputs.py</code> +{' '}
          <code className="font-mono">scripts/eval_*.py</code>. Audit complet :{' '}
          <code className="font-mono">docs/scientific-audit.md</code>. Nous publions ce qui est{' '}
          <strong>prouvé</strong>, ce qui est <strong>faible</strong>, et ce qui n'est{' '}
          <strong>pas encore calculable</strong> — pas une revendication marketing.
        </p>
        <Table
          head={['Expérience', 'Question', 'Verdict (calculé)', 'Force']}
          rows={[
            [
              '1 — Ablation de centralité [Spearman, 1904 ; Fawcett, 2006]',
              'Le score est-il juste de la centralité déguisée ?',
              <><strong>PASS — non.</strong> Spearman(suspicion, in-degree)=0.667, vecteur propre=0.535, forward-influence=0.424, activité=0.317 ; Jaccard@50 ≤ 0.05 (in-degree 0.020, vecteur propre 0.053). Seuils de falsification (Spearman&gt;0.90 OU Jaccard@50&gt;0.80) <strong>non approchés</strong>. → <code className="font-mono">docs/metrics/ablation_centrality.json</code></>,
              <strong>Forte</strong>,
            ],
            [
              '2 — Récupération d’épisode connu (gold externe)',
              'Récupère-t-il une opération documentée ?',
              <><strong>FAIBLE.</strong> Contre un gold <strong>externe, non circulaire</strong> (<code className="font-mono">gold_episode_dugin.json</code>) : seulement 3/12 canaux gold sont dans le corpus ; recall@50=0.167 (hasard 0.162, ×12.35), rang médian 50. Caveat : le gold est <strong>hypothétique</strong> (pas une vraie liste VIGINUM) et l'overlap est minuscule. → <code className="font-mono">docs/metrics/episode_recovery.json</code></>,
              <strong>Faible</strong>,
            ],
            [
              '3 — Discriminant hostile vs organique',
              'Sépare-t-il la coordination hostile de la viralité organique ?',
              <><strong>MITIGÉ, non stressé.</strong> Parmi 446 canaux coordonnés : Spearman(suspicion, ancrage-adverse)=<strong>0.765</strong> (dominant), coordination seule=0.253, base structurelle=0.488. <strong>0 candidat organique</strong> dans le corpus (amorcé sur l'adversaire) → le discriminant n'est pas stressé. → <code className="font-mono">docs/metrics/discriminant_organic.json</code></>,
              <strong>Faible</strong>,
            ],
            [
              'f — Discrimination par embedding [Rousseeuw, 1987 ; Fawcett, 2006]',
              'La famille (f) sépare-t-elle organique-FR de scoré ?',
              <><strong>FAIBLE + caveat de méthode.</strong> ROC-AUC=<strong>0.506</strong> (≈ hasard), silhouette 0.003. Mais le test embedde les <strong>usernames seuls</strong>, pas le contenu des messages comme le fait la famille (f) déployée — donc il ne <strong>teste pas</strong> (f) telle que livrée. Recommandation : ré-encoder sur le contenu. → <code className="font-mono">docs/metrics/embedding_discrimination_russosphere.json</code></>,
              <strong>Faible (mal spécifiée)</strong>,
            ],
            [
              'Significativité (ROC-AUC vs gold, permutation, calibration)',
              'Le score rigoureux est-il significatif vs gold ?',
              <><strong>NON CALCULABLE.</strong> <code className="font-mono">channel_gold</code> = 12 positifs / <strong>0 négatif</strong> (pas de corpus organique) → ROC-AUC indéfini. Bloqué par le même écart que l'Exp 3.</>,
              <strong>Bloquée</strong>,
            ],
          ]}
        />
        <p>
          <strong>Revendication permanente, calibrée sur la preuve :</strong> le système est défendable
          comme <strong>démonstrateur T1</strong> — structure de diffusion observable,{' '}
          <strong>démontrablement séparable de la centralité brute</strong> (Exp 1, calculée) —{' '}
          <strong>pas</strong> comme un détecteur de manipulation validé. Deux écarts, tous deux du
          travail d'annotation humaine, bornent encore la revendication : (1) une <strong>vraie</strong>{' '}
          liste de seed externe pour un épisode documenté (le gold actuel est hypothétique, 3/12
          in-corpus) ; (2) un corpus de <strong>coordination française organique</strong> (la classe
          négative — actuellement 0, ce qui bloque l'Exp 3 et le ROC-AUC de significativité). Tant
          qu'ils ne sont pas comblés, aucune sortie n'est présentée comme plus que T1/T2 selon §4.
        </p>
        <SubSection title="8.2 Analytics vs embedding (calculé)">
          <p>
            Détection de communautés (Leiden [Traag et al., 2019]) sur russosphere, deux pistes
            (chiffres complets : <code className="font-mono">docs/metrics/analytics_vs_embedding.json</code> ;
            discussion : <code className="font-mono">docs/analytics-vs-embedding.md</code>) :
            intra-cohésion 0.6709 → <strong>0.7049 (+5.1 %)</strong>, silhouette [Rousseeuw, 1987]
            −0.274 → 0.021, <strong>modularité [Newman, 2006] 0.7547 → 0.6301</strong>, communautés
            conservées 27 → 17, accord des partitions <strong>NMI 0.887 / ARI 0.528</strong>{' '}
            [Danon et al., 2005 ; Hubert &amp; Arabie, 1985]. Le <strong>trade-off</strong> cohésion↑ /
            modularité↓ est attendu, pas une régression : les arêtes sémantiques{' '}
            <code className="font-mono">EMB_SIM</code> traversent les communautés du graphe de liens
            (voir <code className="font-mono">docs/analytics-vs-embedding.md</code>).
          </p>
        </SubSection>
        <SubSection title="8.3 Piste de validation non circulaire (statut)">
          <p>
            Les <em>instruments</em> sont construits <strong>et s'exécutent désormais</strong> sur des
            scores réels ; ce qui reste, ce sont de <strong>vraies données annotées</strong> :
          </p>
          <List>
            <li>
              <strong>Baseline organique-FR externe</strong>{' '}
              (<code className="font-mono">scripts/bootstrap_baseline.py</code> →{' '}
              <code className="font-mono">data/eval/baseline_organic_fr.json</code>) : 98 canaux FR
              légitimes (ancres pour la famille (f)). Ce n'est <strong>pas</strong> un corpus de
              coordination : il fournit des ancres, pas les <em>négatifs</em> organiques dont l'Exp 3
              / la significativité ont besoin.
            </li>
            <li>
              <strong>Gold d'épisode externe</strong>{' '}
              (<code className="font-mono">data/eval/gold_episode_*.json</code>, schéma{' '}
              <code className="font-mono">ExternalGoldEpisode</code>,{' '}
              <code className="font-mono">excluded_from_scorer_inputs=True</code>) :{' '}
              <strong>hypothétique</strong>, 3/12 in-corpus — à remplacer par une vraie liste sourcée
              VIGINUM.
            </li>
            <li>
              <strong>Test de discrimination par embedding</strong>{' '}
              (<code className="font-mono">scripts/eval_embedding_discrimination.py</code>) : s'exécute
              (ROC-AUC 0.506) mais mal spécifié (usernames, pas contenu) — à corriger avant de tirer
              des conclusions.
            </li>
            <li>
              <strong>Dérive temporelle</strong>{' '}
              (<code className="font-mono">scripts/compare_snapshots.py</code>) : relit les instantanés
              pour le contrôle longitudinal (§9).
            </li>
          </List>
          <p>
            Bilan honnête : la falsification bon marché (Exp 1){' '}
            <strong>passe sur des chiffres réels et reproductibles</strong> ; les revendications plus
            fortes restent bloquées par la classe négative organique manquante et un vrai gold externe.
          </p>
        </SubSection>
        <SubSection title="Cadre d'évaluation">
          <p>
            Le système est évalué comme un <strong>outil d'investigation</strong>, pas comme un
            classifieur : précision top-K sur les canaux prioritaires, gain temporel sur
            l'identification par fact-checkers publics, qualité de reconstruction de la carte de
            forward/seeding, et utilité analyste (temps de triage, stabilité et justifiabilité des
            explications). Il n'est jamais évalué par « persuasion mesurée » ou « influence prouvée ».
          </p>
        </SubSection>
      </Section>

      <Section title="9. Infrastructure et traitement des données (tel qu'implémenté)">
        <List>
          <li>
            <strong>Pipeline hors-ligne uniquement.</strong> Des scripts Python exécutent la chaîne
            complète (ingestion → normalisation → arêtes → tag → score → découverte d'épisodes →
            analyse → export) ; l'interface analyste est un <strong>bundle web statique</strong> lisant
            du JSON précalculé — pas de backend live, pas de détection côté serveur au moment de la
            requête. Le bundle est construit et servi sur Vercel ; une étape de prebuild
            (<code className="font-mono">webapp/scripts/pull-snapshots.mjs</code>) fige les instantanés
            de communauté dans le bundle, de sorte que le navigateur ne contacte jamais la base.
          </li>
          <li>
            <strong>Pile :</strong> PostgreSQL (managé Supabase) pour le magasin de
            messages/arêtes/scores, graphe NetworkX/igraph en mémoire. Pas de serveur de base de
            graphe, pas d'orchestration de conteneurs, pas de bus de messages — corrections des
            revendications Neo4j/Docker Compose de la version 0.1.0.
          </li>
          <li>
            <strong>Embeddings :</strong> inférence <code className="font-mono">sentence-transformers</code>{' '}
            locale (MiniLM multilingue, 384-dim), déterministe et mise en cache hors-ligne (clé de
            cache = <code className="font-mono">sha256(model‖text)</code>), de sorte que la famille (f)
            et le bloc d'épisode sémantique ne coûtent rien en ré-exécution et ne requièrent aucune API
            payante.
          </li>
          <li>
            <strong>Magasin d'instantanés (bidirectionnel) :</strong> les instantanés de communauté
            sont poussés vers une table Supabase protégée
            (<code className="font-mono">community_snapshots</code>, accès service-role) et{' '}
            <strong>relus</strong> par le pipeline (<code className="font-mono">pull_snapshot</code>)
            pour le contrôle de dérive temporelle du §8.3 — ils ne sont plus en écriture seule.
          </li>
          <li>
            <strong>Ingestion :</strong> Telegram MTProto (client Hydrogram), canaux publics
            uniquement, backfill d'historique plus polling à paliers, discipline FLOOD_WAIT, unique
            compte dédié en lecture seule. Pas de collecte grise, pas de scraping hors-ToS, pas de
            désanonymisation. Les identifiants des membres de canal ne sont pas collectés.
          </li>
          <li>
            <strong>Secrets :</strong> la session Telegram et les identifiants API sont des dépendances
            d'exécution et sont scrubbés (par clé et par valeur) de chaque export.
          </li>
          <li>
            <strong>Posture de conformité officielle :</strong> base légale, rétention, suppression et
            obligations de contrôle d'accès sont détenues par le cadre officiel du sponsor. Elles ne
            sont pas un flux de backlog produit Idéfix autonome. Idéfix ne conserve que les hooks
            techniques demandés pour l'exploitation officielle : minimisation, classification d'export,
            métadonnées d'audit, scrubbing des secrets, événements de suppression/couverture lorsque
            requis, et champs de chaîne de custody.
          </li>
        </List>
      </Section>

      <Section title="10. Gouvernance">
        <List>
          <li>
            Cette méthodologie est publiée 3 mois avant toute sortie de détection live (exigence de
            résistance EIP). Les bundles exportés embarquent un hash de ce document, de sorte que toute
            révision de méthodologie soit détectable dans la chaîne de custody.
          </li>
          <li>
            <strong>Ratio symétrique</strong> (part adverse-liée vs organique de la population scorée)
            est calculé à chaque run de scoring complet et publié avec le bundle (§3.3).
          </li>
          <li>
            <strong>Corroboration multi-source</strong> est imposée structurellement : pas de label
            T2, et pas de tier de sévérité escaladé, sans ≥ 2 familles de score indépendantes
            déclenchées (§3.2).
          </li>
          <li>
            <strong>Arm-only :</strong> les sorties vont aux destinataires institutionnels désignés
            uniquement — jamais aux plateformes, jamais au public, jamais aux candidats ou à la presse.
          </li>
          <li>
            <strong>Vocabulaire à tiers</strong> (§4) est obligatoire dans chaque sortie ; les
            revendications T3 sont un défaut rapportable.
          </li>
          <li>
            L'état de validation (§8) est livré avec la méthodologie et est mis à jour à chaque
            ré-exécution de la batterie de falsification ; les revendications sont bornées par
            l'expérience pertinente la plus faible.
          </li>
        </List>
      </Section>

      <Section title="11. Références">
        <p>
          Chaque choix méthodologique est ancré dans la littérature. Bibliographie complète (formatée,
          avec DOIs/arXiv) : <strong><code className="font-mono">docs/references.md</code></strong>.
          Audit indépendant de l'ancrage (cité vs implémenté vs non cité) :{' '}
          <strong><code className="font-mono">docs/scientific-audit.md</code></strong>.
        </p>
        <p>
          Ancres clés : détection de communautés — Leiden [Traag, Waltman &amp; van Eck, 2019] ;
          modularité [Newman, 2006]. Qualité de cluster/partition — silhouette [Rousseeuw, 1987] ; NMI
          [Danon et al., 2005] ; ARI [Hubert &amp; Arabie, 1985]. Statistiques — Benjamini-Hochberg FDR
          [1995] ; combinaison de Stouffer [1949] ; bootstrap [Efron, 1979] ; tests de permutation
          [Good, 2000] ; ROC-AUC [Fawcett, 2006]. NLP — TF-IDF [Spärck Jones, 1972] ; Sentence-BERT
          [Reimers &amp; Gurevych, 2019] ; MiniLM [Wang et al., 2020]. Domaine — Bridge Score
          [arXiv:2411.05922] (famille b) ; comportement inauthentique coordonné [Pacheco et al., 2021 ;
          Giglietto et al., 2020] ; VIGINUM D3lta (famille c, piste texte différée) ; MisinfoTeleGraph
          [arXiv:2506.22529] (GNN, cible ultérieure, §7).
        </p>
      </Section>
    </DocPage>
  )
}
