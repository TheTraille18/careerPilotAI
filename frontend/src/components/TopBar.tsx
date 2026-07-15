import BlackCloudLogo from './BlackCloudLogo';

export default function TopBar() {
  return (
    <header className="top-bar">
      <div className="top-bar-inner">
        <a className="top-bar-logo" href="https://ablackcloud.com/apps" target="_blank" rel="noreferrer">
          <BlackCloudLogo />
        </a>
        <div className="top-bar-actions">
          <a
            className="top-bar-link"
            href="https://www.linkedin.com/in/justin-traille-b9a1708a/"
            target="_blank"
            rel="noreferrer"
          >
            LinkedIn
          </a>
          <a
            className="top-bar-link"
            href="https://github.com/TheTraille18/"
            target="_blank"
            rel="noreferrer"
          >
            Github
          </a>
        </div>
      </div>
    </header>
  );
}
