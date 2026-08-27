/* eslint-disable react/prop-types */
// Estado ao vivo do bibite selecionado. Conteudo embutivel dentro do CreatureDetailPanel.
// Recebe `creature` (objeto do state) ou null, e `genome` (topologia da rede recebida via
// creature_inspection, BIT-27) ou null enquanto carrega. Estetica bioluminescente
// (ver hudTheme.js): sinais positivos no acento, negativos no ambar.
import { useState } from 'react';
import { HUD, sectionLabelStyle, sectionRuleStyle } from './hudTheme';
import NeuralNetworkViewer from './NeuralNetworkViewer';

const PANEL_STYLE = {
  color: HUD.text,
  fontFamily: HUD.fontMono,
  fontSize: '12px',
  lineHeight: 1.5,
  padding: '10px 12px 16px',
};

const LABEL_STYLE = { color: HUD.textDim, fontFamily: HUD.fontUi, fontSize: '11px' };

const VALUE_STYLE = { color: HUD.text, fontFamily: HUD.fontMono };

const GROUP_HEADER_STYLE = {
  display: 'flex',
  alignItems: 'center',
  gap: 7,
  cursor: 'pointer',
  padding: '4px 2px',
  marginTop: 6,
  borderRadius: 5,
  fontFamily: HUD.fontUi,
  fontSize: '11.5px',
  fontWeight: 600,
  color: HUD.text,
  userSelect: 'none',
};

const CHEVRON_STYLE = { color: HUD.accent, fontSize: '10px', width: 10 };

const SectionLabel = ({ children }) => (
  <div style={{ ...sectionLabelStyle, marginTop: 14, marginBottom: 8 }}>
    <span>{children}</span>
    <div style={sectionRuleStyle} />
  </div>
);

// Barra horizontal (0..1) — energia. Usa a cor do próprio bibitinho como fill.
const Bar = ({ frac, color }) => (
  <div style={{
    width: '100%',
    height: 9,
    backgroundColor: HUD.track,
    borderRadius: 5,
    overflow: 'hidden',
  }}>
    <div style={{
      width: `${Math.max(0, Math.min(1, frac)) * 100}%`,
      height: '100%',
      backgroundColor: color,
      boxShadow: `0 0 8px ${color}88`,
      borderRadius: 5,
      transition: 'width 0.15s',
    }} />
  </div>
);

// Barrinha vertical de setor de visão. Acento para sinal > 0, âmbar para < 0.
const VisionSector = ({ value }) => {
  const mag = Math.max(0, Math.min(1, Math.abs(value)));
  const color = value >= 0 ? HUD.accent : HUD.warm;
  return (
    <div style={{
      width: 14,
      height: 42,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'flex-end',
      backgroundColor: 'rgba(230,244,239,0.06)',
      borderRadius: 3,
    }}>
      <div style={{
        width: '100%',
        height: `${mag * 100}%`,
        backgroundColor: color,
        boxShadow: mag > 0.12 ? `0 0 5px ${color}` : 'none',
        borderRadius: 2,
      }} />
    </div>
  );
};

// Barra bipolar horizontal (valor em ~[-1, 1]): centro fixo, acento à direita, âmbar à esquerda.
const BipolarBar = ({ label, value }) => {
  const v = Math.max(-1, Math.min(1, value || 0));
  const half = Math.abs(v) * 50;
  return (
    <div style={{ marginBottom: 7 }}>
      <div style={{ ...LABEL_STYLE, marginBottom: 3 }}>
        {label}: <span style={VALUE_STYLE}>{v.toFixed(2)}</span>
      </div>
      <div style={{
        position: 'relative',
        width: '100%',
        height: 7,
        backgroundColor: HUD.track,
        borderRadius: 4,
        overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, backgroundColor: 'rgba(230,244,239,0.3)' }} />
        <div style={{
          position: 'absolute',
          top: 0,
          height: '100%',
          left: v >= 0 ? '50%' : `${50 - half}%`,
          width: `${half}%`,
          backgroundColor: v >= 0 ? HUD.accent : HUD.warm,
          boxShadow: Math.abs(v) > 0.1 ? `0 0 5px ${v >= 0 ? HUD.accent : HUD.warm}` : 'none',
        }} />
      </div>
    </div>
  );
};

