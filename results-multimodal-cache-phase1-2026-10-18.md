# Fase 1 — caché multimodal y línea base MTP3 (2026-10-18)

**Ámbito.** Ejecución directa contra el backend local `vllmcritic`, MTP3, ventana total de 200k y cuatro slots. Los artefactos SSE/JSON completos permanecen privados: contienen respuestas y marcas temporales de la máquina. Este documento publica sólo resultados agregados y hashes de fixture.

## Integridad multimodal

Se generaron tres PNG legales y deterministas (fondo de color y texto OCR de alto contraste), y se enviaron como `data:` bytes en solicitudes reales. No se descargaron imágenes ni se usó otro modelo de visión.

| Prueba | 32k | 64k | Resultado |
|---|---:|---:|---|
| misma foto y mensajes, repetición byte-idéntica | sí | sí | misma respuesta (hash de respuesta igual) |
| continuación con historial wire completo y sin reenviar imagen | no | no | el modelo respondió, pero el grader de código no encontró `73`; no se cuenta como aprobación |
| control de historial sólo texto | sí | sí | código referido recuperado |
| mismo texto, sustitución por otra foto | sí | sí | cambió la respuesta y reconoció azul/41 |
| URL idéntica que sirve bytes distintos | — | — | **INCONCLUSIVE**: el backend no alcanzó el servidor localhost del cliente |
| dos imágenes: orden e intercambio de posición | sí | sí | color/código y orden reconocidos |
| historial largo + imagen final | sí | sí | 32,226 y 64,226 tokens de prompt reportados; verde/92 reconocido |
| 3 historias largas streaming + inyección visual cuarta | 32k | — | tres streams ya visibles antes de inyectar la cuarta; huecos máximos de peers: 1640.7, 1916.4 y 2164.0 ms |

No había activo un fixture fotográfico legal en el path comprobado; por ello **calidad fotográfica: no probada**. Los hashes de bytes de los medios se guardaron sólo en el artefacto privado. No se publicó imagen privada.

La API devolvió `prompt_tokens_details: null` para las solicitudes visuales y no expuso contador de encoder/preprocess ni contador nativo que cubra el tramo de media. Por tanto, **no se demuestra caché de media ni reuse de encoder**. Una repetición correcta o una caché de prefijo textual no equivalen a esa prueba.

## Línea base MTP3: tráfico real

Todos los streams publicados abajo incluyeron contenido visible, `usage`, `finish_reason` y `[DONE]`. TPS E2E = tokens de salida / pared completa; TPS de decode SSE se mantiene privado y es aproximado bajo MTP.

| Carga | Salida | TTFT visible | TPS E2E agregada | Residency nativa |
|---|---:|---:|---:|---|
| 512 cold / 1 | 128 | 0.432 s | 32.07 | observada |
| 512 replay / 1 | 128 | 0.057 s | 35.71 | no aplicable |
| 1024 cold / 1, tres réplicas | 256 | 0.638 / 0.625 / 0.631 s | 32.58 / 31.35 / 33.08 | observada |
| 1024 replay / 1, tres réplicas | 256 | 0.047 / 0.051 / 0.058 s | 34.65 / 33.29 / 35.52 | no aplicable |
| 8192 cold / 1 | 256 | 3.367 s | 25.37 | observada |
| 8192 replay / 1 | 256 | 0.067 s | 37.22 | no aplicable |
| 8192 cold / 2 | 256 c/u | 4.958–6.883 s | 32.33 | observada |
| 8192 cold / 4 | 256 c/u | 4.958–13.698 s | 38.69 | observada |
| 32768 cold / 1 | 128 | 13.079 s | 7.71 | observada |

Las pruebas funcionales separadas de JSON, grounded-null y argumentos exactos de tool pasaron. Esto no certifica calidad general, MMLU, estabilidad prolongada ni cuatro ventanas completas de 200k.

## Límites

- La ola C4 es contenido sintético y salida forzada: no es una afirmación de velocidad de aplicación general.
- El protocolo de URL mutable quedó inconcluso, no aprobado por un UUID o una suposición de invalidación.
- La fase MTP6, si se ejecuta, debe reutilizar estos fixtures/hashes y no modificar esta línea base.
