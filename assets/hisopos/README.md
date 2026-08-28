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

## Hisopos especiales de Stars

Estas veintiuna piezas —veinte de tienda y la histórica Estelar— son artículos visuales y no se cargan como apariciones aleatorias. Se muestran directamente desde estos PNG en la Mini App.

### Hisopo Mini

Archivo: `hisopo-mini.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Images 1 to 3 are style references for the Galerazo Bot cosmetic swab collectible set. Create a brand-new “Hisopo Mini”. Show exactly one unmistakable classic double-ended cotton swab with a deliberately tiny, very short central shaft. The complete object must be stubby and compact: the shaft between the cotton tips is only about twice the length of one cotton tip, making the whole swab visibly much shorter than a normal swab. Both pristine cotton tips remain plump, tactile and proportionally large. Use a pure black luxury studio background with a small restrained warm-white halo and sparse tiny dust motes. Polished high-detail whimsical 3D product render matching the references. Square, compact object centered diagonally, fully visible, generous safe margins emphasizing its miniature size, no cropping. Charming, premium, tiny but dignified. Ivory cotton, muted powder-blue short shaft, restrained silver fittings. No text, letters, numbers, ruler, measuring marks, people, hands, face, eyes, logos, watermark, packaging, extra objects or extra swabs. Exactly one short double-ended swab. Do not render a normal long shaft.

### Hisopo Pico

Archivo: `hisopo-pico.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Image 1 is only a real-world reference for the three specialty applicator tip shapes; Image 2 and Image 3 are style references for the Galerazo Bot cosmetic swab collectible set. Create a brand-new “Hisopo Pico”. Show exactly one unmistakable double-ended swab-like cosmetic applicator, centered diagonally from lower-left to upper-right and fully visible. Replace both ordinary cotton tips with matching compact white conical microbrush tips covered in neat, short, rounded silicone micro-spikes, inspired by the center applicator in Image 1. The two ends must read clearly as pointed textured applicator tips, not cotton balls and not sharp needles. Use a pure black luxury studio background with a restrained cool-white circular halo and sparse silver dust. Polished high-detail whimsical 3D product render matching the references. Square, one object only, strong centered silhouette, generous safe margins, no cropping. Pearl white tips, satin graphite shaft, cool silver accents. No text, letters, numbers, people, hands, face, eyes, logos, watermark, packaging, extra objects or extra swabs. Keep the tips blunt and cosmetic, with rounded micro-spikes; no weapon, gore, medical procedure or insect imagery.

### Hisopo Pala

Archivo: `hisopo-pala.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Image 1 is only a real-world reference for the three specialty applicator tip shapes; Image 2 and Image 3 are style references for the Galerazo Bot cosmetic swab collectible set. Create a brand-new “Hisopo Pala”. Show exactly one unmistakable double-ended cosmetic swab, centered diagonally from lower-left to upper-right and fully visible. Replace both ordinary cotton tips with matching soft white flat angled paddle tips: smooth compact wedge-shaped spatulas with a broad beveled face, inspired by the left applicator in Image 1. Both paddle ends must be clearly visible and symmetrical, unmistakably flat rather than pointed or teardrop shaped. Use a pure black luxury studio background with a restrained warm ivory halo and sparse bronze-silver dust. Polished high-detail whimsical 3D product render matching the references. Square, one object only, strong centered silhouette, generous safe margins, no cropping. Ivory-white paddle tips, satin pale blush shaft, restrained champagne-metal fittings. No text, letters, numbers, people, hands, face, eyes, logos, watermark, packaging, extra objects or extra swabs. The paddle tips are soft cosmetic applicators, not blades; no weapon, gore or medical procedure.

### Hisopo Gota

Archivo: `hisopo-gota.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Image 1 is only a real-world reference for the three specialty applicator tip shapes; Image 2 and Image 3 are style references for the Galerazo Bot cosmetic swab collectible set. Create a brand-new “Hisopo Gota”. Show exactly one unmistakable double-ended cosmetic swab, centered diagonally from lower-left to upper-right and fully visible. Replace both ordinary cotton tips with matching smooth white teardrop-shaped applicator tips, inspired by the right applicator in Image 1. Each end must have a clean rounded base tapering gently to a soft point, like a suspended drop, and both ends must be fully visible. Use a pure black luxury studio background with a restrained translucent aqua circular ripple and a few tiny pearly droplets. Polished high-detail whimsical 3D product render matching the references. Square, one object only, strong centered silhouette, generous safe margins, no cropping. Pearly white teardrop tips, translucent pale-aqua shaft, cool silver rim light. No text, letters, numbers, people, hands, face, eyes, logos, watermark, packaging, extra objects or extra swabs. Tips must be soft cosmetic applicators, not needles; no weapon, gore or medical procedure.

