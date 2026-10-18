# Fase 2 — MTP3 frente a MTP6: resultado de admisión (2026-10-18)

## Resultado

**MTP6: NOTRUN.** No se cambió, inició ni promovió MTP6. El backend quedó/resta en MTP3.

No se fabricó una comparación A/B: habría sido inválida sin un candidato físicamente admisible y un restaurador independiente probado.

## Hechos comprobados antes de decidir

- El runtime instalado reconoce `--speculative-config`; su ayuda enumera métodos MTP y la configuración especulativa.
- El argv efectivo del perfil de 200k contiene duplicados históricos, pero las últimas ocurrencias seleccionan `max-num-seqs=4`, KV FP8 y `{"method":"mtp","num_speculative_tokens":3}`.
- El controlador de producción sólo acepta las claves exactas `200k` y `262k`; ambas están fijadas por manifests y hashes de autorización a MTP3. No existe una clave MTP6.
- El supervisor tiene `Restart=no`; no existe un candidato MTP6 aislado, un selector aprobado ni un guard restaurador MTP6 ya armado.
- Crear el candidato mediante `docker exec`, modificar el script dentro del contenedor o editar manifiestos/controlador habría evitado la barrera de admisión, invalidado sus hashes y violado el requisito de usar el controlador físico probado. No se hizo.

## Línea base disponible

La fase 1 publicada en el commit anterior aporta los fixtures legales, hashes privados, protocolos y métricas MTP3. No se usan los resultados sintéticos anteriores como un supuesto MTP6 ni se reclama mejora.

## Estado final verificado

El servicio de usuario y el contenedor autorizado estaban activos en `qwen-fp4-vllm-disk-mtp3-200k`, con endpoint de 200k y el template físico de 28,234 bytes cuyo SHA-256 es `e57684bae4156211a55473c5a63be976a405a37ab5be5ae0e5abf1df5349c4b2`.

Un A/B real requiere primero una extensión de controlador/perfil MTP6 que conserve el binding físico, con snapshot, watchdog independiente, barrera de admisión y restauración MTP3 verificable. Eso es una modificación de control de producción, no un benchmark inocuo, y no se sustituyó por una prueba simulada.
