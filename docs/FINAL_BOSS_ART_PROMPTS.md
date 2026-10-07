# Prompts del arte del Jefe Final

Generación: 2026-10-07, herramienta integrada `image_gen` (habilidad `imagegen`). No se usó CLI ni una API key del proyecto. Las seis imágenes son entregables individuales; el fondo atmosférico forma parte del PNG. La sexta, el jefe victorioso, se añadió por pedido posterior.

Salida inicial verificada: cinco PNG de 1254 × 1254 píxeles, entre 2,24 y 2,67 MB por archivo. La herramienta devolvió esa resolución para la solicitud cuadrada; se conservaron los originales sin conversión. La validación del sexto PNG se registra en su sección.

## Dirección visual y referencias

Se inspeccionaron `assets/hisopos/hisopo-gigante.png`, `hisopo-frenetico.png` e `hisopo-bomba.png` como referencias de estilo: un único hisopo doble, algodón blanco, diagonal ascendente, render fantástico detallado y fondo atmosférico, sin texto. La fase 1 establece la identidad del Jefe Final: eje negro de obsidiana, ornamentos dorados y núcleo circular de amatista. Las otras cinco imágenes se generaron usando ese PNG como referencia explícita para conservar la identidad.

Los números de fase, reglas, contadores, acertijos y botones pertenecen a Telegram; ninguna imagen los incorpora. La imagen derrotada representa la victoria del grupo. La imagen victoriosa muestra al jefe ganador cuando el grupo pierde o vence el plazo. El resultado y los puntos se aclaran en el caption.

## Validación visual

Se revisaron individualmente las cinco imágenes iniciales: silueta e identidad consistentes, ambos extremos de algodón legibles, sin texto, números, rostros o extremidades. La fase 2 incorpora energía y movimiento; la fase 3 usa anillos ordenados; la fase 4 expone un núcleo inestable; el estado derrotado conserva el hisopo quebrado e inactivo. No se recortó, redimensionó ni recompuso la salida de la herramienta. La revisión del jefe victorioso se registra en su sección.

## Prompts finales

### Fase 1: imponente y cooperativo

Archivo: `assets/hisopos/hisopo-jefe-final-fase-1.png`.

Generación inicial sin imagen de entrada.

```text
Use case: stylized-concept.
Asset type: square collectible creature illustration for a Telegram cotton-swab game, phase 1 of a final boss.
Create one 1024x1024 standalone polished fantasy 3D illustration, no text anywhere.
Subject: ONE enormous double-ended cotton swab, instantly recognizable as a real cotton swab with two large clean white fluffy oval cotton tips. Shaft is dark obsidian gunmetal with restrained antique-gold ornamented bands, and ONE circular amethyst-violet crystal core at the exact center. Long straight slender shaft, identical cotton tips, absolutely no face, eyes, mouth, limbs, person, or creature anatomy. This is an epic upgraded cotton swab, not a sword or scepter.
Composition: the complete swab floats diagonally from bottom-left to upper-right, centered, both cotton tips fully inside the square with comfortable margins, filling most of frame. Close product-like hero framing with beautifully resolved cotton fibers and metal.
Phase 1 mood: imposing, dormant power, cooperative challenge. Subtle amethyst radiance from center core, a broad faint circular halo behind the swab, a few floating dust motes, dark blue-black atmospheric backdrop. Strong soft rim lighting keeps both white cotton tips readable. Sophisticated game collectible art with realistic materials and cinematic lighting. No hands, no extra swabs, no numbers, no labels, no buttons, no interface, no frame, no watermark. The same swab design will be reused in later phases, so make its silhouette and central crystal very clear.
```

### Fase 2: frenético colaborativo

Archivo: `assets/hisopos/hisopo-jefe-final-fase-2.png`.

Referencia de identidad: `assets/hisopos/hisopo-jefe-final-fase-1.png`.

