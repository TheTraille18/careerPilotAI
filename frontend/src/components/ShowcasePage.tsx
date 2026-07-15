import type { ReactNode } from 'react';
import AppStatusBadge from './AppStatusBadge';
import type { ShowcaseContent } from '../content/careerPilot';

interface ShowcasePageProps {
  content: ShowcaseContent;
  demoTitle?: string;
  children?: ReactNode;
}

export default function ShowcasePage({
  content,
  demoTitle = 'Live demo',
  children,
}: ShowcasePageProps) {
  return (
    <div className="showcase-page">
      <div className="showcase-layout">
        <div className="showcase-main">
          <section className="showcase-card">
            <div className="showcase-title-row">
              <h1 className="showcase-title">{content.title}</h1>
              <AppStatusBadge status={content.status} size="md" />
            </div>
            <p className="showcase-tagline">{content.tagline}</p>
          </section>

          <section className="showcase-card showcase-card-scroll">
            <h2 className="showcase-section-title">Summary</h2>
            <div className="showcase-scroll-body">
              {content.summary.map((paragraph) => (
                <p key={paragraph} className="showcase-body-text">
                  {paragraph}
                </p>
              ))}
            </div>
          </section>

          <section className="showcase-card">
            <h2 className="showcase-section-title">Tools used</h2>
            <div className="tool-groups">
              {content.toolsUsed.map((group) => (
                <div key={group.category} className="tool-group">
                  <h3 className="tool-category">{group.category}</h3>
                  <ul className="tool-list">
                    {group.tools.map((tool) => (
                      <li key={tool} className="tool-pill">
                        {tool}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>

          {children && (
            <section className="showcase-card showcase-card-demo">
              <h2 className="showcase-section-title">{demoTitle}</h2>
              {children}
            </section>
          )}
        </div>

        <aside className="showcase-sidebar">
          <section className="showcase-card showcase-card-sidebar">
            <h2 className="showcase-section-title">Progress updates</h2>
            <div className="showcase-scroll-body">
              <ul className="timeline">
                {content.progressUpdates.map((update) => (
                  <li key={`${update.date}-${update.title}`} className="timeline-item">
                    <p className="timeline-date">{update.date}</p>
                    <h3 className="timeline-title">{update.title}</h3>
                    <p className="timeline-detail">{update.detail}</p>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
