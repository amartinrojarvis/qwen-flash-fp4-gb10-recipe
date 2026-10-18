# Multimodal integrity — corrected v2 / Integridad multimodal — v2 corregida

Measured evidence: [summary.json](benchmarks/runs/2026-10-18-multimodal-cache-v2/summary.json). These are completed MTP3 measurements, not MTP6 results. No inference or runtime change was performed while preparing this publication.

## Español

Las once solicitudes registradas completaron con `stop` y aprobaron sus contratos de integridad dentro de esta fixture sintética. La primera lectura y la repetición devolvieron `RIVERA 73`; la continuación del historial recuperó el mismo texto. Sustituir la imagen produjo `AZUL 41`. Las tres pruebas posicionales aprobaron tras regrado offline del color (nombre español/inglés o hexadecimal con canal dominante), sin repetir inferencia y conservando los grados originales.

La misma URL sirvió dos cuerpos distintos registrados por el servidor, y las respuestas cambiaron correctamente de rojo/73 a azul/41. El fallo anterior `list index out of range` procedía del registrador, que trataba una URL HTTP como si fuera un data URI; no probaba que el backend fuera incapaz de acceder al servidor.

La pregunta original sobre «el código» era ambigua: el modelo respondió con el hexadecimal del color que había descrito previamente. La nueva pregunta pide inequívocamente el texto impreso. Ese caso anterior no demuestra pérdida de la imagen por caché.

El caso con texto largo e imagen al final reportó 32.226 tokens de entrada y reconoció `VERDE 92`. Esto no acredita reutilización de un prefijo largo que contenga medios históricos. La API no expuso tokens cacheados por solicitud ni métricas de encoder: **la reutilización del encoder o de estado visual sigue inconclusa**. En las solicitudes no streaming el TTFT no se midió; el JSON conserva `null` y duración total por separado.

El ensayo visual mixto anterior observó pausas de 1.641, 1.916 y 2.164 segundos: un peer excedió el umbral de 2 segundos. Se conserva ese límite, sin convertirlo en una aprobación global de fluidez. Calidad fotográfica, vídeo y MTP6 siguen sin calificarse; MTP6 permanece pausado para permitir el trabajo normal.

## English

All eleven recorded requests completed with `stop` and passed the scoped synthetic integrity contracts. Initial OCR, exact replay and the real-history follow-up recovered `RIVERA 73`. Replacing pixels changed the answer to `AZUL 41`. The three position/order cases passed an offline grader revision accepting explicit equivalent color encodings; original grades are retained and no inference was repeated for that revision.

The same URL served two different recorded byte bodies, and answers changed correctly from red/73 to blue/41. The earlier URL failure was a metadata-parser error, not evidence of network unreachability. The earlier “code” question was ambiguous between printed OCR and a hexadecimal color; the new fixture explicitly requests printed text.

The long-text-plus-final-image request reported 32,226 prompt tokens and recognized `VERDE 92`. This does not establish retained reuse of a long media-bearing prefix. Per-request cached-token details and encoder metrics were unavailable, so **media/encoder reuse remains inconclusive**. Nonstreaming TTFT remains unknown rather than being substituted with total duration.

One peer in the separate earlier mixed visual workload exceeded the declared two-second gap threshold. No general photographic quality, video, engine superiority or MTP6 speedup is claimed. MTP6 is still unrun and paused. See the JSON for actual timing, usage, hashes and original/revised grading evidence.
