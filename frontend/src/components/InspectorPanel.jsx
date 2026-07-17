/* eslint-disable react/prop-types */
// Estado ao vivo do bibite selecionado. Conteudo embutivel (renderiza inline dentro do
// ControlMenu). Recebe `creature` (objeto do state) ou null, e `genome` (topologia da
// rede recebida via creature_inspection, BIT-27) ou null enquanto carrega. Estetica
// bioluminescente (ver hudTheme.js): sinais positivos no acento, negativos no ambar.
import { useState } from 'react';
import { HUD } from './hudTheme';
import NeuralNetworkViewer from './NeuralNetworkViewer';

const PANEL_STYLE = {
  color: HUD.text,
  fontFamily: HUD.fontMono,
  fontSize: '12px',
  lineHeight: 1.45,
};

const LABEL_STYLE = { color: HUD.textDim, fontFamily: HUD.fontUi, fontSize: '11px' };

// Cabecalho de grupo colapsavel — mesmo padrao visual dos grupos do ParamsPanel (.hud-group).
const GROUP_HEADER_STYLE = {
  display: 'flex',
  alignItems: 'center',
  gap: 7,
  cursor: 'pointer',
  padding: '5px 4px',
  marginTop: 9,
  borderRadius: 5,
  fontFamily: HUD.fontUi,
  fontSize: '11.5px',
  fontWeight: 600,
  color: HUD.text,
  userSelect: 'none',
};

const CHEVRON_STYLE = { color: HUD.accent, fontSize: '10px', width: 10 };

// Barra horizontal simples (0..1) — usada para energia.
const Bar = ({ frac, color }) => (
  <div style={{
    width: '100%',
    height: 7,
    backgroundColor: HUD.track,
    borderRadius: 4,
    overflow: 'hidden',
  }}>
    <div style={{
      width: `${Math.max(0, Math.min(1, frac)) * 100}%`,
      height: '100%',
      backgroundColor: color,
      boxShadow: `0 0 6px ${color}`,
    }} />
  </div>
);

// Barrinha vertical de setor de visao: acento para sinal > 0, ambar para < 0,
// altura proporcional a |valor| (valor esperado em ~[-1, 1]).
const VisionSector = ({ value }) => {
  const mag = Math.max(0, Math.min(1, Math.abs(value)));
  const color = value >= 0 ? HUD.accent : HUD.warm;
  return (
    <div style={{
      width: 10,
      height: 28,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'flex-end',
      backgroundColor: 'rgba(230,244,239,0.08)',
      borderRadius: 2,
    }}>
      <div style={{
        width: '100%',
        height: `${mag * 100}%`,
        backgroundColor: color,
      }} />
    </div>
  );
};

// Barra bipolar horizontal (valor em ~[-1, 1]): centro fixo, preenche para a direita quando
// positivo (acento) e para a esquerda quando negativo (ambar).
const BipolarBar = ({ label, value }) => {
  const v = Math.max(-1, Math.min(1, value || 0));
  const half = Math.abs(v) * 50;
  return (
    <div style={{ marginBottom: 5 }}>
      <div style={{ ...LABEL_STYLE, marginBottom: 2 }}>{label}: <span style={{ color: HUD.text, fontFamily: HUD.fontMono }}>{v.toFixed(2)}</span></div>
      <div style={{
        position: 'relative',
        width: '100%',
        height: 7,
        backgroundColor: HUD.track,
        borderRadius: 4,
        overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, backgroundColor: 'rgba(230,244,239,0.35)' }} />
        <div style={{
          position: 'absolute',
          top: 0,
          height: '100%',
          left: v >= 0 ? '50%' : `${50 - half}%`,
          width: `${half}%`,
          backgroundColor: v >= 0 ? HUD.accent : HUD.warm,
        }} />
      </div>
    </div>
  );
};

// Badge liga/desliga para acoes booleanas do cerebro.
const ActionBadge = ({ label, on }) => (
  <span style={{
    display: 'inline-block',
    padding: '2px 7px',
    marginRight: 5,
    borderRadius: 4,
    fontSize: '11px',
    fontFamily: HUD.fontUi,
    backgroundColor: on ? HUD.accent : 'rgba(230,244,239,0.08)',
    color: on ? '#04201a' : HUD.textDim,
    boxShadow: on ? HUD.accentGlow : 'none',
  }}>
    {label}
  </span>
);

const InspectorPanel = ({ creature, genome }) => {
  // Secao da rede aberta por padrao: ver o cerebro e o proposito do inspetor (BIT-27).
  const [netOpen, setNetOpen] = useState(true);

  if (!creature) return null;

  const color = creature.color || HUD.accent;
  const maxEnergy = creature.max_energy || 100;
  const energyFrac = maxEnergy > 0 ? (creature.energy || 0) / maxEnergy : 0;
  const vision = Array.isArray(creature.vision) ? creature.vision : [];

  return (
    <div style={PANEL_STYLE}>
      <div style={{ fontWeight: 700, marginBottom: 4, fontSize: '13px' }}>
        <span style={{ color: HUD.textDim }}>#</span>{creature.id}{' '}
        <span style={{ color }}>{creature.life_stage || '—'}</span>
      </div>
      <div style={LABEL_STYLE}>Idade: <span style={{ color: HUD.text, fontFamily: HUD.fontMono }}>{(creature.age ?? 0).toFixed(1)}s</span></div>

      <div style={{ ...LABEL_STYLE, marginTop: 7, marginBottom: 3 }}>
        Energia: <span style={{ color: HUD.text, fontFamily: HUD.fontMono }}>{(creature.energy ?? 0).toFixed(0)} / {maxEnergy.toFixed(0)}</span>
      </div>
      <Bar frac={energyFrac} color={color} />

      <div style={{ ...LABEL_STYLE, marginTop: 7 }}>Dieta: <span style={{ color: HUD.text }}>{creature.diet ?? '—'}</span></div>
      <div style={LABEL_STYLE}>Cooldown repro.: <span style={{ color: HUD.text, fontFamily: HUD.fontMono }}>{(creature.reproduction_cooldown ?? 0).toFixed(1)}s</span></div>

      <div style={{ ...LABEL_STYLE, marginTop: 9, marginBottom: 3 }}>Visao (9 setores)</div>
      <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
        {vision.map((v, i) => <VisionSector key={i} value={v} />)}
      </div>

      <div style={{ ...LABEL_STYLE, marginTop: 9, marginBottom: 3 }}>Cerebro</div>
      <BipolarBar label="motor_forward" value={creature.motor_forward} />
      <BipolarBar label="motor_torque" value={creature.motor_torque} />
      <div style={{ marginTop: 5 }}>
        <ActionBadge label="acasalar" on={!!creature.action_mate} />
        <ActionBadge label="pegar/soltar" on={!!creature.action_grab_drop} />
      </div>

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
