# Artes del Recolector de Hisopos

Esta carpeta conserva las imágenes fuente del juego. Telegram no recibe estos archivos desde disco en cada aparición: el bot reenvía cada foto mediante su `file_id` persistente.

Para cargar un arte nuevo:

1. Enviarlo al bot de pruebas como **foto**, no como archivo o documento.
2. Responder esa foto con `/debug`.
3. Copiar el `file_id` de la última entrada de `message.photo`, que es el tamaño mayor. No usar `file_unique_id`.
4. Guardarlo en la variable `TELEGRAM_HISOPO_*_FILE_ID` correspondiente y reiniciar el bot local.

## Hisopo gigante cooperativo

Archivo: `hisopo-gigante.png`

Prompt final, generado con ImageGen integrado usando `hisopo-comun.png`, `hisopo-gemelo.png` e `hisopo-diamante.png` solamente como referencias visuales:

> Use case: stylized-concept. Asset type: square Telegram game collectible image. Create a brand-new “Hisopo Gigante cooperativo” image belonging to the same collectible set as the three references. Use the same clean pale blue-to-warm-white luminous studio gradient, sparse white star sparkles and soft floor shadow. Show one truly colossal double-ended cotton swab, visibly thicker and more monumental than the normal swab, diagonally composed, with a deep cobalt-blue shaft and subtle intertwined luminous bands suggesting many people contributing together. Add a restrained ring of small abstract glowing handprint-like marks or linked light points, symbolic and secondary. Polished whimsical 3D product illustration, tactile cotton fibers, premium game collectible art, generous margins and an unmistakable Telegram-thumbnail silhouette. Soft celestial cooperative blue-violet glow. No text, numbers, people, faces, logos or watermark; exactly one double-ended cotton swab. Avoid weapons, medical gore, packaging, busy scenery and dark horror aesthetics.

## Hisopo milagroso

Archivo: `hisopo-milagroso.png`

Prompt final, generado con ImageGen integrado usando las mismas tres referencias visuales:

> Use case: stylized-concept. Asset type: square Telegram game collectible image. Create a brand-new “Hisopo Milagroso” image belonging to the same collectible set and communicating an exceptionally rare fixed +15-point blessing. Use the same clean pale blue-to-warm-white luminous studio gradient, sparse white star sparkles and soft floor shadow. Show exactly one elegant double-ended cotton swab with a pearly white shaft infused with warm gold and subtle opalescent rainbow light. Both cotton tips glow softly, surrounded by a restrained circular halo of tiny radiant particles suggesting extraordinary good fortune without religious symbols. Polished whimsical 3D product illustration, tactile cotton fibers, luminous pearl-and-gold materials, generous margins and a strong Telegram-thumbnail silhouette. No text, numbers, people, faces, religious icons, logos or watermark; exactly one double-ended cotton swab. Avoid angel figures, crosses, medical gore, packaging, busy scenery and dark horror aesthetics.

## Hisopo bomba

Archivos:

- `hisopo-bomba.png`: aparición activa y tablero 4x4.
- `hisopo-bomba-desactivado.png`: resultado de desactivación.
- `hisopo-bomba-explotado.png`: resultado de explosión.

Prompt final de la aparición activa, generado con ImageGen integrado en modo `stylized-concept`:

> Use case: stylized-concept. Asset type: square Telegram game collectible artwork. Primary request: Create a polished "Hisopo bomba" (bomb swab): a single cotton swab transformed into a dangerous cartoon bomb mechanism, with a matte black central stick, subtle metallic bands, a short lit fuse attached near the center, tiny red warning lights, and tense sparks. The cotton tips remain clearly recognizable and white. Scene/backdrop: dark smoky navy-to-charcoal gradient with a restrained red-orange glow behind the swab. Subject: one cotton swab only, centered diagonally from lower-left to upper-right, large and fully visible. Style/medium: high-detail stylized 3D product render, soft plush cotton texture, polished game collectible art, matching the clean luminous visual language of the project's other swab artworks. Composition/framing: square, generous safe padding, strong centered silhouette, no cropping. Lighting/mood: cinematic rim light, suspenseful but playful rather than realistic violence. Color palette: matte black, charcoal, deep navy, restrained red and orange accents, white cotton tips. Constraints: no text, no letters, no numbers, no buttons, no people, no logos, no watermark, exactly one cotton swab, image must work as a Telegram photo.

