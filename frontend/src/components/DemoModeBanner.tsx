import { useAdmin } from '../auth/AdminContext';
import Tip from './Tip';

type DemoModeBannerProps = {
  onSignIn?: () => void;
};

/** Visible notice when visitors are on the restricted demo experience. */
export default function DemoModeBanner({ onSignIn }: DemoModeBannerProps) {
  const { authEnabled, isAdmin, login } = useAdmin();

  if (!authEnabled || isAdmin) {
    return null;
  }

  return (
    <div className="demo-mode-banner" role="status">
      <div className="demo-mode-banner-main">
        <span className="demo-mode-badge">Demo</span>
        <div className="demo-mode-copy">
          <strong>Restricted preview</strong>
          <span>
            Sample jobs only. AI actions (fit check, resume tailoring, edits) are locked.
          </span>
        </div>
      </div>
      <Tip text="Sign in with Google to unlock AI tools and your real job data">
        <button
          type="button"
          className="btn-secondary demo-mode-signin"
          onClick={() => {
            onSignIn?.();
            login();
          }}
        >
          Admin sign-in
        </button>
      </Tip>
    </div>
  );
}
