/* eslint-disable react/prop-types */
// Mini-grafico de linha em SVG puro (BIT-26) — sem lib de graficos: o HUD e todo custom e
// os graficos sao pequenos. Normaliza a polyline ao min/max da janela de dados (escala
// relativa ao observado); com menos de 2 pontos renderiza so a trilha vazia (linha de base).
import { HUD } from './hudTheme';

const PAD = 2; // folga interna para o traco nao encostar na borda do viewBox

const Sparkline = ({ data, width = 210, height = 36, color = HUD.accent }) => {
  const points = Array.isArray(data) ? data.filter((v) => Number.isFinite(v)) : [];
  const baselineY = height - PAD;

  let polyline = null;
  if (points.length >= 2) {
    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1; // serie constante: linha reta no meio, sem divisao por zero
    const innerW = width - PAD * 2;
    const innerH = height - PAD * 2;
    const coords = points.map((v, i) => {
      const x = PAD + (i / (points.length - 1)) * innerW;
      const y = PAD + (1 - (v - min) / range) * innerH;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    polyline = (
      <polyline
        points={coords.join(' ')}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    );
  }

  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      {/* linha de base no track do HUD: da chao visual mesmo sem dados */}
      <line x1={PAD} y1={baselineY} x2={width - PAD} y2={baselineY} stroke={HUD.track} strokeWidth="1" />
      {polyline}
    </svg>
  );
};

export default Sparkline;
