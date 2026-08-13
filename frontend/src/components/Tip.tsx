import {
  cloneElement,
  isValidElement,
  useId,
  useState,
  type CSSProperties,
  type FocusEvent,
  type MouseEvent,
  type ReactElement,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';

type TipProps = {
  text: string;
  children: ReactNode;
  className?: string;
  /** Prefer tooltip above (default) or below the pointer when space allows. */
  place?: 'top' | 'bottom';
  style?: CSSProperties;
  /**
   * Attach tip behavior to the child element itself (e.g. a table row).
   * Use when a wrapper span would break layout.
   */
  attach?: boolean;
};

type InteractiveProps = {
  onMouseEnter?: (event: MouseEvent) => void;
  onMouseLeave?: (event: MouseEvent) => void;
  onMouseMove?: (event: MouseEvent) => void;
  onMouseOver?: (event: MouseEvent) => void;
  onFocus?: (event: FocusEvent) => void;
  onBlur?: (event: FocusEvent) => void;
  'aria-describedby'?: string;
};

const NESTED_CONTROL = 'button, a, select, input, textarea, .has-tip';
const EDGE = 12;
const OFFSET = 14;

function coordsNearPointer(
  clientX: number,
  clientY: number,
  place: 'top' | 'bottom',
): { top: number; left: number; place: 'top' | 'bottom' } {
  const preferBottom = place === 'bottom' || clientY < 56;
  const preferTop = !preferBottom && clientY > window.innerHeight - 72;
  const resolved: 'top' | 'bottom' = preferTop ? 'top' : preferBottom ? 'bottom' : place;

  let left = clientX + OFFSET;
  let top = resolved === 'bottom' ? clientY + OFFSET : clientY - OFFSET;

  left = Math.min(Math.max(left, EDGE), window.innerWidth - EDGE);
  top = Math.min(Math.max(top, EDGE), window.innerHeight - EDGE);

  return { top, left, place: resolved };
}

function coordsNearElement(
  el: Element,
  place: 'top' | 'bottom',
): { top: number; left: number; place: 'top' | 'bottom' } {
  const rect = el.getBoundingClientRect();
  return coordsNearPointer(rect.left + rect.width / 2, rect.top + rect.height / 2, place);
}

type BubbleState = { top: number; left: number; place: 'top' | 'bottom' };

/** Hover/focus tooltip that explains what a clickable control does. */
export default function Tip({ text, children, className, place = 'top', style, attach = false }: TipProps) {
  const tipId = useId();
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<BubbleState | null>(null);

  const showAtPointer = (clientX: number, clientY: number) => {
    setCoords(coordsNearPointer(clientX, clientY, place));
    setOpen(true);
  };
  const showAtElement = (el: Element) => {
    setCoords(coordsNearElement(el, place));
    setOpen(true);
  };
  const hide = () => setOpen(false);

  const bubble =
    open &&
    coords &&
    createPortal(
      <span
        id={tipId}
        className={`tip-bubble tip-bubble-portal tip-bubble-portal-${coords.place}`}
        role="tooltip"
        style={{ top: coords.top, left: coords.left }}
      >
        {text}
      </span>,
      document.body,
    );

  if (attach && isValidElement(children)) {
    const child = children as ReactElement<InteractiveProps>;
    const isNestedControl = (target: EventTarget | null) => {
      if (!(target instanceof Element)) return false;
      return Boolean(target.closest(NESTED_CONTROL));
    };

    return (
      <>
        {cloneElement(child, {
          onMouseOver: (event: MouseEvent) => {
            child.props.onMouseOver?.(event);
            if (isNestedControl(event.target)) {
              hide();
              return;
            }
            showAtPointer(event.clientX, event.clientY);
          },
          onMouseMove: (event: MouseEvent) => {
            child.props.onMouseMove?.(event);
            if (isNestedControl(event.target)) {
              hide();
              return;
            }
            showAtPointer(event.clientX, event.clientY);
          },
          onMouseLeave: (event: MouseEvent) => {
            child.props.onMouseLeave?.(event);
            hide();
          },
          onFocus: (event: FocusEvent) => {
            child.props.onFocus?.(event);
            if (isNestedControl(event.target)) {
              hide();
              return;
            }
            showAtElement(event.currentTarget);
          },
          onBlur: (event: FocusEvent) => {
            child.props.onBlur?.(event);
            hide();
          },
          'aria-describedby': open ? tipId : child.props['aria-describedby'],
        })}
        {bubble}
      </>
    );
  }

  return (
    <span
      className={`has-tip${className ? ` ${className}` : ''}`}
      style={style}
      onMouseEnter={(event) => showAtPointer(event.clientX, event.clientY)}
      onMouseMove={(event) => showAtPointer(event.clientX, event.clientY)}
      onMouseLeave={hide}
      onFocus={(event) => showAtElement(event.currentTarget)}
      onBlur={hide}
    >
      {children}
      {bubble}
    </span>
  );
}