```text
Use case: identity-preserve. Asset type: square final-boss game collectible illustration. Edit the reference image to show another battle state of EXACTLY THE SAME double-ended cotton swab. Preserve the full diagonal bottom-left to upper-right framing, two distinct fluffy white oval cotton tips, straight black obsidian-metal shaft, recognizable ornate antique-gold bands and circular central amethyst core. Preserve cinematic realistic 3D fantasy material rendering and square composition. No face, eyes, mouth, limbs, humanoids, text, numerals, runes resembling text, labels, controls, buttons, UI, border, logo, watermark. One swab only; do not turn it into a weapon or a creature. PHASE 2: the final boss is overloaded and frenzied, channeling collective energy. Make the core radiate intensely violet-white, electric cyan and amber arcs race along the black shaft, and spiraling energy trails swirl behind it to communicate rapid tapping and motion. Keep both cotton tips and the central core crisply legible; any motion streaks stay in background. The same floating ancient ruins remain in the dark atmospheric backdrop but are blurred by the energy vortex. Strong dynamic contrast, visibly more active and dangerous than the calm first phase. No explosion yet, no destroyed parts.
```

### Fase 3: coordinación

Archivo: `assets/hisopos/hisopo-jefe-final-fase-3.png`.

Referencia de identidad: `assets/hisopos/hisopo-jefe-final-fase-1.png`.

```text
Use case: identity-preserve. Asset type: square final-boss game collectible illustration. Edit the reference image to show another battle state of EXACTLY THE SAME double-ended cotton swab. Preserve the full diagonal bottom-left to upper-right framing, two distinct fluffy white oval cotton tips, straight black obsidian-metal shaft, recognizable ornate antique-gold bands and circular central amethyst core. Preserve cinematic realistic 3D fantasy material rendering and square composition. No face, eyes, mouth, limbs, humanoids, text, numerals, runes resembling text, labels, controls, buttons, UI, border, logo, watermark. One swab only; do not turn it into a weapon or a creature. PHASE 3: coordinated precision. The boss has stabilized into a controlled astral mechanism; surround its amethyst core with two concentric broken rings of floating small antique-gold and obsidian segments, organized into an elegant precise circular pattern behind and around the swab. Thin violet light lines connect the organized segments, a sense of synchronization and strategic order. The dark blue ancient-ruins backdrop remains, with quieter particles. Make this phase visually distinct through geometric orderly rings, keeping the swab unobstructed and central. There must be no text, numbers, labels, glyphs, or user-interface elements on the rings. The central gem and swab remain intact.
```

### Fase 4: núcleo explosivo

Archivo: `assets/hisopos/hisopo-jefe-final-fase-4.png`.

Referencia de identidad: `assets/hisopos/hisopo-jefe-final-fase-1.png`.

```text
Use case: identity-preserve. Asset type: square final-boss game collectible illustration. Edit the reference image to show another battle state of EXACTLY THE SAME double-ended cotton swab. Preserve the full diagonal bottom-left to upper-right framing, two distinct fluffy white oval cotton tips, straight black obsidian-metal shaft, recognizable ornate antique-gold bands and circular central amethyst core. Preserve cinematic realistic 3D fantasy material rendering and square composition. No face, eyes, mouth, limbs, humanoids, text, numerals, runes resembling text, labels, controls, buttons, UI, border, logo, watermark. One swab only; do not turn it into a weapon or a creature. FINAL PHASE 4: the circular central core is exposed and critically unstable. Split open the small antique-gold housing around the original amethyst crystal, showing a bright hot white center threaded with glowing crimson-orange cracks and sparks, with faint violet remaining at crystal edges. The shaft and two cotton tips remain complete and clearly recognizable, with slight singeing near the metal collars only. A threatening dark crimson-and-violet storm surrounds the same ancient ruins. Fine embers and tension suggest an imminent explosion, but the image must still show an intact swab with a vulnerable central crystal and no actual detonation. Do not reveal any solution visually; the riddle and 20 buttons are supplied separately by the app, so do not draw text, numbered objects, controls or buttons.
```

### Victorioso: victoria del Jefe Final

Archivo: `assets/hisopos/hisopo-jefe-final-victorioso.png`.

Referencia de identidad: `assets/hisopos/hisopo-jefe-final-fase-1.png`.

