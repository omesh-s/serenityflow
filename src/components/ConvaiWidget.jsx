import React, { useEffect, useRef } from 'react';

const SCRIPT_ID = 'elevenlabs-convai-script';
const WIDGET_ID = 'elevenlabs-convai-widget';
const DEFAULT_AGENT_ID = 'agent_4801k9jw7h6pf56brs516fkc592q';

export default function ConvaiWidget({ agentId = DEFAULT_AGENT_ID }) {
  const containerRef = useRef(null);

  useEffect(() => {
    // Inject script once
    if (!document.getElementById(SCRIPT_ID)) {
      const s = document.createElement('script');
      s.src = 'https://unpkg.com/@elevenlabs/convai-widget-embed';
      s.async = true;
      s.type = 'text/javascript';
      s.id = SCRIPT_ID;
      document.body.appendChild(s);
    }

    // Ensure widget element only exists once
    if (containerRef.current && !containerRef.current.querySelector('elevenlabs-convai')) {
      const widget = document.createElement('elevenlabs-convai');
      widget.setAttribute('agent-id', agentId);
      widget.id = WIDGET_ID;
      containerRef.current.appendChild(widget);
    }

    return () => {
      // Cleanup: remove widget element when component unmounts
      if (containerRef.current) {
        const widget = containerRef.current.querySelector(`#${WIDGET_ID}`);
        if (widget) {
          widget.remove();
        }
      }
    };
  }, [agentId]);

  return <div ref={containerRef}></div>;
}