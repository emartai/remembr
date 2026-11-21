import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import styles from './index.module.css';

const features = [
  {
    title: 'Quick Start',
    icon: '⚡',
    description: 'Start the local server, create a space and connect your first agent.',
    link: '/docs/getting-started',
  },
  {
    title: 'Shared Project Memory',
    icon: '🔌',
    description: 'Share project decisions across agents with separate credentials and named revisions.',
    link: '/docs/shared-project-memory',
  },
  {
    title: 'API Reference',
    icon: '📖',
    description: 'Explore the REST endpoints for authentication, sessions and project memory.',
    link: '/docs/api-reference',
  },
  {
    title: 'Self-Hosting',
    icon: '🐳',
    description: 'Run the memory server and Ollama embeddings on your own machine or server.',
    link: '/docs/self-hosted',
  },
  {
    title: 'Hybrid Search',
    icon: '🔍',
    description: 'Search by meaning, keyword or a combination of the two.',
    link: '/docs/concepts/search-modes',
  },
  {
    title: 'Data Controls',
    icon: '🛡️',
    description:
      'Soft deletes, hard deletes, export, and targeted erasure at every scope level.',
    link: '/docs/cookbook/gdpr-deletion',
  },
];

export default function Home() {
  const { siteConfig } = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <main>
        {/* Hero */}
        <div className={styles.hero}>
          <h1 className={styles.heroTitle}>Remembr</h1>
          <p className={styles.heroSubtitle}>
            Self-hosted, open-source memory for AI agents.
            <br />
            Save a decision with one agent and pick it up with another.
          </p>
          <div className={styles.heroCtas}>
            <Link className={styles.ctaPrimary} to="/docs/getting-started">
              Get Started →
            </Link>
            <Link className={styles.ctaSecondary} to="/docs/pilot">
              Try the developer pilot
            </Link>
          </div>
          <div className={styles.heroInstall}>
            <code>python -m pip install remembr==0.2.2</code>
            <span className={styles.separator}>·</span>
            <code>npm install @remembr/sdk@0.2.2</code>
          </div>
        </div>

        {/* Feature cards */}
        <div className={styles.features}>
          <div className={styles.grid}>
            {features.map((f) => (
              <Link key={f.title} to={f.link} className={styles.card}>
                <div className={styles.cardIcon}>{f.icon}</div>
                <h3 className={styles.cardTitle}>{f.title}</h3>
                <p className={styles.cardDesc}>{f.description}</p>
              </Link>
            ))}
          </div>
        </div>

        {/* Code example */}
        <div className={styles.codeSection}>
          <h2>Find the same decision from two agents</h2>
          <pre className={styles.codeBlock}>{`import os
from remembr import RemembrClient

space = os.environ["REMEMBR_SPACE_ID"]
url = "http://localhost:8000/api/v1"
writer = RemembrClient(api_key=os.environ["REMEMBR_WRITER_KEY"], base_url=url)
reader = RemembrClient(api_key=os.environ["REMEMBR_READER_KEY"], base_url=url)

writer.projects.store(
    space,
    "Project storage uses PostgreSQL.",
    idempotency_key="storage-v1",
    source_ref="design-notes",
)
results = reader.projects.search(space, "PostgreSQL", mode="keyword")
print(results["results"][0]["content"])`}</pre>
        </div>
      </main>
    </Layout>
  );
}
