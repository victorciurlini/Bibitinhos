/* eslint-disable react/prop-types */
// Parametros tunaveis em runtime (BIT-23). Conteudo embutivel (renderiza inline dentro do
// ControlMenu). Recebe `params` ({nome: valor} ecoado pelo servidor) e `onCommand` (envia
// comandos WS). Metadados HARDCODADOS aqui, espelhando PARAM_SPECS do backend (params.py) — o
// state so transporta valores. Estetica bioluminescente (ver hudTheme.js).
import { useRef, useState } from 'react';
import { HUD, rangeFill } from './hudTheme';

// Espelho fiel da tabela PARAM_SPECS do backend (22 params, 4 grupos). Ordem preservada.
const PARAM_SPECS = [
  // --- Energia ---
  { name: 'idle_penalty_rate', group: 'Energia', label: 'Imposto de ociosidade (E/s)', min: 0.0, max: 5.0, step: 0.1 },
  { name: 'motor_forward_cost', group: 'Energia', label: 'Custo de propulsao (E/s)', min: 0.0, max: 5.0, step: 0.1 },
  { name: 'spin_cost', group: 'Energia', label: 'Custo de girar parado (E/s)', min: 0.0, max: 5.0, step: 0.1 },
  { name: 'movement_reference_speed', group: 'Energia', label: 'Velocidade de referencia (px/s)', min: 5.0, max: 100.0, step: 1.0 },
  { name: 'metabolism_adult', group: 'Energia', label: 'Metabolismo ADULT (E/s)', min: 0.0, max: 5.0, step: 0.1 },
  { name: 'metabolism_elder', group: 'Energia', label: 'Metabolismo ELDER (E/s)', min: 0.0, max: 10.0, step: 0.1 },

  // --- Reproducao ---
  { name: 'fertility_energy_threshold', group: 'Reproducao', label: 'Energia p/ ficar fertil', min: 0.0, max: 100.0, step: 1.0 },
  { name: 'mating_radius', group: 'Reproducao', label: 'Raio de acasalamento (px)', min: 20.0, max: 400.0, step: 10.0 },
  { name: 'reproduction_energy_cost', group: 'Reproducao', label: 'Custo do acasalamento', min: 0.0, max: 100.0, step: 1.0 },
  { name: 'reproduction_cooldown', group: 'Reproducao', label: 'Cooldown sexuado (s)', min: 0.0, max: 120.0, step: 1.0 },
  { name: 'min_energy_asexual', group: 'Reproducao', label: 'Energia minima p/ clonar', min: 0.0, max: 100.0, step: 1.0 },
  { name: 'asexual_energy_cost', group: 'Reproducao', label: 'Custo da clonagem', min: 0.0, max: 100.0, step: 1.0 },
  { name: 'asexual_cooldown', group: 'Reproducao', label: 'Cooldown da clonagem (s)', min: 0.0, max: 180.0, step: 1.0 },

  // --- Ecossistema ---
  { name: 'max_total_food', group: 'Ecossistema', label: 'Teto global de comida', min: 0, max: 300, step: 1 },
  { name: 'food_energy_value', group: 'Ecossistema', label: 'Energia por comida', min: 5.0, max: 100.0, step: 1.0 },
  { name: 'oasis_spawn_chance', group: 'Ecossistema', label: 'Chance de oasis (/frame)', min: 0.0, max: 0.1, step: 0.005 },
  { name: 'oasis_food_spawn_chance', group: 'Ecossistema', label: 'Chance de comida no oasis (/frame)', min: 0.0, max: 0.5, step: 0.01 },
  { name: 'max_active_oases', group: 'Ecossistema', label: 'Maximo de oasis ativos', min: 0, max: 12, step: 1 },
  { name: 'oasis_ttl_min', group: 'Ecossistema', label: 'TTL minimo do oasis (s)', min: 5.0, max: 120.0, step: 1.0 },
  { name: 'oasis_ttl_max', group: 'Ecossistema', label: 'TTL maximo do oasis (s)', min: 10.0, max: 180.0, step: 1.0 },

  // --- Ambiente ---
  { name: 'water_drag', group: 'Ambiente', label: 'Arrasto da agua (damping)', min: 0.05, max: 1.0, step: 0.05 },
  { name: 'vision_radius', group: 'Ambiente', label: 'Raio de visao (px)', min: 20.0, max: 200.0, step: 5.0 },
];

// Ordem dos grupos colapsaveis.
const GROUP_ORDER = ['Energia', 'Reproducao', 'Ecossistema', 'Ambiente'];

const GROUP_HEADER_STYLE = {
  display: 'flex',
  alignItems: 'center',
  gap: 7,
  cursor: 'pointer',
  padding: '5px 4px',
  marginTop: 2,
  borderRadius: 5,
  fontFamily: HUD.fontUi,
  fontSize: '11.5px',
  fontWeight: 600,
  color: HUD.text,
  userSelect: 'none',
};

