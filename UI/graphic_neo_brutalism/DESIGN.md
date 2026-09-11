---
name: Graphic Neo-Brutalism
colors:
  surface: '#fcf9f8'
  surface-dim: '#dcd9d9'
  surface-bright: '#fcf9f8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f6f3f2'
  surface-container: '#f0edec'
  surface-container-high: '#ebe7e7'
  surface-container-highest: '#e5e2e1'
  on-surface: '#1c1b1b'
  on-surface-variant: '#5b3f46'
  inverse-surface: '#313030'
  inverse-on-surface: '#f3f0ef'
  outline: '#8f6f76'
  outline-variant: '#e3bdc5'
  surface-tint: '#ba005c'
  primary: '#b60059'
  on-primary: '#ffffff'
  primary-container: '#e30071'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb1c5'
  secondary: '#006970'
  on-secondary: '#ffffff'
  secondary-container: '#00eefc'
  on-secondary-container: '#00686f'
  tertiary: '#735c00'
  on-tertiary: '#ffffff'
  tertiary-container: '#cea700'
  on-tertiary-container: '#4e3e00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffd9e1'
  primary-fixed-dim: '#ffb1c5'
  on-primary-fixed: '#3f001b'
  on-primary-fixed-variant: '#8f0045'
  secondary-fixed: '#7df4ff'
  secondary-fixed-dim: '#00dbe9'
  on-secondary-fixed: '#002022'
  on-secondary-fixed-variant: '#004f54'
  tertiary-fixed: '#ffe083'
  tertiary-fixed-dim: '#eec200'
  on-tertiary-fixed: '#231b00'
  on-tertiary-fixed-variant: '#574500'
  background: '#fcf9f8'
  on-background: '#1c1b1b'
  surface-variant: '#e5e2e1'
typography:
  display:
    fontFamily: Space Grotesk
    fontSize: 56px
    fontWeight: '800'
    lineHeight: 60px
    letterSpacing: -0.04em
  display-mobile:
    fontFamily: Space Grotesk
    fontSize: 38px
    fontWeight: '800'
    lineHeight: 42px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 46px
    letterSpacing: -0.03em
  headline-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '700'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Public Sans
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Public Sans
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 22px
  body-sm:
    fontFamily: Public Sans
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-lg:
    fontFamily: Space Grotesk
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 18px
    letterSpacing: 0.04em
  label-md:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.06em
  label-sm:
    fontFamily: Space Grotesk
    fontSize: 10px
    fontWeight: '800'
    lineHeight: 14px
    letterSpacing: 0.08em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  space-xxs: 0.25rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
  space-3xl: 4rem
  gutter-mobile: 1rem
  gutter-desktop: 2rem
  border-thin: 2px
  border-thick: 3px
  border-heavy: 4px
---

## Brand & Style

This design system combines high-voltage Neo-Brutalism with vintage pop-art and comic print energy. It is designed for products that reject the sea of sterile, muted SaaS templates in favor of unapologetic personality, tactile punch, and vibrant physical presence.

### Audience & Mood
- **Target Audience:** Creative professionals, next-gen digital consumers, indie hackers, media platforms, and streetwear/gaming-adjacent products demanding dynamic, memorable presentation.
- **Emotional Intent:** Confident, irreverent, electric, and hyper-legible. Every interaction feels tangible, punchy, and instantly responsive—evoking the tactile snap of vintage print ink, comic cell frames, and industrial graphic stickers.

### Design Movement
- **Neo-Brutalism x Comic Graphic:** Pure opaque surface fills, unapologetic 2px–3px jet black architectural borders, and hard 0-blur drop shadows that translate elements into physical, cut-out paper layers. The UI relies on crisp geometry, high-contrast ink lines, and saturated pop accents to guide attention with zero ambiguity.

## Colors

