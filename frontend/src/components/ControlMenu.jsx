/* eslint-disable react/prop-types */
// Menu HUD recolhivel no canto superior esquerdo. Escondido por padrao: mostra so o botao de
// expansao. Expandido, abre um painel de vidro teal a esquerda com as secoes Tempo,
// Metricas e Parametros. Estetica "bioluminescente de laboratorio" (ver hudTheme.js). O botao ecoa o
// estado do servidor via props. BIT-34: InspectorPanel movido para CreatureDetailPanel (painel direito).
import { useState } from 'react';
import TimeControls from './TimeControls';
import MetricsPanel from './MetricsPanel';
import ParamsPanel from './ParamsPanel';
import { HUD, panelStyle, sectionLabelStyle, sectionRuleStyle } from './hudTheme';
import './hud.css';

const COLLAPSED_STYLE = {
  position: 'absolute',
  top: 12,
  left: 12,
  zIndex: 10,
};

const TOGGLE_STYLE = {
  width: 38,
  height: 38,
  border: HUD.panelBorder,
  borderRadius: 10,
  cursor: 'pointer',
  backgroundColor: HUD.panelBg,
  backdropFilter: HUD.panelBlur,
  WebkitBackdropFilter: HUD.panelBlur,
  boxShadow: HUD.panelShadow,
  color: HUD.accent,
  fontSize: '18px',
  lineHeight: 1,
  padding: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

const PANEL_STYLE = {
  ...panelStyle,
  position: 'absolute',
  top: 12,
  left: 12,
  width: 244,
  maxHeight: 'calc(100% - 24px)',
  overflowY: 'auto',
  padding: '11px 13px 13px',
  zIndex: 10,
  fontFamily: HUD.fontMono,
  fontSize: '12px',
  boxSizing: 'border-box',
};

const HEADER_STYLE = {
  display: 'flex',
  alignItems: 'center',
  gap: 9,
  marginBottom: 4,
};

const HEADER_TITLE_STYLE = {
  fontFamily: HUD.fontUi,
  fontWeight: 600,
  fontSize: '13px',
  letterSpacing: '0.03em',
  color: HUD.text,
};

const HEADER_TOGGLE_STYLE = {
  width: 24,
  height: 24,
  border: '1px solid rgba(70,229,176,0.22)',
  borderRadius: 7,
  cursor: 'pointer',
  backgroundColor: 'transparent',
  color: HUD.accent,
  fontSize: '14px',
  lineHeight: 1,
  padding: 0,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
};

// Rotulo de secao com filete a direita.
const SectionLabel = ({ children }) => (
  <div style={sectionLabelStyle}>
    <span>{children}</span>
    <span style={sectionRuleStyle} />
  </div>
);

const ControlMenu = ({ paused, speed, params, metrics, metricsSeries, onCommand }) => {
  const [expanded, setExpanded] = useState(false);

  if (!expanded) {
    return (
      <div style={COLLAPSED_STYLE}>
        <button
          className="hud-btn hud-toggle"
          style={TOGGLE_STYLE}
          onClick={() => setExpanded(true)}
          title="Abrir menu"
          aria-label="Abrir menu"
          aria-expanded="false"
        >
          ≡
        </button>
      </div>
    );
  }

  return (
    <div className="hud-scroll hud-panel-in" style={PANEL_STYLE}>
      <div style={HEADER_STYLE}>
        <button
          className="hud-btn hud-icon-btn"
          style={HEADER_TOGGLE_STYLE}
          onClick={() => setExpanded(false)}
          title="Fechar menu"
          aria-label="Fechar menu"
          aria-expanded="true"
        >
          ×
        </button>
        <span style={HEADER_TITLE_STYLE}>Bibitinhos</span>
      </div>

      <SectionLabel>Tempo</SectionLabel>
      <TimeControls paused={paused} speed={speed} onCommand={onCommand} />

      <SectionLabel>Metricas</SectionLabel>
      <MetricsPanel metrics={metrics} series={metricsSeries} />

      <SectionLabel>Parametros</SectionLabel>
      <ParamsPanel params={params} onCommand={onCommand} />
    </div>
  );
};

export default ControlMenu;
