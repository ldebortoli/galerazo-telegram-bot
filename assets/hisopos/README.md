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
