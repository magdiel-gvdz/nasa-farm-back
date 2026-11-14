# Prueba del ciclo de vida de previews

Para comprobar el flujo completo, abrir un PR con un cambio pequeño y verificar:

1. Los checks y el despliegue de `pr-N` terminan correctamente.
2. `/health` responde con `environment` igual a `pr-N`.
3. Después del merge, el job `destroy-preview` termina correctamente.
4. La Lambda, la API y el bucket de `pr-N` desaparecen, y `dev` permanece disponible.

Conservar los enlaces de las ejecuciones como evidencia de la prueba.