Prompt final de edición para la versión desactivada, generado en modo `precise-object-edit` sobre la aparición activa:

> Use case: precise-object-edit. Asset type: square Telegram game collectible artwork, successful bomb-defusal state. Primary request: Transform this exact bomb swab into its safely defused version. Changes: extinguish and neatly cut the fuse; change the central warning light from red to a calm green; remove all active sparks and red danger glow; add a restrained cool green-blue success glow and a few subtle clean sparkles. Keep the bomb mechanism intact but clearly harmless and powered down. Constraints: preserve the exact cotton swab, diagonal composition, scale, textures, square framing and dark backdrop; no text, letters, numbers, buttons, people, logos or watermark.

Prompt final de edición para la explosión, generado en modo `precise-object-edit` sobre la aparición activa:

> Use case: precise-object-edit. Asset type: square Telegram game collectible artwork, bomb-exploded failure state. Primary request: Show this exact bomb swab at the instant just after it explodes. Changes: replace the central mechanism with a playful orange-red fireball and smoky burst; separate the swab into two recognizable diagonal halves with lightly charred broken edges; add sparks, embers and curling dark smoke while keeping both white cotton tips visible. The result should read instantly as an exploded game collectible, dramatic but not graphic. Constraints: preserve square framing, centered silhouette, dark navy backdrop and polished stylized 3D visual language; no gore, text, letters, numbers, buttons, people, logos or watermark.

## Hisopo frenético

Archivo: `hisopo-frenetico.png`

Prompt final, generado con ImageGen integrado en modo `stylized-concept`:

> Use case: stylized-concept. Asset type: square Telegram game collectible artwork. Create a beautiful “Hisopo Frenético” for a rapid 20-tap race. Show exactly one unmistakable double-ended cotton swab, centered diagonally and fully visible, with a sleek cyan shaft, bright white tactile cotton tips and restrained orange energy accents. Surround it with elegant electric cyan and orange speed trails, small sparks and subtle motion echoes that communicate frantic repeated tapping without showing hands, buttons, text or numbers. Use a deep navy cinematic background, polished whimsical 3D product-render quality, premium game collectible lighting, strong thumbnail silhouette and generous safe margins. Energetic and playful, not violent. No letters, interface elements, people, logos, watermark, packaging or extra swabs.

## Hisopo agujero negro

Archivo: `hisopo-agujero-negro.png`

Prompt final, generado con ImageGen integrado en modo `stylized-concept`:

> Use case: stylized-concept. Asset type: square Telegram game collectible artwork. Create a beautiful “Hisopo Agujero Negro” for a competitive 20-tap race that absorbs rivals’ points. Show exactly one recognizable double-ended cotton swab crossing the luminous edge of a compact black hole, centered diagonally and fully visible. Keep both cotton tips bright and tactile while the dark graphite shaft bends subtle violet-blue light around it. Add a restrained accretion ring, elegant cosmic particles and a deep navy-to-black space background. Polished whimsical 3D product render, premium collectible art, dramatic gravitational lighting, generous safe margins and a clear Telegram-thumbnail silhouette. Mysterious and powerful but not horror. No text, numbers, people, hands, buttons, logos, watermark, planets, weapons or extra swabs.

## Hisopo vencido

Archivo: `hisopo-vencido.png`

Prompt final, generado con ImageGen integrado y refinado para eliminar marcas de reloj:

> Use case: stylized-concept. Asset type: square Telegram game collectible artwork. Create a generic “Hisopo Vencido” result image. Show exactly one old, dried-out double-ended cotton swab, centered diagonally and fully visible, with slightly yellowed frayed cotton, a faded beige shaft and a restrained dusty amber halo. Use a sober dark blue-gray background, a few drifting dust motes, soft floor shadow and polished whimsical 3D product-render quality consistent with a premium game collectible set. It should read instantly as expired and missed, not rotten gore or medical waste. Preserve generous margins and a strong thumbnail silhouette. Do not include clocks, clock hands, clock faces, numerals, tick marks, text, letters, people, logos, watermark, packaging or extra swabs.
