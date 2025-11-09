import React, { useEffect } from 'react';

const SCRIPT_ID = 'elevenlabs-convai-script';
const DEFAULT_AGENT_ID = 'agent_4801k9jw7h6pf56brs516fkc592q';

/**
 * ConvaiWidget
 * Injects the ElevenLabs ConvAI widget script once and renders the
 * custom element where the component is mounted.
 *
 * Usage: <ConvaiWidget agentId="agent_xxx" />
 */
export default function ConvaiWidget({ agentId = DEFAULT_AGENT_ID }) {
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

    // No teardown for the script: it's shared across the app
  }, []);

  // Render the custom element; the external script will hydrate it when ready
  // The tag name is as provided by ElevenLabs: <elevenlabs-convai>
  return (
    // eslint-disable-next-line react/no-unknown-property
    <elevenlabs-convai agent-id={agentId}></elevenlabs-convai>
  );
}
