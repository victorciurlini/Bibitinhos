/* eslint-disable react/prop-types */
// Estado ao vivo do bibite selecionado. Conteudo embutivel (renderiza inline dentro do
// ControlMenu; nao se posiciona sozinho). Recebe `creature` (objeto do state) ou null
// (nao renderiza nada — o menu mostra a dica de selecao).

const PANEL_STYLE = {
  color: '#fff',
  fontFamily: 'monospace',
  fontSize: '12px',
  lineHeight: 1.4,
};

// Barra horizontal simples (0..1) — usada para energia.
const Bar = ({ frac, color }) => (
  <div style={{
    width: '100%',
    height: 8,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderRadius: 3,
    overflow: 'hidden',
  }}>
    <div style={{
      width: `${Math.max(0, Math.min(1, frac)) * 100}%`,
      height: '100%',
      backgroundColor: color,
    }} />
  </div>
);

// Barrinha vertical de setor de visao: verde para sinal > 0, vermelho para < 0,
// altura proporcional a |valor| (valor esperado em ~[-1, 1]).
const VisionSector = ({ value }) => {
  const mag = Math.max(0, Math.min(1, Math.abs(value)));
  const color = value >= 0 ? '#4CAF50' : '#e05252';
  return (
    <div style={{
      width: 10,
      height: 28,
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'flex-end',
      backgroundColor: 'rgba(255,255,255,0.10)',
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

// Barra bipolar horizontal (valor em ~[-1, 1]): centro fixo, preenche para a
// direita quando positivo e para a esquerda quando negativo.
const BipolarBar = ({ label, value }) => {
  const v = Math.max(-1, Math.min(1, value || 0));
  const half = Math.abs(v) * 50;
  return (
    <div style={{ marginBottom: 4 }}>
      <div style={{ fontSize: '11px', opacity: 0.85 }}>{label}: {v.toFixed(2)}</div>
      <div style={{
        position: 'relative',
        width: '100%',
        height: 8,
        backgroundColor: 'rgba(255,255,255,0.12)',
        borderRadius: 3,
        overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, backgroundColor: 'rgba(255,255,255,0.4)' }} />
        <div style={{
          position: 'absolute',
          top: 0,
          height: '100%',
          left: v >= 0 ? '50%' : `${50 - half}%`,
          width: `${half}%`,
          backgroundColor: v >= 0 ? '#5aa9e6' : '#e6a55a',
        }} />
      </div>
    </div>
  );
};

// Badge liga/desliga para acoes booleanas do cerebro.
const ActionBadge = ({ label, on }) => (
  <span style={{
    display: 'inline-block',
    padding: '2px 6px',
    marginRight: 4,
    borderRadius: 3,
    fontSize: '11px',
    backgroundColor: on ? '#4CAF50' : 'rgba(255,255,255,0.15)',
    color: on ? '#000' : 'rgba(255,255,255,0.6)',
  }}>
    {label}
  </span>
);

const InspectorPanel = ({ creature }) => {
  if (!creature) return null;

  const color = creature.color || '#4CAF50';
  const maxEnergy = creature.max_energy || 100;
  const energyFrac = maxEnergy > 0 ? (creature.energy || 0) / maxEnergy : 0;
  const vision = Array.isArray(creature.vision) ? creature.vision : [];

  return (
    <div style={PANEL_STYLE}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
        #{creature.id} <span style={{ color }}>{creature.life_stage || '—'}</span>
      </div>
      <div>Idade: {(creature.age ?? 0).toFixed(1)}s</div>

      <div style={{ marginTop: 6, marginBottom: 2 }}>
        Energia: {(creature.energy ?? 0).toFixed(0)} / {maxEnergy.toFixed(0)}
      </div>
      <Bar frac={energyFrac} color={color} />

      <div style={{ marginTop: 6 }}>Dieta: {creature.diet ?? '—'}</div>
      <div>Cooldown repro.: {(creature.reproduction_cooldown ?? 0).toFixed(1)}s</div>

      <div style={{ marginTop: 8, marginBottom: 2 }}>Visao (9 setores)</div>
      <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end' }}>
        {vision.map((v, i) => <VisionSector key={i} value={v} />)}
      </div>

      <div style={{ marginTop: 8, marginBottom: 2 }}>Cerebro</div>
      <BipolarBar label="motor_forward" value={creature.motor_forward} />
      <BipolarBar label="motor_torque" value={creature.motor_torque} />
      <div style={{ marginTop: 4 }}>
        <ActionBadge label="acasalar" on={!!creature.action_mate} />
        <ActionBadge label="pegar/soltar" on={!!creature.action_grab_drop} />
      </div>
    </div>
  );
};

export default InspectorPanel;
