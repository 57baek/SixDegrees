# Features Research: SixDegrees People Map

**Domain:** Personalized social graph visualization / people-mapping systems
**Date:** 2026-02-22

---

## Table Stakes (Must Have)

Users won't understand the map without these:

### Map Basics
- **You at the center**: User always at (0,0); all others positioned relative. Without this, the map is disorienting.
- **Visible user labels**: Every dot shows at minimum a username or display name on hover/tap. Unlabeled dots are meaningless.
- **Tier visual distinction**: Color or size coding for Tier 1/2/3. Users need to immediately understand "these people are closest to me."
- **Spatial clustering**: Visually distinct clusters must be apparent — if everything looks uniformly distributed, the map fails its core promise.
- **Map loads within 2 seconds**: Precomputed coordinates (not live compute) are essential for this.

### Algorithm Correctness Signals
- **Similar profiles → close together**: The core promise. Violating this destroys trust.
- **High interaction → close together**: Secondary promise. Must visibly move dots when interaction increases.
- **Consistent relative positions**: Day-to-day, the map should feel stable with gradual drift — not random reshuffling.
- **New users appear at moderate distance**: Not at origin, not at the edge — somewhere neutral.

### Demo/Proof-of-Concept Minimum
- **Scatter plot with labeled dots**: matplotlib or similar; doesn't need to be interactive.
- **Color by tier**: Three distinct colors visible in the plot.
- **Demonstrable sensitivity**: Changing input data → visible change in dot positions.

---

## Differentiators (Competitive Advantage)

What makes SixDegrees' People Map uniquely compelling:

### The Daily Ritual
- **7pm update creates a social moment**: Unlike real-time feeds, the daily batch creates anticipation — "who moved closer today?"
- **Animation of dot transitions**: Future feature, but the architecture needs to support storing old vs new positions. Users sharing their map update as a moment is a virality mechanic.

### Bi-directional Relationships
- **Other users' relationships to each other are visible on YOUR map**: If Friend A and Friend B are close to each other on your map, you can infer they'd get along — even if they've never met. This is the "six degrees" insight made visible.

### Interaction Weighting
- **Engagement moves the map**: Following, liking, messaging someone pulls them toward you. The map becomes a record of relationship investment, not just profile overlap.

---

## Anti-Features (Deliberately Not Build)

| Feature | Why Avoid |
|---------|-----------|
| Real-time map updates | N×N t-SNE is expensive; real-time defeats the daily ritual design intent |
| "Why are you close to X?" explanation UI | Complex to implement, can feel surveillance-like; defer |
| Hiding dots from the map | Introduces moderation complexity; all users visible or none |
| Map zoom that shows raw coordinates | Raw t-SNE coords are unitless; exposing them creates confusion about distance scale |
| Friend requests triggered by map proximity | Feature creep; People Map is observational, not actional — actions come from the feed |
| Global/public map view | Everyone's map is personal and different; a global view doesn't make sense conceptually |

---

## Demo vs Production Requirements

| Feature | Demo (this milestone) | Production (future) |
|---------|----------------------|---------------------|
| Map rendering | matplotlib static plot | Interactive canvas/D3.js (frontend team's job) |
| User data | Seeded mock data | Real user profiles |
| Interaction data | Seeded mock counts | Real likes/comments/DMs |
| Scheduler | APScheduler in FastAPI | Same (or cron job in production) |
| Animation | Not built; coords stored for delta | Animated transitions between daily updates |
| Scale | 10-15 users | 100s to 1000s of users |

---
*Research written: 2026-02-22*
