# MediVita UI Design System

## Principles

The interface should feel calm, trustworthy, premium, and approachable. Information hierarchy and whitespace do most of the visual work. Teal communicates action and source-enabled state; other colors are reserved for semantics.

## Tokens

| Role | Value |
| --- | --- |
| Canvas | `#F6F8FB` |
| Surface | `#FFFFFF` |
| Primary text | `#0F172A` |
| Secondary text | `#64748B` |
| Muted text | `#94A3B8` |
| Brand / hover / pale | `#0F766E` / `#115E59` / `#CCFBF1` |
| Border / light border | `#E2E8F0` / `#F1F5F9` |

Inter is bundled locally. Page titles are 28–31px, section headings 15–18px, body copy 14–15px with generous leading, and metadata 10–12px. Spacing follows a 4/8px rhythm. Cards use a 15px radius, controls about 12px, 1px borders, and restrained shadows.

## Components

- Primary buttons use solid teal, 44px height, and clear disabled states.
- Cards are white with subtle borders; hover elevation is only used when they are interactive.
- Toggles use button semantics with `role="switch"` and visible focus rings.
- Source chips are quiet teal pills. References use text initials rather than third-party logos.
- Assistant responses are document-like sections, not oversized message bubbles.
- User messages use compact, right-aligned pale teal surfaces.
- Skeletons preserve final layout; chat loading combines MediVita identity with readable placeholders.

## Responsive layout

- `>=1280px`: 240px left rail, flexible workspace, 316px context panel.
- `768–1279px`: left rail and workspace; context panel hidden.
- `<768px`: compact header, menu drawer, single-column content.
- News becomes two columns only at the large breakpoint. Health Check becomes split-panel at large sizes.

Verify at 1440, 1280, 1024, 768, and 390px. No control relies on hover alone.

## Accessibility

The app uses landmarks, semantic headings, labels, real buttons/links, switch roles, sufficient contrast, `focus-visible` styling, secure external links, polite live regions, and `prefers-reduced-motion`. All major actions are keyboard accessible.

## Screenshot capture

Run both services, use a 1440×1000 browser viewport, and capture `/chat`, `/health-check`, `/news`, and `/sources` into `docs/screenshots/`. Do not use mocked image composites; screenshots should come from the running application.
