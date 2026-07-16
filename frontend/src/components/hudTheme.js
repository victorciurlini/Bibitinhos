// Tokens do HUD "bioluminescente de laboratorio" — paleta ancorada no aquario escuro da
// simulacao: vidro teal translucido + acento verde-ciano vivo (a "vida" que brilha no tanque).
// Compartilhado por ControlMenu, TimeControls, InspectorPanel e ParamsPanel para manter coesao.
export const HUD = {
  panelBg: 'rgba(9, 26, 30, 0.74)',           // vidro teal profundo
  panelBorder: '1px solid rgba(70, 229, 176, 0.16)',
  panelShadow: '0 6px 24px rgba(0, 0, 0, 0.45)',
  panelBlur: 'blur(10px)',
  radius: 10,

  accent: '#46e5b0',                          // verde-ciano bioluminescente
  accentSoft: 'rgba(70, 229, 176, 0.16)',
  accentGlow: '0 0 8px rgba(70, 229, 176, 0.55)',
  warm: '#f5a15a',                            // ambar: sinais negativos / oposto do acento
  danger: '#ff6b6b',

  text: '#e6f4ef',
  textDim: 'rgba(230, 244, 239, 0.55)',
  track: 'rgba(230, 244, 239, 0.14)',

  fontUi: "'Segoe UI', system-ui, -apple-system, sans-serif",
  fontMono: "'SFMono-Regular', 'Consolas', 'Roboto Mono', ui-monospace, monospace",
};

// Vidro base dos paineis (menu e badges).
export const panelStyle = {
  backgroundColor: HUD.panelBg,
  backdropFilter: HUD.panelBlur,
  WebkitBackdropFilter: HUD.panelBlur,
  border: HUD.panelBorder,
  borderRadius: HUD.radius,
  boxShadow: HUD.panelShadow,
  color: HUD.text,
};

// Rotulo de secao (eyebrow) — caixa alta, tracking largo, cor do acento.
export const sectionLabelStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  textTransform: 'uppercase',
  letterSpacing: '0.14em',
  fontSize: '9.5px',
  fontWeight: 600,
  color: HUD.accent,
  fontFamily: HUD.fontUi,
  margin: '13px 0 7px',
};

// Filete que acompanha o rotulo de secao (fade a partir do acento).
export const sectionRuleStyle = {
  flex: 1,
  height: 1,
  background: 'linear-gradient(to right, rgba(70,229,176,0.35), rgba(70,229,176,0))',
};

// Background do slider preenchido ate a fracao `frac` (0..1) com o acento; resto no track.
export const rangeFill = (frac) => {
  const pct = Math.max(0, Math.min(1, frac)) * 100;
  return `linear-gradient(to right, ${HUD.accent} 0%, ${HUD.accent} ${pct}%, ${HUD.track} ${pct}%, ${HUD.track} 100%)`;
};
