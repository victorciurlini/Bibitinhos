/* eslint-disable react/prop-types */
// BIT-34: Painel overlay direito com informacoes do bibitinho selecionado.
// Posicionado a direita do canvas como irmao do ControlMenu. Quando a criatura morre,
// congela no ultimo estado recebido e exibe indicador de morte para analise post-mortem.
// A cor do bibitinho vira o accent do painel (dot no header, glow da barra de energia).
import InspectorPanel from './InspectorPanel';
import { HUD, panelStyle } from './hudTheme';

const LIFE_STAGE_COLORS = {
  EGG:      'rgba(230, 244, 239, 0.3)',
  JUVENILE: 'rgba(70, 229, 176, 0.55)',
  ADULT:    '#46e5b0',
  ELDER:    '#f5a15a',
};

export default function CreatureDetailPanel({ creature, genome, isDead, onClose }) {
  if (!creature) return null;

  const creatureColor = creature.color || HUD.accent;
  const lifeStageColor = LIFE_STAGE_COLORS[creature.life_stage] || HUD.accent;

  const panelOverride = {
    ...panelStyle,
    position: 'absolute',
    right: 12,
    top: 12,
    width: 280,
    maxHeight: 'calc(100% - 24px)',
    overflowY: 'auto',
    zIndex: 10,
    pointerEvents: 'auto',
    display: 'flex',
    flexDirection: 'column',
    boxSizing: 'border-box',
    borderLeft: isDead
      ? '3px solid rgba(255, 107, 107, 0.5)'
      : `3px solid ${creatureColor}33`,
    transition: 'border-left 0.5s',
  };

  return (
    <div style={panelOverride}>

      {/* Banner de morte — substitui o header colorido */}
      {isDead && (
        <div style={{
          background: 'rgba(255, 107, 107, 0.1)',
          borderBottom: '1px solid rgba(255, 107, 107, 0.25)',
          padding: '5px 12px',
          fontSize: 9,
          fontWeight: 700,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: HUD.danger,
          fontFamily: HUD.fontUi,
          textAlign: 'center',
        }}>
          ● dados congelados — fim do ciclo
        </div>
      )}

      {/* Header: dot · #ID LIFE_STAGE · × */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '9px 12px',
        borderBottom: `1px solid ${isDead ? 'rgba(255,107,107,0.18)' : 'rgba(70,229,176,0.14)'}`,
        flexShrink: 0,
        transition: 'border-bottom 0.4s',
      }}>
        {/* Dot: cor do genoma quando vivo, cinza quando morto */}
        <div style={{
          width: 9,
          height: 9,
          borderRadius: '50%',
          backgroundColor: isDead ? 'rgba(200,200,200,0.25)' : creatureColor,
          boxShadow: isDead ? 'none' : `0 0 9px ${creatureColor}`,
          flexShrink: 0,
          transition: 'background-color 0.5s, box-shadow 0.5s',
        }} />

        {/* #ID + life stage */}
        <span style={{
          fontFamily: HUD.fontUi,
          fontSize: 12,
          fontWeight: 600,
          letterSpacing: '0.04em',
          color: HUD.text,
          flex: 1,
          lineHeight: 1,
        }}>
          <span style={{ color: HUD.textDim, fontWeight: 400 }}>#</span>
          {creature.id}
          {' '}
          <span style={{
            fontSize: 10,
            fontWeight: 500,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: isDead ? 'rgba(200,200,200,0.35)' : lifeStageColor,
            transition: 'color 0.5s',
          }}>
            {creature.life_stage || '—'}
          </span>
        </span>

        {/* Fechar */}
        <button
          style={{
            background: 'none',
            border: 'none',
            color: HUD.textDim,
            cursor: 'pointer',
            fontSize: 17,
            lineHeight: 1,
            padding: '0 2px',
            flexShrink: 0,
            opacity: 0.7,
          }}
          onClick={onClose}
          title="Fechar painel"
          aria-label="Fechar painel"
        >
          ×
        </button>
      </header>

      {/* Conteúdo: dessatura e escurece quando morto */}
      <div style={{
        opacity: isDead ? 0.6 : 1,
        filter: isDead ? 'saturate(0.25)' : 'none',
        transition: 'opacity 0.5s, filter 0.5s',
        flex: 1,
        minHeight: 0,
      }}>
        <InspectorPanel creature={creature} genome={genome} />
      </div>
    </div>
  );
}
