/* eslint-disable react/prop-types */
// Grafo SVG da rede NEAT da criatura inspecionada (BIT-27). Layout fixo em 3 colunas
// (inputs -> hidden -> outputs); o grafo e pequeno (Gen 0: 20 nos, 64 conexoes), entao
// SVG puro basta — sem lib de visualizacao. Arestas: acento para peso positivo, ambar
// para negativo, espessura proporcional a |peso|. Estetica bioluminescente (hudTheme.js).
import { HUD } from './hudTheme';

const WIDTH = 218;
const COL_X = { input: 12, hidden: 109, output: 206 };
const TOP_PAD = 12;
const ROW_SPACING = 13; // 16 inputs => coluna de ~195px (~220px de SVG)
const NODE_RADIUS = 3.5;
const NODE_FILL = { input: HUD.textDim, hidden: HUD.accent, output: HUD.warm };

const FOOTER_STYLE = {
  marginTop: 4,
  fontFamily: HUD.fontMono,
  fontSize: '10.5px',
  color: HUD.textDim,
};

// Texto do <title> (tooltip nativo do SVG): label/key sempre; bias/activation
// so para outputs/hidden (inputs nao tem NodeGene proprio no NEAT 0.92).
const nodeTitle = (node) => {
  const name = node.label || `node ${node.key}`;
  if (node.type === 'input') return `${name} (key ${node.key})`;
  const bias = typeof node.bias === 'number' ? node.bias.toFixed(2) : '—';
  return `${name} (key ${node.key}) — bias ${bias} · ${node.activation || '—'}`;
};

const NeuralNetworkViewer = ({ genome }) => {
  if (!genome || !genome.nodes) return null;

  const nodes = Object.values(genome.nodes);
  // Inputs em ordem do contrato (key -1 = Visual_Sector_0 no topo); demais por key.
  const inputs = nodes.filter((n) => n.type === 'input').sort((a, b) => b.key - a.key);
  const hidden = nodes.filter((n) => n.type === 'hidden').sort((a, b) => a.key - b.key);
  const outputs = nodes.filter((n) => n.type === 'output').sort((a, b) => a.key - b.key);

  const span = Math.max(1, inputs.length - 1) * ROW_SPACING;
  const height = TOP_PAD * 2 + span;

  // Posicao de cada no: inputs em fileiras fixas; hidden/outputs distribuidos na mesma altura.
  const spread = (list, i) => TOP_PAD + (span * (i + 0.5)) / list.length;
  const pos = {};
  inputs.forEach((n, i) => { pos[n.key] = { x: COL_X.input, y: TOP_PAD + i * ROW_SPACING }; });
  hidden.forEach((n, i) => { pos[n.key] = { x: COL_X.hidden, y: spread(hidden, i) }; });
  outputs.forEach((n, i) => { pos[n.key] = { x: COL_X.output, y: spread(outputs, i) }; });

  const connections = Array.isArray(genome.connections) ? genome.connections : [];
  const enabled = connections.filter((c) => c.enabled && pos[c.from] && pos[c.to]);
  const maxAbsWeight = enabled.reduce((m, c) => Math.max(m, Math.abs(c.weight)), 0) || 1;

  return (
    <div>
      <svg width={WIDTH} height={height} role="img" aria-label="Grafo da rede neural">
        {enabled.map((c, i) => (
          <line
            key={i}
            x1={pos[c.from].x}
            y1={pos[c.from].y}
            x2={pos[c.to].x}
            y2={pos[c.to].y}
            stroke={c.weight > 0 ? HUD.accent : HUD.warm}
            strokeWidth={0.4 + (2.0 * Math.abs(c.weight)) / maxAbsWeight}
            opacity={0.55}
          />
        ))}
        {nodes.map((n) => (
          pos[n.key] && (
            <circle key={n.key} cx={pos[n.key].x} cy={pos[n.key].y} r={NODE_RADIUS} fill={NODE_FILL[n.type]}>
              <title>{nodeTitle(n)}</title>
            </circle>
          )
        ))}
      </svg>
      <div style={FOOTER_STYLE}>{nodes.length} nós · {connections.length} conexões</div>
    </div>
  );
};

export default NeuralNetworkViewer;
