import BlackCloudLogo from './BlackCloudLogo';
import Tip from './Tip';

export default function TopBar() {
  return (
    <header className="top-bar">
      <div className="top-bar-inner">
        <Tip text="Open A Black Cloud apps (new tab)">
          <a className="top-bar-logo" href="https://ablackcloud.com/apps" target="_blank" rel="noreferrer">
            <BlackCloudLogo />
          </a>
        </Tip>
        <div className="top-bar-actions">
          <Tip text="Open Justin Traille’s LinkedIn profile">
            <a
              className="top-bar-link"
              href="https://www.linkedin.com/in/justin-traille-b9a1708a/"
              target="_blank"
              rel="noreferrer"
            >
              LinkedIn
            </a>
          </Tip>
          <Tip text="Open Justin Traille’s GitHub profile">
            <a
              className="top-bar-link"
              href="https://github.com/TheTraille18/"
              target="_blank"
              rel="noreferrer"
            >
              Github
            </a>
          </Tip>
        </div>
      </div>
    </header>
  );
}
