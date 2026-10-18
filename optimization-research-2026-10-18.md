# Investigación de fluidez FP4 local (solo lectura/CPU)

**Alcance.** Inspección de configuración/proceso ya existentes, código instalado y receta anclada, más documentación oficial. No se lanzó inferencia, benchmark, compilación, descarga, cambio de configuración ni acceso GPU.

## Estado efectivo verificado

- El proceso real `vllm serve` del contenedor existente termina en `--max-num-seqs 4` y `{"method":"mtp","num_speculative_tokens":3}`. Aunque el vector conservado contiene antes `8` y MTP4, los últimos argumentos son los efectivos para el parser; por tanto el runtime actual es **MTP3 / cuatro secuencias**, `max_model_len=200000`, `max_num_batched_tokens=4096`, prefill por chunks y prefix cache.
- Identidad inspeccionada: imagen `eugr/spark-vllm-b12x@sha256:03a956…7bb3595`; receta `0bdc9c94cd89843e1c8f7d7b33df2d5bc746c03d`; paquete instalado `vllm 0.1.dev21830+g8244d1c44.d20261015`. El árbol fuente instalable no trae `.git`; por eso las referencias de código efectivo incluyen ruta, líneas y SHA-256 de archivo.
- El checkpoint declara `text_config.mtp_num_hidden_layers=1` y contiene un predictor MTP. Eso **no es** una afirmación de “solo MTP1”: profundidad especulativa es `num_speculative_tokens`; el predictor se encadena/ejecuta para proponer. Tampoco prueba por sí solo calidad/aceptación a profundidad 6.

## MTP6 frente a MTP3

### Mecanismo y lo que sí soporta el stack

MTP no acelera el prefill de una conversación fría: propone varios tokens durante **decode**, que el target verifica. Su objetivo es reducir latencia entre tokens con carga media/baja y limitada por memoria; no es una solución para TTFT de un prompt de 200k.[2] `num_speculative_tokens` es la profundidad máxima propuesta.[1]

**MTP6 es plausible, pero no validado aquí:**

1. La implementación efectiva del GDN b12x fija `MAX_FUSED_GDN_MTP_TOKENS = 8` y permite la ruta fusionada cuando el ancho `state_indices` es `<= 8` (`.../mamba/gdn/qwen_gdn_linear_attn.py:197, 2829–2833`, SHA-256 `92609be4…e956c`). MTP6 cae dentro de ese límite de ruta, a diferencia de una profundidad mayor que 8.
2. El parche anclado de QSA contiene pruebas explícitas para profundidades 5–8 y explica que el ring se ensancha a 16 filas con bloque 16; su SHA-256 es `dc7a28c1…aaef71`, líneas 48–64 y 97–136 del parche `05-pr54912.patch`. Esto respalda que la receta fue preparada para 5–8 en esa pieza concreta, no una cualificación end-to-end MTP6.
3. La ruta MTP NVIDIA efectiva lee `mtp_num_hidden_layers`, exige al menos un predictor y remapea sus capas cuantizadas (`.../models/qwen4_exp/nvidia/mtp.py:199–213`, SHA-256 `c87aabf0…bb3d`). Es soporte del predictor del checkpoint, no una garantía de que seis propuestas mejoren la experiencia.

**Coste y riesgo de memoria/latencia.** Cada decode uniforme procesa `1 + num_speculative_tokens` consultas por request (`.../config/vllm.py:821–839`, SHA-256 `a7e678c5…fda2`): MTP3 = 4; MTP6 = 7. El mismo código hace que estados recurrentes del modelo se dimensionen con `num_speculative_tokens` (`.../models/qwen4_exp/nvidia/model.py:753–768, 784–799`, SHA-256 `75d071a5…b69`). Por tanto MTP6 aumenta trabajo/estado transitorio y puede agrandar capturas/gráficos y reducir margen de KV efectivo; la cantidad exacta debe medirse, no inferirse de pesos en disco.

Para QSA con `compress_ratio=4`, el código calcula `span=compress_ratio+num_speculative_tokens` y redondea un ring que divide el bloque. Con bloque 16: MTP3 requiere mínimo 8 filas; MTP6 tiene mínimo 12 pero se ensancha a 16. Es un **doble** del ring QSA por request (8→16), no una medida del KV global ni de RAM total. El código prohíbe ensanchamientos desproporcionados en vez de asignarlos silenciosamente (`05-pr54912.patch:90–136`).