const CHEVRON_STYLE = { color: HUD.accent, fontSize: '10px', width: 10 };

const ROW_STYLE = { marginBottom: 8 };

const LABEL_ROW_STYLE = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'baseline',
  gap: 6,
  fontSize: '10.5px',
  fontFamily: HUD.fontUi,
  color: HUD.textDim,
  marginBottom: 3,
};

const VALUE_STYLE = {
  color: HUD.accent,
  fontFamily: HUD.fontMono,
  fontVariantNumeric: 'tabular-nums',
};

const RESET_BUTTON_STYLE = {
  marginTop: 12,
  width: '100%',
  padding: '7px 8px',
  border: '1px solid rgba(70,229,176,0.35)',
  borderRadius: 7,
  cursor: 'pointer',
  fontFamily: HUD.fontUi,
  fontSize: '11.5px',
  fontWeight: 600,
  letterSpacing: '0.02em',
  backgroundColor: 'rgba(70,229,176,0.10)',
  color: HUD.accent,
};

// Formata o valor para exibicao: inteiro se step >= 1, senao respeita a granularidade.
const formatValue = (value, step) => {
  if (value == null || Number.isNaN(value)) return '—';
  if (step >= 1) return String(Math.round(value));
  const decimals = step >= 0.1 ? 1 : step >= 0.01 ? 2 : 3;
  return value.toFixed(decimals);
};

const ParamsPanel = ({ params, onCommand }) => {
  // Grupos colapsados por padrao (a lista e longa; o menu ja rola).
  const [openGroups, setOpenGroups] = useState({});
  // Slider sob o cursor: enquanto arrastado, exibe o valor local (nao o eco do servidor).
  const activeParamRef = useRef(null);
  const [localValues, setLocalValues] = useState({});

  const params_ = params || {};

  const toggleGroup = (group) => {
    setOpenGroups((prev) => ({ ...prev, [group]: !prev[group] }));
  };

  const handlePointerDown = (name) => {
    activeParamRef.current = name;
  };

  const handlePointerUp = () => {
    activeParamRef.current = null;
    // Limpa o valor local ao soltar: volta a seguir o eco do servidor.
    setLocalValues({});
  };

  const handleChange = (spec, rawValue) => {
    const value = Number(rawValue);
    // Enquanto arrastando, mantem o valor local para o slider nao "brigar" com o eco.
    if (activeParamRef.current === spec.name) {
      setLocalValues((prev) => ({ ...prev, [spec.name]: value }));
    }
    onCommand({ action: 'set_param', name: spec.name, value });
  };

  // Valor a exibir: o local (se arrastando este slider) ou o ecoado pelo servidor.
  const displayValue = (spec) => {
    if (activeParamRef.current === spec.name && spec.name in localValues) {
      return localValues[spec.name];
    }
    return params_[spec.name];
  };

  return (
    <div>
      {GROUP_ORDER.map((group) => {
        const specs = PARAM_SPECS.filter((s) => s.group === group);
        const open = !!openGroups[group];
        return (
          <div key={group}>
            <div
              className="hud-btn hud-group"
              style={GROUP_HEADER_STYLE}
              onClick={() => toggleGroup(group)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') toggleGroup(group); }}
              aria-expanded={open}
            >
              <span style={CHEVRON_STYLE}>{open ? '▾' : '▸'}</span>
              <span>{group}</span>
            </div>
            {open && (
              <div style={{ padding: '4px 4px 2px' }}>
                {specs.map((spec) => {
                  const value = displayValue(spec);
                  const sliderValue = value == null || Number.isNaN(value) ? spec.min : value;
                  const frac = (sliderValue - spec.min) / (spec.max - spec.min || 1);
                  return (
                    <div key={spec.name} style={ROW_STYLE}>
                      <div style={LABEL_ROW_STYLE}>
                        <span>{spec.label}</span>
                        <span style={VALUE_STYLE}>{formatValue(value, spec.step)}</span>
                      </div>
                      <input
                        type="range"
                        className="hud-range"
                        style={{ background: rangeFill(frac) }}
                        min={spec.min}
                        max={spec.max}
                        step={spec.step}
                        value={sliderValue}
                        onPointerDown={() => handlePointerDown(spec.name)}
                        onPointerUp={handlePointerUp}
                        onChange={(e) => handleChange(spec, e.target.value)}
                        aria-label={spec.label}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}

      <button
        className="hud-btn hud-reset"
        style={RESET_BUTTON_STYLE}
        onClick={() => onCommand({ action: 'reset_params' })}
        title="Restaurar todos os parametros aos valores padrao"
      >
        Restaurar padroes
      </button>
    </div>
  );
};

export default ParamsPanel;