// Badge liga/desliga para ações booleanas do cérebro.
const ActionBadge = ({ label, on }) => (
  <span style={{
    display: 'inline-block',
    padding: '2px 8px',
    marginRight: 5,
    borderRadius: 4,
    fontSize: '11px',
    fontFamily: HUD.fontUi,
    backgroundColor: on ? HUD.accent : 'rgba(230,244,239,0.07)',
    color: on ? '#04201a' : HUD.textDim,
    boxShadow: on ? HUD.accentGlow : 'none',
    border: on ? 'none' : `1px solid rgba(230,244,239,0.12)`,
    transition: 'background-color 0.15s, box-shadow 0.15s',
  }}>
    {label}
  </span>
);

const InspectorPanel = ({ creature, genome }) => {
  const [netOpen, setNetOpen] = useState(true);

  if (!creature) return null;

  const color = creature.color || HUD.accent;
  const maxEnergy = creature.max_energy || 100;
  const energyFrac = maxEnergy > 0 ? (creature.energy || 0) / maxEnergy : 0;
  const vision = Array.isArray(creature.vision) ? creature.vision : [];

  return (
    <div style={PANEL_STYLE}>

      {/* METABOLISMO */}
      <SectionLabel>Metabolismo</SectionLabel>

      <div style={{ ...LABEL_STYLE, marginBottom: 4 }}>
        Energia:{' '}
        <span style={VALUE_STYLE}>{(creature.energy ?? 0).toFixed(0)}</span>
        <span style={{ color: HUD.textDim }}>/{maxEnergy.toFixed(0)}</span>
      </div>
      <Bar frac={energyFrac} color={color} />

      <div style={{ display: 'flex', gap: 14, marginTop: 9 }}>
        <div style={LABEL_STYLE}>Idade: <span style={VALUE_STYLE}>{(creature.age ?? 0).toFixed(1)}s</span></div>
        <div style={LABEL_STYLE}>Geração: <span style={VALUE_STYLE}>{creature.generation ?? 0}</span></div>
      </div>
      <div style={{ display: 'flex', gap: 14, marginTop: 4 }}>
        <div style={LABEL_STYLE}>Dieta: <span style={{ color: HUD.text }}>{creature.diet ?? '—'}</span></div>
        <div style={LABEL_STYLE}>Filhos: <span style={VALUE_STYLE}>{creature.children_count ?? 0}</span></div>
      </div>
      <div style={{ ...LABEL_STYLE, marginTop: 4 }}>
        Comidas: <span style={VALUE_STYLE}>{creature.food_eaten ?? 0}</span>
        {'  '}
        Cooldown repro.: <span style={VALUE_STYLE}>{(creature.reproduction_cooldown ?? 0).toFixed(1)}s</span>
      </div>

      {/* SENSORES */}
      <SectionLabel>Sensores</SectionLabel>

      <div style={{ ...LABEL_STYLE, marginBottom: 7 }}>Visão — 9 setores</div>
      <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end' }}>
        {vision.map((v, i) => <VisionSector key={i} value={v} />)}
      </div>

      {/* ATUADORES */}
      <SectionLabel>Atuadores</SectionLabel>

      <BipolarBar label="motor_forward" value={creature.motor_forward} />
      <BipolarBar label="motor_torque" value={creature.motor_torque} />
      <div style={{ marginTop: 6 }}>
        <ActionBadge label="acasalar" on={!!creature.action_mate} />
        <ActionBadge label="pegar/soltar" on={!!creature.action_grab_drop} />
      </div>

      {/* REDE NEURAL (colapsável) */}
      <div
        className="hud-btn hud-group"
        style={GROUP_HEADER_STYLE}
        onClick={() => setNetOpen((open) => !open)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setNetOpen((open) => !open); }}
        aria-expanded={netOpen}
      >
        <span style={CHEVRON_STYLE}>{netOpen ? '▾' : '▸'}</span>
        <span>Rede neural</span>
      </div>
      {netOpen && (
        genome
          ? <NeuralNetworkViewer genome={genome} />
          : <div style={{ ...LABEL_STYLE, padding: '2px 4px' }}>carregando rede…</div>
      )}
    </div>
  );
};

export default InspectorPanel;
