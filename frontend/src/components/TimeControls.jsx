/* eslint-disable react/prop-types */
// Controle de tempo: pausar/retomar + velocidades. Conteudo embutivel (renderiza inline dentro
// do ControlMenu). O estado ativo reflete `paused`/`speed` ECOADOS pelo servidor (props), nunca
// a suposicao de que o comando foi aplicado. Estetica bioluminescente (ver hudTheme.js).
import { HUD } from './hudTheme';

const SPEEDS = [0.5, 1, 2, 4, 8, 50];

const CONTAINER_STYLE = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: 5,
};

const buttonStyle = (active) => ({
  minWidth: 34,
  padding: '5px 9px',
  border: active ? '1px solid rgba(70,229,176,0.9)' : '1px solid rgba(230,244,239,0.12)',
  borderRadius: 7,
  cursor: 'pointer',
  fontFamily: HUD.fontMono,
  fontSize: '12px',
  fontWeight: active ? 700 : 400,
  backgroundColor: active ? HUD.accent : 'rgba(230,244,239,0.06)',
  color: active ? '#04201a' : HUD.text,
  boxShadow: active ? HUD.accentGlow : 'none',
});

const TimeControls = ({ paused, speed, onCommand }) => {
  return (
    <div style={CONTAINER_STYLE}>
      <button
        className="hud-btn hud-time-btn"
        style={buttonStyle(paused)}
        onClick={() => onCommand({ action: 'set_time_control', paused: !paused })}
        title={paused ? 'Retomar' : 'Pausar'}
      >
        {paused ? '▶' : '⏸'}
      </button>
      {SPEEDS.map((v) => (
        <button
          key={v}
          className="hud-btn hud-time-btn"
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