### Hisopo Rosáceo

Archivo: `hisopo-rosaceo.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Images 1 to 3 are style references for the Galerazo Bot cosmetic swab collectible set. Create a brand-new “Hisopo Rosáceo”. Show exactly one unmistakable classic double-ended cotton swab, centered diagonally from lower-left to upper-right and fully visible. The entire physical collectible must be genuinely pink: both cotton tips are saturated soft rose-pink fibers, the full shaft is glossy bubblegum pink, and the small fittings are muted rose metal. Do not leave any part of the swab white, gray, black or colorless. Use a pure black luxury studio background with a restrained blush-pink circular aura, velvety rose mist and sparse pink pearly particles. Polished high-detail whimsical 3D product render matching the references. Square, one object only, strong centered silhouette, generous safe margins, no cropping. Layered blush, rose, bubblegum and muted magenta on black; clearly visible soft pink cotton fibers and glossy pink shaft. No text, letters, numbers, people, hands, face, eyes, hearts, bows, flowers, logos, watermark, packaging, extra objects or extra swabs. Exactly one double-ended swab, and every part of the object itself is pink.

### Hisopo Alfiler

Archivo: `hisopo-alfiler.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Images 1 to 3 are style references for the Galerazo Bot cosmetic swab collectible set. Create a brand-new “Hisopo Alfiler”, an elegant hybrid between a cotton swab and a sewing pin. Show exactly one slender object centered diagonally and fully visible: one end has a single pristine tactile white cotton swab tip, while the opposite end narrows into one fine polished steel pin point. The shaft is slim reflective silver with one tiny muted rose-gold collar near the cotton. It must read immediately as a cotton-tipped pin, not as two separate crossed objects. Use a pure black luxury studio background with a restrained silver circular halo and sparse metallic dust. Polished high-detail whimsical 3D product render matching the references. Square, one hybrid object only, clear diagonal silhouette, generous safe margins, both cotton and point safely inside frame. Silver steel, white cotton, tiny muted rose-gold accent. No text, letters, numbers, people, hands, face, eyes, blood, skin, medical procedure, logos, watermark, packaging, thread, buttons, extra pins, extra swabs or extra objects. The point is visually fine but the image is decorative and nonviolent; no weapon framing.

### Hisopo Sereno

Archivo: `hisopo-sereno.png`

> Use case: stylized-concept. Asset type: square premium game collectible. Create a calm, elegant double-ended cotton swab called “Hisopo Sereno”, centered diagonally and fully visible. Use a sage-green lacquered shaft, immaculate tactile cotton tips, a restrained circular aura, soft mist and tiny floating particles on a deep charcoal studio background. Polished whimsical 3D product render, sober low-saturation palette, generous safe margins, strong thumbnail silhouette. Exactly one swab; no text, people, hands, logos, watermark, packaging or bright neon.

### Hisopo Carmesí

Archivo: `hisopo-carmesi.png`

