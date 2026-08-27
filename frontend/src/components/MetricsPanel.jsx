/* eslint-disable react/prop-types */
// Painel de metricas populacionais (BIT-26). Conteudo embutivel no ControlMenu, irmao do
// InspectorPanel/ParamsPanel: numeros correntes (populacao/comida/oasis), chips por fase de
// vida e sparklines das series amostradas. `metrics` vem do state_update (agregados correntes);
// `series` e o buffer local semeado por GET /metrics/history.
import { HUD, sectionLabelStyle, sectionRuleStyle } from './hudTheme';
import Sparkline from './Sparkline';

const PANEL_STYLE = {
  color: HUD.text,
  fontFamily: HUD.fontMono,
  fontSize: '12px',
  lineHeight: 1.45,
};

const LABEL_STYLE = { color: HUD.textDim, fontFamily: HUD.fontUi, fontSize: '11px' };

const HINT_STYLE = {
  color: HUD.textDim,
  fontFamily: HUD.fontUi,
  fontSize: '11px',
};

// Numero corrente com label em cima (linha Populacao / Comida / Oasis).
const Stat = ({ label, value }) => (
  <div style={{ flex: 1, textAlign: 'center' }}>
    <div style={LABEL_STYLE}>{label}</div>
    <div style={{ fontWeight: 700, fontSize: '14px' }}>{value}</div>
  </div>
);

// Chip de fase de vida com contagem (EGG/JUV/ADU/ELD).
const StageChip = ({ label, count }) => (
  <span style={{
    flex: 1,
    textAlign: 'center',
    padding: '2px 0',
    borderRadius: 4,
    fontSize: '10px',
    fontFamily: HUD.fontMono,
    backgroundColor: count > 0 ? HUD.accentSoft : 'rgba(230,244,239,0.08)',
    color: count > 0 ? HUD.text : HUD.textDim,
  }}>
    <span style={{ color: HUD.textDim }}>{label}</span> {count}
  </span>
);

// Sparkline com titulo e valor corrente ao lado.
const MetricSpark = ({ label, value, data, color }) => (
  <div style={{ marginTop: 8 }}>
    <div style={{ ...LABEL_STYLE, marginBottom: 2, display: 'flex', justifyContent: 'space-between' }}>
      <span>{label}</span>
      <span style={{ color: HUD.text, fontFamily: HUD.fontMono }}>{value}</span>
    </div>
    <Sparkline data={data} color={color} />
  </div>
);

const MetricsPanel = ({ metrics, series }) => {
  if (!metrics) {
    return <div style={HINT_STYLE}>Aguardando dados da simulacao.</div>;
  }

  const stages = metrics.stage_counts || {};
  const samples = Array.isArray(series) ? series : [];
  const pick = (key) => samples.map((s) => s[key]);

  return (
    <div style={PANEL_STYLE}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 7 }}>
        <Stat label="Populacao" value={metrics.population ?? 0} />
        <Stat label="Comida" value={metrics.food_count ?? 0} />
        <Stat label="Oasis" value={metrics.oases_count ?? 0} />
      </div>

      <div style={{ display: 'flex', gap: 4 }}>
        <StageChip label="EGG" count={stages.EGG ?? 0} />
        <StageChip label="JUV" count={stages.JUVENILE ?? 0} />
        <StageChip label="ADU" count={stages.ADULT ?? 0} />
        <StageChip label="ELD" count={stages.ELDER ?? 0} />
      </div>

      <MetricSpark
        label="Populacao"
        value={metrics.population ?? 0}
        data={pick('population')}
        color={HUD.accent}
      />
      <MetricSpark
        label="Energia media"
        value={(metrics.avg_energy ?? 0).toFixed(1)}
        data={pick('avg_energy')}
        color={HUD.accent}
      />
      <MetricSpark
        label="Nascimentos"
        value={metrics.births_total ?? 0}
        data={pick('births_total')}
        color={HUD.accent}
      />
      <MetricSpark
        label="Mortes"
        value={metrics.deaths_total ?? 0}
        data={pick('deaths_total')}
        color={HUD.warm}
      />

      <div style={sectionLabelStyle}>
        Linhagem <span style={sectionRuleStyle} />
      </div>

      <div style={{ display: 'flex', gap: 6, marginBottom: 4 }}>
        <Stat label="Max Geração" value={metrics.max_generation ?? 0} />
        <Stat label="Extinções" value={metrics.extinctions_total ?? 0} />
      </div>

      <MetricSpark
        label="Geração média"
        value={(metrics.avg_generation ?? 0).toFixed(2)}
        data={pick('avg_generation')}
        color={HUD.accent}
      />
      <MetricSpark
        label="Sobrevida média"
        value={(metrics.avg_lifespan ?? 0).toFixed(1)}
        data={pick('avg_lifespan')}
        color={HUD.warm}
      />
    </div>
  );
};

export default MetricsPanel;
