/* eslint-disable react/prop-types */
// Controle de tempo: pausar/retomar + velocidades. Conteudo embutivel (renderiza inline
// dentro do ControlMenu; nao se posiciona sozinho).
// O estado ativo reflete `paused`/`speed` ECOADOS pelo servidor (props),
// nunca a suposicao de que o comando foi aplicado.

const SPEEDS = [0.5, 1, 2, 4];

const CONTAINER_STYLE = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 6,
  fontFamily: 'monospace',
};

const buttonStyle = (active) => ({
  minWidth: 34,
  padding: '4px 8px',
  border: 'none',
  borderRadius: 3,
  cursor: 'pointer',
  fontFamily: 'monospace',
  fontSize: '13px',
  backgroundColor: active ? '#4CAF50' : 'rgba(255,255,255,0.15)',
  color: active ? '#000' : '#fff',
});

const TimeControls = ({ paused, speed, onCommand }) => {
  return (
    <div style={CONTAINER_STYLE}>
      <button
        style={buttonStyle(paused)}
        onClick={() => onCommand({ action: 'set_time_control', paused: !paused })}
        title={paused ? 'Retomar' : 'Pausar'}
      >
        {paused ? '▶' : '⏸'}
      </button>
      {SPEEDS.map((v) => (
        <button
          key={v}
          style={buttonStyle(!paused && speed === v)}
          onClick={() => onCommand({ action: 'set_time_control', speed: v })}
        >
          {v}x
        </button>
      ))}
    </div>
  );
};

export default TimeControls;