> Use case: stylized-concept. Asset type: square premium game collectible. Create an opulent “Hisopo Carmesí”: exactly one double-ended cotton swab with a dark crimson velvet-like shaft, warm ivory cotton tips, subtle ruby ornaments and a restrained red halo. Place it diagonally on a black-to-burgundy studio background with soft cinematic light and delicate particles. Refined, mysterious and collectible rather than violent. Generous margins; no text, people, hands, hearts, logos, watermark, packaging, gore or extra swabs.

### Hisopo Colosal

Archivo: `hisopo-colosal.png`

> Use case: stylized-concept. Asset type: square premium game collectible. Create a monumental “Hisopo Colosal”: one exceptionally thick double-ended cotton swab made from dark graphite and weathered bronze, floating diagonally above a smoky black stone-like background. Both cotton tips must remain unmistakable, oversized and richly textured. Add restrained dust, warm rim light and a powerful museum-object presence. Polished stylized 3D render, generous margins, no text, arms, people, logos, watermark, packaging, weapons or extra swabs.

### Hisopo Masivo

Archivo: `hisopo-masivo.png`

> Use case: stylized-concept. Asset type: square premium game collectible. Create a humorous but polished “Hisopo Masivo”: exactly one recognizable double-ended cotton swab with exactly two large muscular human-like arms, one attached to each side of the central shaft, flexing symmetrical biceps. The swab itself remains the torso; both cotton tips stay visible. Use warm bronze skin, a dark graphite shaft, dramatic gym-style rim lighting and a sober black background with subtle dust. Strong centered silhouette, generous margins, high-detail whimsical 3D render. No text, face, legs, extra limbs, extra swabs, logos, watermark, weapons or neon colors.

### Hisopo Mundial

Archivo: `hisopo-mundial.png`

> Use case: stylized-concept. Asset type: square premium game collectible. Create a “Hisopo Mundial”: exactly one double-ended cotton swab orbiting diagonally around a detailed luminous Earth. Use a deep black space background, restrained blue atmosphere, fine golden orbital trails and sparse stars. The swab must remain the main readable collectible with both cotton tips fully visible. Cinematic polished 3D render, generous safe margins, no text, flags, people, logos, watermark, additional planets or extra swabs.

### Isótopo

Archivo: `hisopo-isotopo.png`

> Use case: stylized-concept. Asset type: square premium game collectible. Create “Isótopo”, a playful atomic cotton swab: exactly one double-ended swab with a cool metallic blue shaft, surrounded by elegant glowing electron orbits and small restrained particles. Use a deep black laboratory-cosmic background, cyan-blue rim light and a compact nucleus-like glow centered behind the shaft. Premium stylized 3D product render, scientifically suggestive but not a diagram, generous margins. No text, radiation symbol, people, logos, watermark, medical equipment or extra swabs.

### Hisopo Infinito

Archivo: `hisopo-infinito.png`

> Use case: stylized-concept. Asset type: square premium game collectible. Create a mystical “Hisopo Infinito”: exactly one double-ended cotton swab crossing through a luminous violet-gold infinity loop made of energy. Keep both cotton tips and the full diagonal silhouette clearly visible. Use a deep black cosmic background with restrained purple nebula haze and fine stars. Polished high-detail 3D render, elegant rather than neon, generous safe margins. No text, numbers, people, logos, watermark, packaging or extra swabs.

### Hisopo Estelar

Archivo: `hisopo-estelar.png`

> Use case: stylized-concept. Asset type: square premium game collectible and exclusive membership reward. Create a regal “Hisopo Estelar”: exactly one refined double-ended cotton swab with a midnight-blue shaft, warm gold fittings and bright pearlescent cotton tips, centered diagonally inside a restrained eight-point star halo. Use a deep black celestial background with fine golden stardust and soft blue rim light. Luxurious polished 3D render, generous margins and a strong Telegram-thumbnail silhouette. No text, crowns, people, logos, watermark, packaging or extra swabs.

