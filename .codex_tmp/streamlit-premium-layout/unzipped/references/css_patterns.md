# CSS Premium — Referência Completa para Streamlit

## Como injetar CSS no Streamlit

```python
st.markdown("""
<style>
/* CSS aqui */
</style>
""", unsafe_allow_html=True)
```

## Ocultar elementos padrão do Streamlit

```css
/* Toolbar, decoration e header padrão */
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }

/* Rodapé padrão */
footer { display: none !important; }

/* Padding padrão do bloco principal */
.block-container { padding-top: 0 !important; }
.stMainBlockContainer { padding-top: 0 !important; }
```

## Seletores Streamlit — Referência

| Elemento | Seletor |
|---|---|
| Container principal | `[data-testid="stAppViewContainer"]` |
| Bloco de conteúdo | `[data-testid="stMainBlockContainer"]` |
| Coluna | `[data-testid="column"]` |
| Bloco horizontal (st.columns) | `[data-testid="stHorizontalBlock"]` |
| Popover container | `[data-testid="stPopover"]` |
| Popover conteúdo | `[data-testid="stPopoverBody"]` |
| Botão | `[data-testid="stBaseButton-secondary"]` |
| Botão primário | `[data-testid="stBaseButton-primary"]` |
| Input text | `[data-testid="stTextInput"] input` |
| Sidebar | `[data-testid="stSidebar"]` |

## Paleta de Cores — DietHealth

```css
:root {
  --bg-deep:    #060f18;
  --bg-card:    rgba(255,255,255,0.04);
  --border:     rgba(255,255,255,0.08);
  --green:      #1a9e6e;
  --green-light:#43c59e;
  --green-glow: rgba(26,158,110,0.35);
  --text:       #e8f0e8;
  --text-muted: rgba(255,255,255,0.5);
  --text-dim:   rgba(255,255,255,0.3);
}
```

## Tipografia Premium

```css
/* Importar no início do CSS */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700;800&display=swap');

body { font-family: 'Inter', sans-serif; }
h1, h2, h3 { font-family: 'Sora', sans-serif; }
```

## Animações

```css
/* Pulso suave para CTA principal */
@keyframes pulse-green {
  0%, 100% { box-shadow: 0 4px 16px rgba(26,158,110,0.35); }
  50%       { box-shadow: 0 6px 28px rgba(26,158,110,0.6); }
}
.cta-primary { animation: pulse-green 2.5s ease-in-out infinite; }

/* Fade in suave */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
.hero-content { animation: fadeInUp 0.6s ease-out; }
```

## Scrollbar Premium

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #1a9e6e, #43c59e);
  border-radius: 3px;
}
```

## Breakpoints Responsivos

```css
/* Desktop grande */
@media (min-width: 1200px) { ... }

/* Desktop padrão */
@media (max-width: 1080px) { ... }

/* Tablet */
@media (max-width: 900px) { ... }

/* Mobile grande */
@media (max-width: 640px) { ... }

/* Mobile pequeno */
@media (max-width: 400px) { ... }
```

## Problema: CSS não aplica

1. **Inspecionar o DOM real** com `browser_console_exec`:
   ```javascript
   document.querySelector('[class*="dh"]')?.className
   ```

2. **Verificar prefixo correto** — o HTML pode usar `dhx-`, `dh-`, `lp-`, etc.

3. **Verificar especificidade** — usar `!important` quando necessário:
   ```css
   .meu-seletor { color: red !important; }
   ```

4. **CSS conflitante** — buscar regras que sobrescrevem:
   ```bash
   grep -n 'display: none' /app/<arquivo>.py | grep -i 'topbar\|nav\|header'
   ```
