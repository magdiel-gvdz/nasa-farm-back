# Ciclo de vida de previews

Abrir los PR como borrador mientras se trabaja. Los borradores y forks ejecutan
checks sin publicar imágenes ni crear recursos. Al pasar un PR interno a listo
para revisión, el pipeline publica en ECR su SHA, aplica `pr-N` y consulta
`/health`. Un mismo SHA reutiliza la imagen ya publicada.

Antes del primer preview de esta migración hay que aplicar bootstrap y registrar
`ECR_REPOSITORY_URL`. ECS Express Mode usa el clúster y la VPC por defecto.
Cada entorno mantiene al menos una tarea encendida; no escala a cero. La regla
de expiración del bucket no elimina el servicio ni su coste.

## Evidencia requerida

1. Registrar el enlace del workflow, SHA, tiempo real de creación y `api_url`.
   La salida selecciona `ingress_paths` con `access_type == "PUBLIC"` y toma
   su atributo `endpoint`, añadiendo HTTPS cuando hace falta.
2. Consultar `curl <api_url>/health` y verificar el entorno `pr-N`.
3. Cerrar el PR y comprobar que termina `destroy-preview`.
4. Comprobar que ya no aparecen servicio ECS, tabla DynamoDB, bucket, roles ni
   logs de ese preview, y que `dev` sigue disponible.

Observado en `pr-7` el 14 de noviembre de 2026: el primer despliegue ECS
inició a las 20:05:18 y terminó a las 20:10:22 (America/Mexico_City),
5 min 4 s. Una actualización posterior tardó 8 min 26 s. El primer job
falló al seguir el despliegue por permisos de IAM; la tarea sí quedó sana.
La recuperación conserva el servicio y reconcilia su estado antes de reintentar CI.
La imagen ECR compartida se conserva y su ciclo de vida retiene 30 imágenes.

## Recuperación y transición

**Cleanup preview** recibe el número de un PR cerrado, valida que pertenece al
repositorio y ejecuta `terraform plan -destroy` y `terraform apply` desde `main`.
Usa valores válidos de relleno para la etiqueta y no necesita reconstruir imagen.
Los workflows serializan applies y limpieza; nunca se cancela un apply en curso.

La limpieza de un PR sin fusionar utiliza el código de su base. Durante el primer
PR que introduce ECS, esa base todavía contiene el stack anterior: antes de
cerrarlo sin fusionar, destruir el preview con el stack nuevo y credenciales de
preview, o recuperarlo desde `main` una vez integrada la migración. No dar por
verificada la limpieza hasta completar la comprobación real. Los permisos
heredados se mantienen hasta que no queden entornos con la plataforma anterior.

No borrar estados manualmente. Ante un bloqueo, confirmar que no hay ejecución
activa y liberar solo ese bloqueo con `terraform force-unlock` y el backend del
preview correcto.
