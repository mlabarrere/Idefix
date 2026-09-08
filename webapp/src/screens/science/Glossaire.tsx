// Glossaire — transcription de docs/glossary.md.
import { DocPage, Section, Table, Note } from './docs-ui'

export function Glossaire() {
  return (
    <DocPage
      title="Glossaire"
      subtitle="Vocabulaire de référence pour tous les livrables (PRD, architecture, stories, dossiers). À aligner avec VIGINUM / EEAS / OSCE — pas « fake news »."
      source="docs/glossary.md"
    >
      <Note>
        <strong>2026-05-26 — projet re-scopé Telegram-only</strong> (X abandonné, paywall API). Les
        primitives ci-dessous ont été reconverties : <em>cascade retweet multi-saut → chaîne de
        forwards profondeur-1 + chaînes inter-canaux sur fenêtres multi-jours</em> ;{' '}
        <em>compte → canal</em> ; <em>Community Notes retiré</em>. Voir{' '}
        <code className="font-mono">_bmad-output/planning-artifacts/scope-change-telegram-only-2026-05-26.md</code>.
      </Note>

      <Section title="Concepts d'analyse">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>Épisode (de revendication)</strong>,
              <>Unité d'analyse fondamentale du système. Une revendication documentée + ses variants sémantiques tracés dans le temps. Le système ne cherche jamais « la fausseté en général » — seulement des familles de revendications documentées et leurs variants.</>,
            ],
            [
              <><strong>Chaîne de forwards</strong> <em>(forward chain)</em></>,
              <>Primitive de propagation Telegram : étoile de <strong>profondeur-1</strong> (chaque forward pointe directement vers le message d'origine) avec délais à queue lourde s'étalant sur des jours. Remplace la cascade retweet de l'ère X. L'unité analytique est le <em>fan-out à profondeur 1 depuis un canal-source</em> + les chaînes de re-forward inter-canaux, observés sur fenêtres multi-jours.</>,
            ],
            [
              <strong>Cascade</strong>,
              <>Terme générique conservé pour l'arbre de propagation observé d'une revendication. Sur Telegram, reconstruit à partir des <strong>forwards</strong> (et replies dans les groupes de discussion liés), pas des reposts/quotes X.</>,
            ],
            [
              <strong>Variant sémantique</strong>,
              <>Formulation alternative d'une même revendication (paraphrase, traduction, recontextualisation, recadrage d'image). Identifié via matching multilingue (MuMiN + LaBSE).</>,
            ],
            [
              <strong>Coordination</strong>,
              <>Convergence de plusieurs signaux comportementaux faibles (texte quasi-identique inter-canaux, co-URL, co-forwarding, sync temporelle multi-jours, réutilisation d'image/vidéo, motifs de mention/admin partagé) à travers un ensemble de canaux, au-delà du hasard. <em>Aucun signal seul</em> n'est fiable — c'est l'alignement multiplex qui compte.</>,
            ],
            [
              <strong>Graphe hétérogène dynamique</strong>,
              <>Nœuds : <em>channels, messages, URLs, media, claims</em>. Arêtes : forward (avec <code className="font-mono">delay_seconds</code>), reply, mention, co-share de domaine, similarité de texte au-dessus d'un seuil, réutilisation d'image/vidéo, sync temporelle, co-forwarding inter-canaux. Fenêtré dans le temps (multi-jours) ; communautés recalculées dynamiquement. <em>L'arête channel↔domaine (sites Pravda/Doppelganger cités par les canaux) est conservée — couche d'infra adverse P2, pas une 2ᵉ plateforme.</em></>,
            ],
          ]}
        />
      </Section>

      <Section title="Rôles dans la cascade (archétypes Telegram)">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <><strong>Seeding-source channel</strong> <em>(canal-source de seeding)</em></>,
              <>Canal qui origine récurremment un narratif tôt, avant le fan-out. Analog Telegram de l'<em>initiator</em> ; cible primaire d'alerte précoce. Rarement = originateur au sens fort.</>,
            ],
            [
              <strong>Forward-hub</strong>,
              <>Canal dont le contenu est forwardé largement (fort fan-out à profondeur 1). Le plus visible — pas nécessairement le plus important.</>,
            ],
            [
              <><strong>Cross-channel bridge</strong> <em>(pont inter-canaux)</em></>,
              <>Canal qui transporte un narratif d'une communauté de canaux à une autre. <strong>Souvent stratégiquement plus important que le forward-hub à fort volume.</strong> Cible primaire de la cartographie de coordination.</>,
            ],
            [
              <strong>Reactivator</strong>,
              <>Canal qui réinjecte périodiquement un narratif ancien dans des conversations fraîches. Indicateur de récidive.</>,
            ],
            [
              <strong>Superpropagateur</strong>,
              <>Canal qui apparaît récurremment tôt dans les chaînes de forwards de contenu peu crédible. Identifié par la <strong>forward-influence + récurrence de seeding</strong> (analog Telegram de la métrique <em>Influence</em> de DeVerna et al. 2024), pas par nombre d'abonnés.</>,
            ],
          ]}
        />
      </Section>

      <Section title="Métriques">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>Forward-influence</strong>,
              <>Forwards gagnés par du contenu peu crédible. Backbone de la famille de score 5.d (récidive inter-épisodes) ; analog Telegram de la métrique <em>Influence</em> (retweets gagnés) de DeVerna, Aiyappa, Pacheco, Bryden &amp; Menczer, <em>PLOS One</em> 2024. <em>Bat le nombre d'abonnés et les heuristiques type Bot Score.</em></>,
            ],
            [
              <strong>Rₜ narratif</strong>,
              <>Taux de reproduction effectif appliqué à un narratif (analogie épidémiologique). Sur Telegram, estimé sur fenêtres multi-jours ; estimation robuste exige plusieurs fenêtres de comparaison.</>,
            ],
            [
              <><strong>Top-K precision (priority channels)</strong></>,
              <>Des K canaux top-rankés sur un épisode historique, combien apparaissent dans le noyau de seeding/coordination identifié a posteriori. Métrique d'évaluation primaire.</>,
            ],
            [
              <><strong>Gain temporel</strong> <em>(temporal gain)</em></>,
              <>Heures/jours par lesquels l'alerte du POC précède l'identification publique par fact-checkers. Valeur ajoutée opérationnelle (capter la phase de <em>seeding</em>). <em>(Community Notes retiré — capteur X-only.)</em></>,
            ],
          ]}
        />
      </Section>

      <Section title="Cinq familles de score (P1)">
        <Table
          head={['#', 'Famille', 'Définition']}
          rows={[
            ['5.a', <strong>Claim proximity</strong>, <>Match sémantique à une revendication enregistrée. + sous-flag <em>authenticité de source vs. authenticité de revendication</em>.</>],
            ['5.b', <strong>Cascade role</strong>, <>Classification dans les 4 archétypes Telegram : seeding-source / forward-hub / cross-channel bridge / reactivator.</>],
            ['5.c', <strong>Coordination</strong>, <>Convergence multiplex de co-actions sur fenêtres multi-jours.</>],
            ['5.d', <strong>Cross-episode recidivism</strong>, <>Apparition précoce répétée à travers plusieurs épisodes ; opérationalisé via forward-influence + récurrence de seeding.</>],
            ['5.e', <strong>GenAI-origin probability</strong>, <>Audio cloning + deepfake video + LLM-text fingerprints (cible spécifiquement les modèles CopyCop).</>],
          ]}
        />
      </Section>

      <Section title="Tiers d'attribution">
        <Table
          head={['Tier', 'Nom', 'Ce qu’on prétend', 'Posture POC']}
          rows={[
            [<strong>T1</strong>, 'Diffusion observable', 'Premier canal-source visible, forward-hubs précoces, forme de fan-out', <strong>Livrable primaire</strong>],
            [<strong>T2</strong>, 'Récurrence comportementale', 'Mêmes comptes / motifs à travers les épisodes', <strong>Livrable secondaire</strong>],
            [<strong>T3</strong>, 'Attribution monde-réel', 'Une personne, une organisation, un État, un sponsor', <><strong>Hors périmètre</strong> — exige preuves hors-plateforme</>],
          ]}
        />
        <p>
          Tout livrable qui mélange les tiers est un défaut. Chaque dossier doit déclarer son tier.
        </p>
      </Section>

      <Section title="Tiers de sévérité (T1–T5)">
        <p>
          Échelle d'escalade opérationnelle (P3 CSIRT orchestration) — distincte des tiers
          d'attribution ci-dessus. Mapping public requis (NFR EIP-resistance). Changement de tier
          exige corroboration multi-source (≥ 3 signaux indépendants de ≥ 2 familles).
        </p>
      </Section>

      <Section title="Cadre légal &amp; institutionnel">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>VIGINUM</strong>,
              <>Service de vigilance et de protection contre les ingérences numériques étrangères. Créé 2021-07-13 sous le SGDSN. ~60 agents. Mandat : détecter et caractériser l'ingérence numérique <em>étrangère</em> du débat public français. <em>Le POC est conçu pour armer VIGINUM.</em></>,
            ],
            [
              <strong>Arcom</strong>,
              <>Autorité de régulation de la communication audiovisuelle et numérique. Coordinateur national au titre du DSA pour les plateformes désignées. 2ᵉ point d'atterrissage institutionnel de l'axiom #2.</>,
            ],
            [
              <strong>SGDSN</strong>,
              <>Secrétariat général de la défense et de la sécurité nationale. Tutelle de VIGINUM. Coordination interministérielle.</>,
            ],
            [
              <strong>FIMI</strong>,
              <><em>Foreign Information Manipulation and Interference</em>. Terminologie officielle EEAS/UE. À préférer à « disinformation » dans les livrables stakeholders.</>,
            ],
            [
              <strong>DSA</strong>,
              <>Digital Services Act (UE). Articles porteurs pour le POC : <strong>Art. 36</strong> (mécanisme de crise) et <strong>Art. 40</strong> (accès chercheurs / coordinateur national = Arcom pour la France).</>,
            ],
            [
              <strong>Loi anti-infox</strong>,
              <>Loi du 22 décembre 2018. Procédure judiciaire d'urgence (48 h) pour suspendre la diffusion de fausses informations en période électorale.</>,
            ],
            [
              <strong>Loi 2024-850</strong>,
              <>(25 juillet 2024) — Loi visant à prévenir les ingérences étrangères en France. Cadre légal de prévention en complément du dispositif anti-infox.</>,
            ],
            [
              <strong>CNIL</strong>,
              <>Commission nationale de l'informatique et des libertés. Données publiques = données personnelles. Le POC doit documenter base légale, durées de rétention, journal d'accès, règles de minimisation.</>,
            ],
            [
              <strong>Blackout 44 h</strong>,
              <>Silence médiatique imposé par la loi électorale française dans les 44 heures précédant un scrutin. Fenêtre opérationnelle critique pour le POC (mode SOAR dédié pré/pendant/post-blackout). C'est ce qui a défait Macron Leaks 2017.</>,
            ],
          ]}
        />
      </Section>

      <Section title="Frameworks techniques">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>DISARM</strong>,
              <>Taxonomie open-source de TTPs (Tactics, Techniques, Procedures) d'opérations d'influence. Modélisé sur MITRE ATT&amp;CK. <em>DISARM Red</em> = côté attaquant ; <em>DISARM Blue</em> = côté défense. Le POC émet ses détections en TTP IDs DISARM Red et structure ses playbooks SOAR en DISARM Blue.</>,
            ],
            [
              <strong>STIX 2.1 / TAXII 2.1</strong>,
              <>Standards OASIS de sérialisation et transport de cyber-threat-intelligence (juin 2021). Le POC emballe ses preuves en STIX. <em>Pas d'extension OASIS formelle pour le disinfo/FIMI à ce jour — opportunité de standardisation.</em></>,
            ],
            [
              <strong>TLP</strong>,
              <><em>Traffic Light Protocol</em>. Marquage de partage d'information (WHITE/GREEN/AMBER/RED). Tous les packages de preuves du POC sont TLP-marqués.</>,
            ],
            [
              <strong>Chaîne de custody</strong>,
              <>Preuve cryptographique de l'intégrité d'une pièce et de la séquence de ses détenteurs. Requis pour les évidences admissibles en procédure judiciaire (loi anti-infox).</>,
            ],
            [
              <strong>MuMiN</strong>,
              <>Dataset multilingue de matching de revendications (arxiv 2202.11684 ; SIGIR 2022). 21,5 M tweets, 12 914 revendications fact-checkées, 41 langues incluant le français. Brique du sous-système P1.a.</>,
            ],
            [
              <strong>LaBSE</strong>,
              <><em>Language-agnostic BERT Sentence Embeddings</em>. Embeddings utilisés par MuMiN pour le matching multilingue.</>,
            ],
            [
              <strong>MAVOS-DD</strong>,
              <>Premier benchmark open-set multilingue audio-vidéo de détection de deepfake (arxiv 2505.11109, 2025). 8 langues, 250+ heures. Base du sous-système P1.e. <em>SOTA dégrade sur générateurs inconnus — bandes de confiance + flag « générateur inconnu » obligatoires.</em></>,
            ],
            [
              <strong>Community Notes</strong>,
              <>Système d'annotation crowdsourcé de X. <strong>Retiré du périmètre dans le re-scope Telegram-only du 2026-05-26</strong> (capteur X-only, aucun équivalent Telegram). Les labels faibles / validation a posteriori proviennent désormais des <strong>corpus de fact-checking</strong> (AFP Factuel, Les Décodeurs, CheckNews, 20 Minutes). Conservé ici comme référence historique.</>,
            ],
            [
              <strong>TGStat</strong>,
              <>Annuaire indexant 2,7 M+ canaux Telegram (filtres pays/langue/catégorie). Outil canonique de découverte de canaux (référencé par le Bellingcat Toolkit). Sert de couche de discovery : seed depuis le DFRLab Pravda Dashboard → expansion via « canaux similaires » → filtre FR → validation manuelle opérateur.</>,
            ],
            [
              <strong>FLOOD_WAIT</strong>,
              <>Réponse de limitation de débit MTProto (champ <code className="font-mono">seconds</code> à respecter). Telegram ne publie pas de plafonds exacts. Discipline FLOOD_WAIT = équivalent Telegram de la gestion des rate-limit headers X.</>,
            ],
            [
              <strong>SOAR</strong>,
              <><em>Security Orchestration, Automation and Response</em>. Playbooks automatisés de réponse aux incidents. Modèle adopté pour P3.</>,
            ],
          ]}
        />
      </Section>

      <Section title="Adversaires (catalogue P2 fermé pour MVP)">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <><strong>Doppelganger</strong> <em>(RU)</em></>,
              <>Cloned French/European media domains + amplification bot. Meta déc. 2022 (Struktura + Social Media Agency) ; VIGINUM juin 2023.</>,
            ],
            [
              <><strong>Media Brands / RRN</strong> <em>(RU)</em></>,
              <><em>Reliable Russian News</em>. Création de marques médiatiques inauthentiques.</>,
            ],
            [
              <><strong>Undercut</strong> <em>(RU)</em></>,
              <>Un des « cinq IMSs » canonisés par EU DisinfoLab. Méthodologie moins documentée.</>,
            ],
            [
              <><strong>Storm-1516</strong> <em>(RU)</em></>,
              <>Désignation Microsoft Threat Intelligence. 100+ sites fake news + deepfakes vidéo. Rapport VIGINUM mai 2025 (modus operandi).</>,
            ],
            [
              <><strong>Matriochka / Operation Overload</strong> <em>(RU)</em></>,
              <>Opération <em>target-the-defender</em> qui noie les fact-checkers et journalistes. Rapport SGDSN/VIGINUM juin 2024.</>,
            ],
            [
              <><strong>CopyCop</strong> <em>(RU)</em></>,
              <>Recorded Future mars 2024. 300+ sites mi-2025. LLM-generated, impersonates médias français. Fingerprint : <code className="font-mono">dolphin-2.9-llama3-8b</code> et <code className="font-mono">Llama-3-8B-Lexi-Uncensored</code> fine-tunés sur médias d'État russes.</>,
            ],
            [
              <><strong>Cluster IUVM</strong> <em>(IR)</em></>,
              <>International Union of Virtual Media. Surface limitée ; liée à la position française sur Israël.</>,
            ],
            [
              <><strong>APT28 / GRU Unit 26165</strong> <em>(RU)</em></>,
              <>Cyber + leak ops. Attribution officielle française des Macron Leaks 2017. Convention de phrasing : <em>« matches tradecraft of GRU Unit 26165 (APT28) »</em>.</>,
            ],
          ]}
        />
      </Section>

      <Section title="Acteurs institutionnels alliés">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>EEAS StratCom Task Force</strong>,
              <>Service européen d'action extérieure. Opère EUvsDisinfo. Publie le rapport annuel FIMI Threats (4ᵉ édition mars 2026 : 540 incidents en 2025).</>,
            ],
            [
              <><strong>NATO StratCom CoE</strong> <em>(Riga)</em></>,
              <>Steward du framework DISARM côté OTAN.</>,
            ],
            [
              <><strong>Hybrid CoE</strong> <em>(Helsinki)</em></>,
              <>Centre d'excellence européen contre les menaces hybrides (EU + OTAN). Co-auteur des standards DISARM-FIMI.</>,
            ],
            [
              <strong>EU DisinfoLab</strong>,
              <>ONG bruxelloise. Maintient le hub Doppelganger et la cartographie canonique des « cinq IMSs ».</>,
            ],
            [
              <><strong>DFRLab</strong> <em>(Atlantic Council)</em></>,
              <>Digital Forensic Research Lab. 1 000+ investigations depuis 2016. Délivre le G7 Rapid Response Mechanism Digital Transnational Repression Detection Academy.</>,
            ],
            [
              <strong>Stanford Internet Observatory</strong>,
              <><em>Démantelé juin 2024</em>. Cas d'école de la classe de NFR EIP-resistance du pilier P4.</>,
            ],
            [
              <><strong>UW CIP</strong> <em>(Center for an Informed Public, U. Washington)</em></>,
              <>Bras nord survivant de l'ancien EIP.</>,
            ],
            [
              <strong>Sciences Po médialab</strong>,
              <>Partenaire académique français potentiel. Manon Berriche est co-autrice de Basol et al. 2021 sur l'inoculation cross-culturelle en français.</>,
            ],
          ]}
        />
      </Section>

      <Section title="Concepts de gouvernance (P4)">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>EIP-resistance</strong>,
              <>Classe de NFR (Non-Functional Requirement) imposée par le pilier P4. Recouvre : méthodologie pré-publiée 3 mois avant le live, vocabulaire à tiers, publication à deux vitesses, règle de corroboration multi-source, COI audités, ratio symétrique mensuel publié, checklist post-mortem EIP. <em>Chaque release-gate inclut un check EIP-resistance.</em></>,
            ],
            [
              <><strong>Ratio symétrique</strong> <em>(symmetric topic ratio)</em></>,
              <>Publication mensuelle de la répartition topique des épisodes surfacés (gauche / droite / centre / autre). Garde-fou contre l'asymétrie qui a politiquement détruit l'EIP en 2023.</>,
            ],
            [
              <strong>Publication à deux vitesses</strong>,
              <>Note préliminaire rapide + note longue après corroboration multi-source. Calque OSCE.</>,
            ],
            [
              <strong>COI</strong>,
              <><em>Conflict of Interest</em>. Déclaration auditée pour chaque analyste ayant autorité d'escalade. Rotation des binômes.</>,
            ],
            [
              <strong>Multi-source corroboration rule</strong>,
              <>Aucune escalade T4/T5 sur un signal unique. Requis : ≥ 3 signaux indépendants de ≥ 2 familles.</>,
            ],
            [
              <strong>Audit trail public</strong>,
              <>Chaque interaction logguée dans un journal public en lecture seule (couche transparence du pilier P6).</>,
            ],
          ]}
        />
      </Section>

      <Section title="Concepts d'inoculation (P5)">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>Pre-bunking / inoculation</strong>,
              <>Exposition préventive à une forme affaiblie de manipulation pour développer la résistance cognitive. Roozenbeek / van der Linden. Validé en français par Basol et al. 2021.</>,
            ],
            [
              <strong>Trusted-messenger partners</strong>,
              <>Partenaires externes (campagnes, fact-checkers, presse régionale) qui distribuent les pre-bunks sous <em>leur</em> marque. <strong>Jamais sous marque gouvernementale.</strong> Garde-fou critique contre le risque E-L1.</>,
            ],
            [
              <strong>Templates fallacieux</strong>,
              <>Types de raisonnement adressés par les pre-bunks (strawman, moving-the-goalposts, whataboutism…). <em>Moving-the-goalposts dépriorité</em> — polarise dans certaines populations (Biddlestone 2025).</>,
            ],
          ]}
        />
      </Section>

      <Section title="Concepts UX (P6)">
        <Table
          head={['Terme', 'Définition']}
          rows={[
            [
              <strong>Console opérateur</strong>,
              <>Vue analyste VIGINUM/Arcom : triage + cascade visualization + dossier preview.</>,
            ],
            [
              <strong>Vue commanditaire / démo</strong>,
              <>Vue command-center : temps réel + mode replay sur cas Telegram-natifs (Matriochka 2024, Storm-1516 2024–2025, FR-législatives 2024 sous-graphe Telegram ; Pravda en continu). <em>(Macron Leaks 2017 retiré — Telegram négligeable en politique FR en 2017.)</em></>,
            ],
            [
              <><strong>Couche transparence publique</strong> <em>(Public Transparency Layer)</em></>,
              <>Vue publique en lecture seule : ratio symétrique + audit méthodologique + comptes par tier de sévérité. <strong>Elle est elle-même un artefact d'EIP-resistance</strong>, pas un simple habillage.</>,
            ],
          ]}
        />
      </Section>
    </DocPage>
  )
}
