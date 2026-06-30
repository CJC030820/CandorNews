---
name: NewsWise AI
colors:
  surface: '#fbf8fc'
  surface-dim: '#dbd9dc'
  surface-bright: '#fbf8fc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f6'
  surface-container: '#efedf0'
  surface-container-high: '#e9e7eb'
  surface-container-highest: '#e4e2e5'
  on-surface: '#1b1b1e'
  on-surface-variant: '#44474e'
  inverse-surface: '#303033'
  inverse-on-surface: '#f2f0f3'
  outline: '#75777f'
  outline-variant: '#c5c6cf'
  surface-tint: '#4e5e81'
  primary: '#031635'
  on-primary: '#ffffff'
  primary-container: '#1a2b4b'
  on-primary-container: '#8293b8'
  inverse-primary: '#b6c6ef'
  secondary: '#6b38d4'
  on-secondary: '#ffffff'
  secondary-container: '#8455ef'
  on-secondary-container: '#fffbff'
  tertiary: '#001a20'
  on-tertiary: '#ffffff'
  tertiary-container: '#00303a'
  on-tertiary-container: '#00a0bb'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#b6c6ef'
  on-primary-fixed: '#081b3a'
  on-primary-fixed-variant: '#364768'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#acedff'
  tertiary-fixed-dim: '#4cd7f6'
  on-tertiary-fixed: '#001f26'
  on-tertiary-fixed-variant: '#004e5c'
  background: '#fbf8fc'
  on-background: '#1b1b1e'
  surface-variant: '#e4e2e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  mono-label:
    fontFamily: monospace
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  container-max: 1440px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style

The design system is engineered for a sophisticated AI intelligence platform that prioritizes clarity, authority, and rapid information synthesis. The target audience includes analysts, journalists, and enterprise decision-makers who require deep insights into news veracity and sentiment.

The visual style is **Corporate Modern with subtle Glassmorphism**, balancing the reliability of traditional news media with the cutting-edge nature of artificial intelligence. It emphasizes a "Data-First" philosophy, where the UI recedes to let critical metrics and intelligence summaries lead. The emotional response is one of calm confidence, precision, and objectivity. High-density information is managed through generous whitespace and a rigorous hierarchy of information.

## Colors

The palette is anchored by a deep **Navy Blue** (#1A2B4B) to establish institutional trust. AI-driven features are distinguished by a gradient or interplay between **Purple** (#8B5CF6) and **Cyan** (#06B6D4), signifying intelligence and technological sophistication.

The neutral system utilizes a stark **White** background with **Soft Grey** (#F3F4F6) surfaces to create distinct content areas without heavy borders. A critical "Trust System" uses a semantic trio: **Green** for verified high-trust signals, **Yellow** for moderate uncertainty, and **Red** for high-risk or low-credibility indicators.

## Typography

This design system utilizes **Inter** across all levels to maintain a systematic, utilitarian aesthetic. The type hierarchy is intentionally steep to help users scan dense intelligence reports effectively.

- **Headlines:** Use tighter letter spacing and semi-bold weights to command attention.
- **Body:** Optimized for long-form reading with 1.5x line height.
- **Labels:** Small, uppercase, and tracked out for metadata and trust indicators.
- **Data Points:** Where precise technical data is shown (e.g., source code fragments or raw timestamps), a monospace fallback is permitted for clarity.

## Layout & Spacing

The design system employs a **Fixed Grid** model for desktop dashboards to ensure data visualizations remain consistent. The core layout uses a 12-column grid with 24px gutters.

- **Desktop (1200px+):** Sidebar navigation (fixed at 280px) + fluid content area with a 1440px max-width container.
- **Tablet (768px - 1199px):** Sidebar collapses to icons; margins reduce to 24px.
- **Mobile (below 768px):** Single-column vertical stack; margins reduce to 16px. Typography scales down (e.g., `headline-lg-mobile`).

Spacing follows a 4px baseline, with 16px and 24px being the most common increments for internal card padding and element grouping.

## Elevation & Depth

Depth is conveyed through **Tonal Layers** supplemented by **Ambient Shadows**.

1.  **Background:** Pure White (#FFFFFF).
2.  **Surfaces:** Soft Grey (#F3F4F6) is used for the dashboard background to make white cards pop.
3.  **Cards & Modals:** Use a multi-layered shadow (0px 4px 20px rgba(26, 43, 75, 0.05)) to create a soft, lifelike lift.
4.  **AI Elements:** Utilize a subtle "inner glow" or backdrop-blur effect (Glassmorphism) when overlaid on data visualizations to highlight AI-generated insights.
5.  **Interactivity:** Hover states for cards increase shadow spread and decrease opacity, simulating a "floating" effect.

## Shapes

The shape language is defined by **Rounded** corners to soften the professional tone and make the platform feel modern and accessible.

- **Standard Elements:** 0.5rem (8px) for buttons, inputs, and small widgets.
- **Cards & Major Blocks:** 1rem (16px) as requested, creating a friendly "containerized" look.
- **Badges & Trust Indicators:** 1.5rem (24px) or full pill-shape for high-glanceability and distinction from square-ish content.

## Components

### Buttons & Inputs
- **Primary Button:** Solid Navy Blue with white text, 8px roundedness.
- **AI Action Button:** Gradient background (Purple to Cyan) with a subtle glow.
- **Input Fields:** Soft Grey background with a 1px border that turns Cyan on focus.

### Trust & Intelligence Indicators
- **Trust Score Badges:** Pill-shaped, high-contrast labels using the semantic color system (Green/Yellow/Red). Use a light tinted background with dark text for accessibility.
- **Match Percentage Gauges:** Circular SVG strokes. The "track" is Soft Grey; the "progress" uses the Cyan/Purple gradient.
- **Explainable Trust Panels:** These are secondary containers within cards using a very light 1px border and a subtle background tint of the trust color (e.g., 5% Red tint for risk panels).

### Content Blocks
- **AI Summary Blocks:** Distinguished by a "Glass" effect and a thin left-border gradient of Purple/Cyan. Includes a "Generated by AI" label in `label-md`.
- **News Cards:** 16px rounded corners, White background, soft shadow. Headlines use `headline-sm`. Sentiment labels (Positive/Neutral/Negative) are placed in the top-right corner using small, low-saturation chips.