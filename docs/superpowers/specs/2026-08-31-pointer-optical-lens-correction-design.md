# RouteMind Pointer Optical Lens Correction

**Task:** RM-246
**Status:** Approved for implementation
**Primary reference:** Codrops, "Pointer Square Lens Distortion with RGB Shift"

## Problem

The RM-245 pointer lens is a DOM overlay built from `backdrop-filter`, a border, and two
chromatic edge pseudo-elements. It communicates a selected area but does not refract the
rendered geographic world. Its behavior therefore reads as an inspection outline instead
of the physical square optical lens demonstrated by the approved Codrops reference.

## Decision

RouteMind will replace the DOM lens with a MapLibre custom WebGL2 layer mounted after the
interleaved Deck.gl operational overlay. The layer copies the already-composited map
framebuffer into one reusable texture and renders only the square lens area with:

- the Codrops CC Lens radial UV displacement;
- a square local-UV mask with only a very small softened edge;
- radial red, green, and blue sample separation;
- channel separation driven by the smoothed pointer velocity;
- a restrained optical clarity response inside the lens;
- premultiplied-alpha compositing back into the same WebGL context.

This preserves one persistent canvas and one renderer ownership boundary. Pointer samples
remain in refs and render-loop objects; React does not receive per-frame state updates.

## Data Flow

`OperationsMotionCoordinator` remains the pointer sampler. It converts native pointer
events into an eased screen position, velocity, target classification, and interaction
energy. `GeoWorldController.setPointerFrame` maps that screen position into the persistent
map viewport and passes a compact frame to the optical layer. The optical layer converts
CSS pixels to drawing-buffer pixels and requests a MapLibre repaint only while the lens is
active or fading.

Controls, links, inputs, chart labels, accessibility affordances, and all non-scene pointer
targets deactivate the lens. The native cursor remains unchanged.

## Motion And Accessibility

Normal motion uses the existing `0.13` pointer easing, close to the reference's `0.1`
interpolation. RGB displacement rises with velocity and acceleration, remains moderate
during ordinary movement, and eases to nearly zero at rest.

Reduced motion keeps the square optical lens available as a static inspection surface but
sets chromatic separation to zero. It does not replace WebGL with the fallback. The existing
fallback remains reserved for WebGL2 or map initialization failure.

## Lifecycle And Performance

The custom layer owns one program, one vertex array, one fullscreen triangle buffer, and one
capture texture. It reallocates the texture only when the drawing buffer changes size and
deletes every resource in `onRemove`. Lens rendering is skipped when fully inactive. Device
pixel ratio remains limited by the existing MapLibre configuration.

No second canvas, second renderer, readback, React render loop, or additional chart/scene
dependency is introduced.

## Intentional Differences From Codrops

The reference demonstrates the lens over static editorial media and makes the outside image
grayscale with a wave/noise treatment. RouteMind keeps the geographic world outside the lens
unchanged so roads, controls, SLA status, and operational colors remain readable. It also
suppresses the lens over critical UI and disables velocity chromatic separation under
reduced motion. The square optical refraction, radial RGB separation, smooth tracking, and
transient physical response remain direct adaptations of the reference behavior.

## Source And License

The shader math and interaction structure are adapted from the MIT-licensed
`tomoyukinakata/mouse-following-square-lens-effect` project linked by Codrops. RouteMind does
not copy the reference branding, text, images, or artwork. The upstream attribution and MIT
license text are retained in `apps/web/THIRD_PARTY_NOTICES.md`.

## Visual Gates

The checkpoint requires side-by-side browser inspection with the Codrops demo and RouteMind.
Evidence must show a recognizably square following lens, real local refraction over map and
Deck.gl content, velocity-sensitive RGB separation, smooth decay, UI exclusion, normal and
reduced-motion behavior, one canvas, no console errors, and usable 1280, 1024, and 760 pixel
wide compositions. A CSS outline, glow, tooltip, or simple magnifier is a failed result.
