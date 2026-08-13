import { useEffect, useId, useRef, useState } from 'react';
import { useAdmin } from '../auth/AdminContext';
import Tip from './Tip';

function ProfileIcon() {
  return (
    <svg
      className="profile-icon-svg"
      viewBox="0 0 24 24"
      width="22"
      height="22"
      aria-hidden="true"
      focusable="false"
    >
      <circle cx="12" cy="12" r="11" fill="#111111" />
      <circle cx="12" cy="9" r="3.25" fill="#f5f5f5" />
      <path
        d="M5.5 18.6c1.7-2.6 4-3.9 6.5-3.9s4.8 1.3 6.5 3.9"
        fill="none"
        stroke="#f5f5f5"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Black profile control — upper-right dropdown for admin sign-in / sign-out. */
export default function ProfileButton() {
  const { authEnabled, isAdmin, email, loading, login, logout } = useAdmin();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };

    window.addEventListener('mousedown', onPointerDown);
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('mousedown', onPointerDown);
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  if (!authEnabled) {
    return null;
  }

  return (
    <div className="profile-menu" ref={rootRef}>
      <Tip text="Open account menu for admin sign-in or sign-out">
        <button
          type="button"
          className={`profile-icon-button${isAdmin ? ' is-admin' : ''}`}
          onClick={() => setOpen((value) => !value)}
          disabled={loading}
          aria-label="Account menu"
          aria-haspopup="menu"
          aria-expanded={open}
          aria-controls={menuId}
        >
          <ProfileIcon />
        </button>
      </Tip>

      {open && (
        <div className="profile-dropdown" id={menuId} role="menu">
          <div className="profile-dropdown-status">
            {isAdmin ? (
              <>
                <span className="profile-dropdown-label">Signed in</span>
                <span className="profile-dropdown-email">{email || 'Admin'}</span>
              </>
            ) : (
              <>
                <span className="profile-dropdown-label">Demo mode</span>
                <span className="profile-dropdown-email">AI actions locked</span>
              </>
            )}
          </div>

          {isAdmin ? (
            <Tip text="Sign out of admin and return to the restricted demo view" place="bottom">
              <button
                type="button"
                className="profile-dropdown-item"
                role="menuitem"
                disabled={loading}
                onClick={() => {
                  setOpen(false);
                  void logout();
                }}
              >
                Sign out
              </button>
            </Tip>
          ) : (
            <Tip text="Sign in with Google to unlock AI tools and real job data" place="bottom">
              <button
                type="button"
                className="profile-dropdown-item"
                role="menuitem"
                disabled={loading}
                onClick={() => {
                  setOpen(false);
                  login();
                }}
              >
                Admin sign-in
              </button>
            </Tip>
          )}
        </div>
      )}
    </div>
  );
}