### Hisopo Bacteriófago

Archivo: `hisopo-bacteriofago.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Create a brand-new “Hisopo Bacteriófago” belonging to a sober dark luxury cotton-swab collectible set. Show exactly one unmistakable double-ended cotton swab centered diagonally and fully visible, reimagined with elegant bacteriophage-inspired biology: a refined geometric capsid-like crystal structure around the midpoint, delicate symmetrical tail-fiber legs attached only near the center, and subtle microscopic hexagonal motifs. Keep both pristine tactile cotton tips and the full shaft clearly recognizable. Use deep teal, muted emerald and cool silver bioluminescent accents on a solid black microscopic background, sparse floating particles, polished high-detail whimsical 3D product render, generous safe margins and a strong thumbnail silhouette. Scientific and fascinating, not diseased or frightening. No text, letters, numbers, people, hands, bacteria characters, medical gore, logos, watermark, packaging, or extra swabs. Exactly one swab; no face or eyes.

### Hisopo Invisible

Archivo: `hisopo-invisible.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork for a fictional “Hisopo Invisible”. The image must contain no cotton swab at all and no visible object shaped like a swab. Create an elegant pure-black studio scene where an invisible diagonal collectible is suggested only by an extremely restrained displacement of fine dust motes, two faint soft indentations in mist at opposite diagonal ends, and a nearly imperceptible cool-silver rim shimmer around empty space. The center remains visibly empty. Sober luxury minimalism, deep solid black background, generous negative space, polished cinematic lighting, strong conceptual joke that the collectible is invisible. No swab, no stick, no cotton tips, no silhouette, no transparent ghost object, no text, letters, numbers, people, hands, face, eyes, logos, watermark, packaging, stars, planets, or other props. Do not draw the object; show only empty space and subtle environmental evidence.

### Hisopo Cuásar

Archivo: `hisopo-cuasar.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Create a brand-new “Hisopo Cuásar” belonging to a sober dark luxury cotton-swab collectible set. Show exactly one unmistakable double-ended cotton swab centered diagonally and fully visible, aligned with the blazing axis of a distant quasar. Give it a sleek midnight graphite shaft with subtle blue-violet metallic details and bright tactile cotton tips. Behind the midpoint place a compact radiant accretion disk with two elegant narrow polar jets, one extending in each opposite direction, surrounded by sparse stars on a pure black space background. Dramatic but restrained violet, blue and warm-white lighting, polished high-detail whimsical 3D product render, generous safe margins, strong thumbnail silhouette. No text, letters, numbers, people, hands, planets, logos, watermark, packaging, weapons, gore, or extra swabs. Keep the jets secondary so the cotton swab reads first; avoid cropped tips and neon clutter.

### Hisopo Big Bang

Archivo: `hisopo-big-bang.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Create a brand-new “Hisopo Big Bang” belonging to a sober dark luxury cotton-swab collectible set. Show exactly one unmistakable double-ended cotton swab centered diagonally and fully visible at the instant a miniature universe is born behind its midpoint: a compact brilliant white-gold core expanding into a restrained spherical burst of orange, magenta, blue cosmic dust and fine star particles. The swab remains the hero, with a dark obsidian shaft, pristine tactile cotton tips, cinematic rim light, deep solid-black space background, generous safe margins, strong thumbnail silhouette, polished high-detail whimsical 3D product render. No text, letters, numbers, people, hands, planets, logos, watermark, packaging, weapons, gore, or extra swabs. Avoid covering or cropping either cotton tip; avoid oversaturated neon.

### Hisopo de Caca

Archivo: `hisopo-de-caca.png`