The palette operates on stark, high-contrast separation. Pure solid dark ink (#121212) anchors every element against high-luminance canvas planes and electric CMYK-inspired pop accents.

### Palette Architecture
- **Primary (`#ff2a85` - Neon Magenta):** High-energy primary actions, urgent badges, destructive focus states, and marquee accent panels.
- **Secondary (`#00f0ff` - Electric Cyan):** Information callouts, active indicators, secondary interactive states, and hover accents.
- **Tertiary (`#facc15` - Cyber Canary):** Warning banners, highlighting markers, badges, and attention-grabbing chips.
- **Accent Emerald (`#10b981` - Punch Lime/Emerald):** Success confirmations, positive trends, and validation states.
- **Neutral Surface Canvas (`#fef9c3` / `#fafafa` / `#ffffff`):** Cream-tinted newsprint and crisp white backgrounds that evoke comic gutters and screen-printed posters.
- **Ink Solid (`#121212` / `#000000`):** Total-contrast outline ink for all 2px/3px structural borders, text, and hard offset drop shadows.

### Usage Principles
- Avoid ambient or translucent alpha layers. Color fills are 100% solid.
- Color combinations should evoke offset lithography: combine `#facc15` with `#121212` text, or `#ff2a85` with `#ffffff` text enclosed within heavy borders.
- Backgrounds alternate between warm paper `#fafafa` for application layouts and `#fef9c3` or `#ffffff` for elevated card containers.

## Typography

Typography relies on a dual-engine hierarchy: **Space Grotesk** for punchy, industrial comic-grade display headers and action labels, paired with **Public Sans** for ultra-legible, sturdy editorial body text.

### Hierarchical Roles
- **Headlines & Display:** Space Grotesk in 700 and 800 weights delivers angular, mechanical personality. Uppercase styling is recommended for badges, category chips, and table headers.
- **Body & Longform:** Public Sans in medium (500) weight ensures that even against high-contrast outlines and vivid colors, text remains crisp, open, and effortless to read.
- **Labels & Microcopy:** Space Grotesk in 700/800 weight with wide positive letter-spacing (`0.04em` to `0.08em`) to balance the density of thick container borders.

## Layout & Spacing

The layout is structured around an intentional, rigid modular grid inspired by graphic novels and newspaper comics. Elements align cleanly into bounded panels separated by distinct gutters.

### Layout Rhythm & Breakpoints
- **Desktop (1280px+):** 12-column grid, max-width 1240px, 32px (`space-xl`) gutters, 32px safe margins.
- **Tablet (768px - 1279px):** 8-column grid, 24px (`space-lg`) gutters, 24px safe margins.
- **Mobile (320px - 767px):** 4-column grid, 16px (`space-md`) gutters, 16px margins. Cards span full width (4 columns) to retain border fidelity and internal padding.

### Panel Spacing Philosophy
- Consistent base-8 spacing scale (`space-xs` through `space-3xl`).
- Component internal padding is generous (minimum 16px to 24px) to ensure bold 2px–3px black outlines do not encroach on typography.
- Containers stack with explicit vertical margins rather than collapsible margins, preserving graphic frame separation.

## Elevation & Depth

This design system completely rejects blurred gaussian shadows, skeuomorphic bevels, and ambient depth. Elevation is communicated strictly through hard, opaque, directional offset drop shadows and thick structural ink outlines.

### Depth Mechanics
- **Shadow Direction:** Down and to the right (`45°` / `135°` axis).
- **Shadow Color & Blur:** Strict `#121212` or `#000000` with `0px` blur radius and `100%` opacity.
- **Surface Borders:** Every elevated container, card, or button must have a continuous `2px` or `3px` solid `#121212` border.

### Elevation Tiers
1. **Flat (Base Level):** `0px 0px 0px #121212` with a `2px` border. Used for inert input fields, table rows, and quiet panels.
2. **Elevated Low (Chips, Interactive Badges, Inputs on Focus):** `box-shadow: 2px 2px 0px #121212`.
3. **Elevated Default (Cards, Standard Buttons, Dialogs):** `box-shadow: 4px 4px 0px #121212`.
4. **Elevated High (Modals, Hovered Cards, Hero Elements):** `box-shadow: 6px 6px 0px #121212` to `8px 8px 0px #121212`.

### Dynamic Interaction (Tactile Depress)
- When interactive elements (buttons, pills, cards) are pressed (`:active`), transform coordinates move diagonally by `translate(3px, 3px)` while the shadow collapses to `1px 1px 0px #121212` or `0px 0px 0px #121212`. This creates a crisp, mechanical, mechanical-switch click effect.

## Shapes

The design system maintains a structured, semi-geometric aesthetic using mild corner rounding (`roundedness: 1`). Corners have a subtle `4px` (`0.25rem`) radius—softening brutalist sharpness just enough to resemble clean die-cut paper, comic book frames, and vinyl stickers without rounding into pillowy software shapes.

### Corner Rules
- **Base Components (Cards, Panels, Inputs, Modals):** `4px` border radius (`rounded-sm`).
- **Pill Elements (Chips, Category Tags, Notification Dots):** Can optionally use full radius (`9999px`) if wrapped in thick 2px borders and hard offset shadows to mimic printed buttons and badges.
- **Borders:** Crisp, sharp-joined solid ink outlines (`2px` on controls, `3px` on primary layout blocks).

## Components

### Buttons
- **Structure:** 2px to 3px solid `#121212` border, 4px border radius.
- **Primary Button:** Background in `#ff2a85` or `#00f0ff` with bold `#121212` or pure white Space Grotesk text. Hard offset shadow: `4px 4px 0px #121212`.
- **Secondary Button:** Solid white (`#ffffff`) or cream (`#fef9c3`) fill with `#121212` text and border. Hard shadow: `4px 4px 0px #121212`.
- **States:** 
  - *Hover:* Slight offset lift (`translate(-1px, -1px)` with shadow expanding to `5px 5px 0px #121212`).
  - *Active:* `translate(3px, 3px)` with shadow collapsing to `1px 1px 0px #121212`.

### Cards & Panels
- **Structure:** Crisp white (`#ffffff`) or newsprint cream (`#fafafa`) fill with a `3px` solid `#121212` border, `4px` radius, and `4px 4px 0px #121212` or `6px 6px 0px #121212` hard drop shadow.
- **Header Accents:** Cards can feature a top accent strip or colored header block (e.g. `#facc15` or `#00f0ff`) separated from the card body by an internal `2px` horizontal black line.

### Input Fields
- **Default:** Clean `#ffffff` fill, `2px` solid `#121212` border, `4px` radius, `2px 2px 0px #121212` base shadow.
- **Focus:** Border widens to `3px` solid `#121212`, shadow pops to `4px 4px 0px #00f0ff` or `#ff2a85`, outline none.
- **Labels:** Set in Space Grotesk Bold, positioned outside and above the field with crisp character.

### Badges & Chips
- **Structure:** `2px` solid `#121212` border, `2px 2px 0px #121212` offset shadow, uppercase Space Grotesk font (`10px`–`12px`).
- **Fills:** Alternating high-saturation fills (`#facc15`, `#00f0ff`, `#ff2a85`, `#10b981`) to classify categories, tags, or operational statuses.

### Checkboxes & Radio Buttons
- **Checkbox:** Square box (`20x20px`), `2.5px` solid `#121212` border, `2px 2px 0px #121212` hard shadow. Checked state fills with `#ff2a85` or `#00f0ff` featuring a chunky `#121212` checkmark vector.
- **Radio Button:** Circular outline (`20x20px`), `2.5px` solid `#121212` border, `2px 2px 0px #121212` hard shadow. Checked state reveals an inset solid black circle dot.

### Graphic Accents & Comic Flourishes (System Specials)
- **Callout Stickers:** Slanted floating badges (`transform: rotate(-2deg)` to `rotate(3deg)`) with heavy borders and contrasting fills to draw instant eyes to sales, alerts, or new features.
- **Divider Rules:** Solid `2px` or `3px` `#121212` black lines across full width, or zigzag/hash patterned dividing strips for distinct visual breaks.