**Riesgo funcional.** Una ventana de propuesta más larga solo da ganancia si se acepta suficiente prefijo. Con rechazo temprano, paga más compute/transitorios y puede empeorar la cadencia; la aceptación depende de idioma, prosa, código, herramientas y muestreo. vLLM expone `mean_acceptance_length`, tasa/histograma de aceptación, tokens propuestos y aceptados por solicitud; son las métricas necesarias para decidir, no TPS agregado.[5]

**Conclusión MTP6:** soporte de componentes: **sí, plausible** para este stack, hasta 8 en la ruta GDN y con tratamiento QSA 5–8. Soporte de rendimiento/calidad/estabilidad MTP6 para este checkpoint exacto a 4×200k: **no verificado**. No hay base para afirmar que “MTP6 es mejor” ni para cambiar producción.

## Optimizaciones plausibles para fluidez

| Palanca | Soporte en código efectivo | Qué puede mejorar | Riesgo / recomendación |
|---|---|---|---|
| MTP3 → MTP6 | Plausible; ver sección anterior | Cadencia de decode si aceptación es alta | Probar aislado; no arregla TTFT de cold prefill ni la cola de 200k. |
| `--long-prefill-token-threshold` | **Soportado**. Parser efectivo `arg_utils.py:1703–1709`; scheduler corta chunks a ese umbral `scheduler.py:583–590, 1097–1108` | Intercalar mejor un prefill frío con decodes ya en curso, reduciendo su mayor pausa visible | Aumenta número de pasos y normalmente TTFT/overhead del request frío. Es la palanca más directamente relacionada con fluidez mixta, después de demostrar el solapamiento real. |
| Mantener `--enable-chunked-prefill` y presupuesto 4096 | Ya activo | Permite mezclar prefill compute-bound y decode memory-bound, mecanismo que la guía oficial atribuye a mejor equilibrio throughput/latencia.[3] | No subir el presupuesto para “ganar TPS” si aumenta gaps de streams; medir gaps y TTFT por separado. |
| `--async-scheduling` | **No apto con MTP actual.** El código efectivo dice que async solo soporta especulación Eagle y desactiva MTP automáticamente (`config/vllm.py:1661–1716`, SHA-256 `a7e678c5…fda2`) | No proponerlo como arreglo MTP | No A/B: sería un cambio de contrato/especulación, no una optimización compatible. |
| `max_num_partial_prefills`, `max_long_partial_prefills` | **No expuestos en el paquete instalado**: búsqueda de todos los `.py` de `vllm` no encontró esos identificadores; el parser solo ofrece el threshold anterior | Ninguno en este runtime | No inventar flags de upstream/otras versiones. |
| `--num-scheduler-steps` | **No soportado**: el parser efectivo documenta que multi-step scheduling fue retirado (`arg_utils.py:1708–1709`) | Ninguno | No usar. |
| Ajuste dinámico de profundidad por tamaño de batch | Código presente para `num_speculative_tokens_per_batch_size` (`scheduler.py:315–321`) | Podría evitar propuesta profunda cuando C4 reduce aceptación | **No recomendado aún**: requiere confirmar aceptación por carga; añade otro cambio e interactúa con capturas. |
| Prefix cache | Ya activo | Reduce TTFT de continuación solo si hay prefijo idéntico reutilizable | No resuelve entrada de historia nueva/cold; verificar `cached_tokens` en pruebas calientes. |

El scheduler documenta que `max_num_batched_tokens` es el techo de tokens por iteración y que la profundidad especulativa puede requerir un límite de tokens programados menor; el código pide subir ese presupuesto o bajar profundidad si no hay espacio para la especulación (`arg_utils.py:2653–2662`). Con 4096 y cuatro secuencias, MTP6 tiene margen aritmético mínimo (4×7=28), pero eso no mide la fluidez ni la huella real de graphs/estados.

## Plan A/B mínimo posterior, si se autoriza explícitamente

No ejecutado. Mantener imagen, revisión de modelo, KV FP8, GMU 0.8, 200k total, `max-num-seqs=4`, batch 4096, cache, PLE, kernels, chat template y sampling idénticos. Un cambio por experimento:

1. **Base MTP3**: repetir la fixture mixta ya relevante: tres streams de historia caliente larga, inyectar el cuarto prompt frío largo mientras siguen generando. Guardar por request TTFT de contenido, máximo gap entre deltas no vacíos, duración cold, prompt/cached/completion tokens, finalización y recuperación de cola.
2. **MTP6**: solo cambiar `num_speculative_tokens: 3 → 6`, con tamaños de CUDA graph derivados/revisados para la nueva profundidad, no reciclados ciegamente. Comparar las mismas fixtures de español/prosa, código/herramienta y una continuación caliente larga.
3. Para ambas: guardar métricas de aceptación por solicitud (`mean_acceptance_length`, accepted/draft tokens, histograma) y lectura de capacidad/memoria/errores. La documentación oficial define esas métricas y su máximo (`k+1`).[5]
4. Decisión: retener MTP6 solo si no empeora el máximo gap ni TTFT caliente, no reduce la seguridad de C4×200k y mejora de manera repetible la tasa visible de cada stream. Un aumento de TPS agregado o un prompt corto no basta.
5. Si MTP6 no gana, conservar MTP3 y probar **por separado** un umbral de prefill (p. ej. 1024; después 512 solo si es necesario), comparando el compromiso: menos gap para los tres streams frente a TTFT mayor del cuarto. No combinar MTP6+threshold en el primer A/B.

## Recomendaciones

1. **Prioridad 1: medir y proteger la fluidez bajo solapamiento**, no el TPS headline. El síntoma de conversaciones largas se ataca por scheduling de prefill/chunks; MTP solo modifica decode.
2. **No promover MTP6 todavía.** Es un candidato técnicamente razonable, no un upgrade probado. El coste QSA y los estados recurrentes hacen especialmente importante mantener el margen de cuatro contextos.
3. **Primer experimento de scheduling, después de MTP A/B o como alternativa si el problema dominante es cold prefill:** `long-prefill-token-threshold` aislado. El default efectivo 0 no aplica cap adicional; cambiarlo es una política explícita de ceder TTFT frío por continuidad de streams.
4. **Descartar como propuestas inmediatas** `async_scheduling`, multi-step scheduling y flags de partial-prefill citados: MTP los invalida o el runtime efectivo no los expone.
5. Mantener QSA/PLE/b12x/graphs y allocator actual durante estos A/B; desactivarlos cambiaría demasiadas variables y no es una solución específica a la cadencia.

## Referencias locales verificables

- Configuración: `profiles/200k/config.json (entrada del despliegue local, no distribuida)`.
- Receta anclada: `spark-vllm-docker` @ `0bdc9c94cd89843e1c8f7d7b33df2d5bc746c03d`.
- Evidencia de soporte QSA: `docker/patches/qwen3.8/vllm/05-pr54912.patch`, SHA-256 `dc7a28c1883c3949f7ebf8fdf35465fe0484b6f96d60a6efe2ec4f9b06aaef71`.
- Evidencia de confidence fallback SM121 (no recomendada sin A/B): `04-pr60068.patch`, SHA-256 `9beda564e859406efa9c69cd98f04f777da1f4674dd626c39f60e7f66b7b0fae`, líneas 20–26: espera GPU por draft y declara SM120 no probado; por eso no forma parte del plan.
- Código efectivo en contenedor: `/usr/local/lib/python3.12/dist-packages/vllm/`, hashes y líneas citados en el texto.

## Sources

[1] https://docs.vllm.ai/en/latest/features/speculative_decoding/mtp
[2] https://docs.vllm.ai/en/latest/features/speculative_decoding
[3] https://docs.vllm.ai/en/latest/configuration/optimization
[5] https://docs.vllm.ai/en/latest/features/speculative_decoding/acceptance_metrics

## Contraste con el benchmark terminado

La prueba mixta publicada en `results-interactivity-2026-10-18.md` mantuvo tres continuaciones cercanas a 198K respondiendo mientras entraba un cuarto prompt frío de 32K. Cumplió TTFT caliente <=2s y máximo gap visible <=2s en esta fixture. No se introdujo un cuarto prompt frío de 200K ni se compararon ambos motores.

La generación repetía la palabra `pulse`: es una carga sintética predecible, no una medición de TPS de programación, herramientas o prosa natural. No comparar sus 106–111 TPS agregados con baterías anteriores de otro contenido/cache/tamaño como si fueran una mejora de configuración. Antes de promover MTP6, usar fixtures pareadas de español, código y herramientas, además de esta prueba de scheduler.

Las métricas por solicitud citadas en la documentación upstream pueden no estar expuestas por la imagen instalada. Verificar el esquema real; si solo hay contadores globales, reportar sus deltas en una ventana aislada y mantener desconocidos los campos por solicitud.

Decisión actual: mantener MTP3. MTP6 requiere un A/B autorizado, recuperación preparada y validación de capacidad/memoria. Un umbral de prefill menor también requiere experimento separado; no se justifica pagar más TTFT frío solo por cambiar una configuración que ya pasó estos umbrales sintéticos.
