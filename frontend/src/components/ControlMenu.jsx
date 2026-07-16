/* eslint-disable react/prop-types */
// Menu HUD recolhivel no canto superior esquerdo. Escondido por padrao: mostra so o botao
// de expansao. Expandido, abre um painel a esquerda com as secoes Tempo (controles de
// velocidade/pausa) e Inspetor (bibite selecionado). Mantem a estetica dos overlays da sim
// (fundo translucido escuro + monospace); o botao ecoa o estado do servidor via props.
import { useState } from 'react';
import TimeControls from './TimeControls';
import InspectorPanel from './InspectorPanel';

const PANEL_BG = 'rgba(0,0,0,0.6)';

const TOGGLE_STYLE = {
  width: 34,
  height: 34,
  border: 'none',
  borderRadius: 5,
  cursor: 'pointer',
  backgroundColor: PANEL_BG,
  color: '#fff',
  fontFamily: 'monospace',
  fontSize: '18px',
  lineHeight: 1,
  padding: 0,
};

const COLLAPSED_STYLE = {
  position: 'absolute',
  top: 10,
  left: 10,
  zIndex: 10,
};

const PANEL_STYLE = {
  position: 'absolute',
  top: 10,
  left: 10,
  width: 236,
  maxHeight: 'calc(100% - 20px)',
  overflowY: 'auto',
  padding: '8px 10px',
  backgroundColor: PANEL_BG,
  borderRadius: '5px',
  color: '#fff',
  zIndex: 10,
  fontFamily: 'monospace',
  fontSize: '12px',
  boxSizing: 'border-box',
};

const HEADER_STYLE = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  marginBottom: 8,
};

const HEADER_TOGGLE_STYLE = {
  ...TOGGLE_STYLE,
  width: 26,
  height: 26,
  fontSize: '15px',
  backgroundColor: 'rgba(255,255,255,0.12)',
};

// Rotulo de secao (eyebrow): caixa alta, discreto, separa Tempo de Inspetor.
const SECTION_LABEL_STYLE = {
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  fontSize: '10px',
  opacity: 0.55,
  margin: '10px 0 4px',
};

const ControlMenu = ({ paused, speed, creature, onCommand }) => {
  const [expanded, setExpanded] = useState(false);

  if (!expanded) {
    return (
      <div style={COLLAPSED_STYLE}>
        <button
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
    <div style={PANEL_STYLE}>
      <div style={HEADER_STYLE}>
        <button
          style={HEADER_TOGGLE_STYLE}
          onClick={() => setExpanded(false)}
          title="Fechar menu"
          aria-label="Fechar menu"
          aria-expanded="true"
        >
          ×
        </button>
        <span style={{ fontWeight: 'bold' }}>Menu</span>
      </div>

      <div style={{ ...SECTION_LABEL_STYLE, marginTop: 0 }}>Tempo</div>
      <TimeControls paused={paused} speed={speed} onCommand={onCommand} />

      <div style={SECTION_LABEL_STYLE}>Inspetor</div>
      {creature
        ? <InspectorPanel creature={creature} />
        : <div style={{ opacity: 0.6 }}>Clique num bibite para inspecionar.</div>}
    </div>
  );
};

export default ControlMenu;
