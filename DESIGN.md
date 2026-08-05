---
name: Nhihad's Expense Tracker
description: A calm mobile-first personal finance workspace.
colors:
  midnight-canvas: "#051424"
  midnight-panel: "#122131"
  midnight-raised: "#1c2b3c"
  ink-light: "#e7eefb"
  muted-light: "#94a3b8"
  violet-action: "#8b5cf6"
  mint-income: "#4edea3"
  coral-expense: "#ff7f79"
  light-canvas: "#f4f7fb"
  light-panel: "#ffffff"
  ink-dark: "#172033"
typography:
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "27px"
    fontWeight: 700
    lineHeight: 1.15
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.25
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.04em"
rounded:
  sm: "12px"
  md: "18px"
  lg: "24px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.violet-action}"
    textColor: "{colors.ink-light}"
    rounded: "{rounded.pill}"
    padding: "12px 18px"
    height: "44px"
  button-income:
    backgroundColor: "{colors.mint-income}"
    textColor: "{colors.midnight-canvas}"
    rounded: "{rounded.pill}"
    height: "56px"
  button-expense:
    backgroundColor: "{colors.coral-expense}"
    textColor: "{colors.midnight-canvas}"
    rounded: "{rounded.pill}"
    height: "56px"
  input:
    backgroundColor: "{colors.midnight-raised}"
    textColor: "{colors.ink-light}"
    rounded: "{rounded.sm}"
    padding: "12px"
    height: "44px"
---

# Design System: Nhihad's Expense Tracker

## Overview

**Creative North Star: "The Pocket Ledger"**

The interface should feel like opening a precise personal ledger that happens to fit in one hand. Financial hierarchy is immediate: timeframe, cash in, cash out, net, then categories and transactions. The mobile experience is a structural design, not a desktop layout made narrower.

The system rejects generic fintech decoration and copied finance-app styling. Its personality comes from clear numbers, quiet midnight surfaces, one violet action color, and semantic mint and coral only when money direction matters.

## React implementation context

The interface is implemented as a React and TypeScript application. React owns screen composition, navigation state, accessible dialogs, local interaction state, and optimistic UI. It does not own financial parsing or persistence: those remain in the existing Python API layer and Supabase owner-scoped tables. This keeps statement-import and duplicate-protection rules in one trusted place while allowing each screen to be maintained as a focused component.

### Component boundaries

- `AppShell` owns authentication-aware layout and responsive navigation.
- `OverviewPage` owns the period summary and route into cash flow.
- `CashFlowPage` owns timeframe controls, donut selection, category drill-down, and the cash-in/cash-out/net hierarchy.
- `ActivityPage` owns the chronological feed and entry editing entry point.
- `EntryComposer` is a full-screen mobile dialog and desktop side panel.
- `ImportPage` owns the existing preview, mapping, duplicate, and commit workflow through the import API; files never enter persistent browser state.

### Responsive rules

- From 320px through 767px, use one content column, a four-item bottom bar, and a safe-area-aware money-entry dock. No horizontal scrolling is allowed.
- At 768px and above, navigation may become a sidebar and the entry composer becomes a side panel; data controls remain keyboard reachable.
- Every action is at least 44px in its smallest dimension. Dialogs lock page scroll only while open and respect `prefers-reduced-motion`.

### Tokens and icon treatment

The CSS custom properties in this document remain the source for semantic colors, radius, spacing, and motion. UI motion stays between 150 and 220ms. Category icons are inline outlined SVG React components with a consistent 1.8 stroke and a text label; neither emoji nor color alone communicates meaning.

**Key Characteristics:**

- Mobile banking familiarity with personal-dashboard depth.
- Restrained surfaces and strong information hierarchy.
- Traceable summaries, direct manipulation, and explicit system feedback.
- Responsive state motion between 150 and 220 milliseconds.

## Colors

The dark theme uses blue-tinted midnight neutrals, while light mode uses cool paper-like surfaces. Violet identifies navigation and primary actions. Mint is reserved for money in and success; coral is reserved for money out and destructive actions.

### Primary