> Use case: stylized-concept. Asset type: square premium Telegram game collectible artwork. Create a funny but polished “Hisopo de Caca” belonging to a sober dark cotton-swab collectible set. Show exactly one unmistakable double-ended cotton swab centered diagonally and fully visible. Give the central shaft a rich dark-brown lacquer and add one small stylized glossy poop-swirl ornament wrapped around the midpoint, clearly readable and humorous, with restrained warm amber highlights. Both cotton tips remain pristine, white, tactile, and completely unobstructed. Use a pure black studio background, subtle brown dust particles, soft cinematic rim lighting, generous safe margins, strong thumbnail silhouette, high-detail whimsical 3D product render. Cute and cheeky, not disgusting: no realistic feces, stains, flies, toilet, bathroom, smell lines, gore, people, face, eyes, text, letters, logos, watermark, packaging, or extra swabs. Avoid cropping either tip and avoid oversaturated colors.

### Hisopo Dengue

Archivo: `hisopo-dengue.png`

> Use case: stylized-concept. Asset type: square ultra-premium Telegram game collectible artwork. Create a brand-new “Hisopo Dengue”, an affectionate fictional tribute collectible inspired by the visual traits of an Aedes mosquito, belonging to a sober dark cotton-swab set. Show exactly one unmistakable double-ended cotton swab centered diagonally and fully visible. Give the shaft a glossy near-black finish with elegant ivory-white segmented markings reminiscent of Aedes aegypti legs, and attach one long, slender, clearly recognizable mosquito proboscis projecting from the midpoint without obscuring the swab. Add two restrained translucent mosquito-like wings near the center for silhouette recognition, but no complete insect body. Keep both cotton tips pristine, white, tactile, and fully visible. Use a pure black background, subtle silver particles, dramatic cool rim lighting, generous safe margins, strong thumbnail silhouette and museum-grade whimsical 3D product rendering. It must look like the rarest, most expensive item in the collection: refined black, ivory, silver and a tiny muted crimson accent. No text, letters, numbers, real person, portrait, face, eyes, disease imagery, blood, bite, skin, gore, logos, watermark, packaging, or extra swabs. Avoid horror, cropping and neon clutter.

### Hisopo Galerazo

Archivo: `hisopo-galerazo.png`

Prompt final, generado con ImageGen integrado usando `galerazo-bot-icon.png`, `hisopo-dengue.png` e `hisopo-estelar.png` como referencias visuales:

> Use case: stylized-concept. Asset type: square ultra-premium Telegram game collectible artwork. Primary request: Create a brand-new “Hisopo Galerazo”, a celebratory tribute to the Galerazo Bot identity and its creator. Preserve the sober, cinematic, high-detail 3D product-render language of the referenced paid cotton-swab artworks, while using the referenced Galerazo icon only for its recognizable white-rabbit-and-black-top-hat identity. Show exactly one unmistakable double-ended cotton swab centered diagonally from lower-left to upper-right and fully visible with generous safe margins. Give it a glossy deep-black shaft with refined warm-gold fittings and pristine pearlescent white cotton tips. At the midpoint, integrate one miniature elegant black magician’s top hat with a restrained red band; from the hat emerge exactly two small stylized white rabbit ears with muted pink inner details, unmistakably evoking Galerazo without adding a face, full rabbit, mascot, person, portrait, or second object competing with the swab. Add a subtle warm-gold circular gallery halo, sparse bronze-gold dust particles, and a tiny restrained red accent on a pure black studio background. Lighting/mood: majestic, playful, affectionate and rare; museum-grade luxury, just slightly more prestigious than the Dengue collectible, but visually cohesive with the set. Composition: the cotton swab remains the clear hero, both tips unobstructed, all elements safely inside the square crop, readable as a Telegram thumbnail. Constraints: no text, letters, numbers, price, Stars currency symbol, logos, watermark, crowns, hands, people, portraits, full animal body, face, eyes, extra hats, extra ears, weapons, medical imagery, gore, packaging, or extra swabs. Exactly one double-ended cotton swab and one tiny top hat at its midpoint. Avoid neon, busy scenery, cropped tips, oversaturation and cartoon-flat rendering.