Pedido adicional: mostrar al Jefe Final ganador cuando el grupo pierde, incluso si vence el plazo antes de la primera ayuda. No sustituye el arte derrotado de la colección de la Mini App.

Validación: PNG cuadrado original de 1254 × 1254 píxeles y 3.030.731 bytes, revisado visualmente. Conserva ambos extremos blancos, eje de obsidiana, ornamentos dorados y gema amatista intacta. El halo dorado y la luz estable comunican triunfo; no hay fracturas, núcleo expuesto, explosión, texto ni botones. Distinto de fase 4 y del estado derrotado. Se usó exclusivamente la herramienta integrada `image_gen`; se conserva su salida sin recortes ni conversión.

```text
Use case: identity-preserve.
Asset type: square terminal-state game illustration, THE FINAL BOSS WON and the group of players lost.
Input image: reference for the exact cotton-swab boss identity.
Edit the reference into a triumphant victorious final-boss portrait. Preserve EXACTLY this recognizable object: one double-ended cotton swab with two clean fluffy white oval cotton tips, a long straight black obsidian-metal shaft, the same ornate antique-gold collars and filigree, and one circular faceted amethyst crystal at the center. The whole swab is intact and pristine. No face, eyes, mouth, limbs, humanoid anatomy, crown accessory, trophy, or additional swabs.
Composition: complete swab floating majestically on the same bottom-left to top-right diagonal, both cotton tips fully inside a square 1254x1254 frame. Make the central crystal and white cotton tips beautifully legible at small Telegram-photo size.
Victorious mood: the boss has decisively prevailed, its power is restored, immense and fully controlled. The central amethyst is brilliant and uncracked; restrained gold light runs through its ornamentation. Behind the swab, a magnificent broad violet-and-antique-gold radiant halo with long elegant rays creates an unmistakable triumphant aura. Use a deep royal-violet atmospheric ancient-ruins background with calm golden dust drifting around the swab and subdued ruined architecture beneath it. Heroic low-angle lighting, stately symmetry in the light halo, crisp rich materials, realistic cotton fibers, cinematic highly polished fantasy 3D rendering. Stronger and more radiant than the first-phase reference, but stable and composed rather than frenzied or unstable.
No cracks, no broken housing, no exposed dangerous core, no explosion, no unstable red sparks, no defeated pose, no fallen object. No text, letters, numbers, labels, symbols resembling writing, controls, buttons, UI, border, logo or watermark. This picture will be used whenever the boss survives and the group loses, including a timeout with no participation.
```

### Derrotado: victoria del grupo

Archivo: `assets/hisopos/hisopo-jefe-final-derrotado.png`.

Referencia de identidad: `assets/hisopos/hisopo-jefe-final-fase-1.png`.

```text
Use case: identity-preserve. Asset type: square final-boss game collectible illustration. Edit the reference image to show another battle state of EXACTLY THE SAME double-ended cotton swab. Preserve the full diagonal bottom-left to upper-right framing, two distinct fluffy white oval cotton tips, straight black obsidian-metal shaft, recognizable ornate antique-gold bands and circular central amethyst core. Preserve cinematic realistic 3D fantasy material rendering and square composition. No face, eyes, mouth, limbs, humanoids, text, numerals, runes resembling text, labels, controls, buttons, UI, border, logo, watermark. One swab only; do not turn it into a weapon or a creature. DEFEATED / TERMINAL STATE: the battle has ended. Show this same ornate double-ended cotton swab fallen diagonally onto a dark stone surface. Its shaft is snapped immediately beside the central circular crystal housing, with the two pieces slightly separated while still aligned along the original diagonal so the recognizable overall silhouette remains. The amethyst crystal is cracked and completely dark and inactive, antique-gold trim worn and slightly bent. The two fluffy white cotton tips are intact and very visible with minor grey dust, never gore. A few small glass and metal fragments rest nearby, calm settled dust, dim peaceful blue-grey light after the storm, no glowing power, no smoke hiding the object. The ancient ruin backdrop is quiet and softly out of focus. This image must communicate that the encounter is finished and remain suitable as a permanent group keepsake. No characters, text, medals, victory words, labels or UI.
```