- **Ledger Violet** (#8b5cf6): Primary actions, selected navigation, focus emphasis, and the active timeframe.

### Secondary

- **Income Mint** (#4edea3): Income values, the add-income action, and confirmed positive state.
- **Expense Coral** (#ff7f79): Expense values, the add-expense action, and destructive confirmation.

### Neutral

- **Midnight Canvas** (#051424): Default dark page background.
- **Midnight Panel** (#122131): Primary dark surface.
- **Midnight Raised** (#1c2b3c): Inputs and selected secondary surfaces.
- **Cool Paper** (#f4f7fb): Light-mode page background.
- **Light Panel** (#ffffff): Light-mode primary surface.

**The Semantic Direction Rule.** Mint and coral always communicate money direction or state. They are never decorative accents.

## Typography

**Display Font:** Inter with the system sans-serif stack
**Body Font:** Inter with the system sans-serif stack

**Character:** Numerals are compact, stable, and easy to compare. Interface language is native-feeling and avoids ornamental typography.

### Hierarchy

- **Headline** (700, 27px, 1.15): App and major screen titles.
- **Title** (700, 18px, 1.25): Section and composer titles.
- **Body** (400, 14px, 1.5): Explanations, transactions, and form content.
- **Label** (600, 12px, 0.04em): Compact metadata and control labels.

**The Number First Rule.** Financial figures receive weight before scale. Oversized hero metrics are prohibited.

## Elevation

The system is flat by default. Depth comes from tonal surface steps and one-pixel borders. Shadows appear only on anchored overlays, the mobile composer, or focused floating actions.

### Shadow Vocabulary

- **Anchored Lift** (`0 18px 48px -24px rgba(0,0,0,.65)`): Full-height composer and floating action dock only.
- **State Lift** (`0 10px 24px -20px rgba(0,0,0,.7)`): Hover or active state on desktop.

**The Flat Ledger Rule.** If every section casts a shadow, hierarchy has failed.

## Components

### Buttons

- **Shape:** Pill for primary actions and gently rounded rectangles (12px) for utilities.
- **Primary:** Ledger Violet with 44px minimum height.
- **Income / Expense:** Mint and coral actions use text plus signs, never color alone.
- **Hover / Focus:** Border or brightness change with a visible three-pixel focus ring.

### Chips

- **Style:** Compact rounded filters on a raised neutral surface.
- **State:** Selected filters use Ledger Violet; unselected filters remain neutral.

### Cards / Containers

- **Corner Style:** 18px for sections, 24px only for the central cash-flow visualization.
- **Background:** Solid tonal surfaces, never decorative blur.
- **Border:** One-pixel quiet border.
- **Internal Padding:** 16px on phones and 20 to 24px on larger screens.

### Inputs / Fields

- **Style:** Solid raised surface, visible label, 12px radius, 44px minimum height.
- **Focus:** Violet border plus a visible focus ring.
- **Error / Disabled:** Error text is explicit; disabled state reduces contrast but remains legible.

### Navigation

Desktop uses the existing sidebar and page tabs. Phones use a four-destination bottom bar: Overview, Activity, Plans, and More. The selected item uses icon, label, and color together. Persistent money-entry actions sit above the safe-area inset and never cover scrollable content.

### Cash-Flow Donut

The donut is a control as well as a chart. Its center always shows cash in, cash out, and net. A selected segment updates the category detail below without removing the core totals. Every segment has a keyboard-accessible equivalent in the category list.

Cash flow lives on a dedicated mobile child page rather than inside the Overview landing screen. Overview provides a compact period summary and a clearly labelled route into Cash flow. The child page owns timeframe navigation, the donut, category focus, and transaction drill-down; it preserves the bottom navigation and money-entry dock, and uses a conventional back control plus the `#cash-flow` deep link.

## Do's and Don'ts

### Do:

- **Do** keep all essential phone actions at least 44 by 44 pixels.
- **Do** keep cash in, cash out, and net visible before secondary analytics.
- **Do** pair category color with an icon and text label.
- **Do** preserve the same category colors and names across charts, lists, and forms.
- **Do** respect reduced-motion preferences and safe-area insets.

### Don't:

- **Don't** squeeze desktop tabs or wide financial tables into a phone viewport.
- **Don't** copy a mint-green finance app or use a generic navy-and-gold fintech theme.
- **Don't** use decorative glass, gradient text, gradient buttons, or background blur.
- **Don't** use colored side-stripe borders on cards or list rows.
- **Don't** hide meaning behind color-only controls or tiny icon-only actions.
