"""Encabezado con el que la API marcaba las respuestas fijas.

Ya no queda ningún endpoint con respuesta fija, pero CORS sigue exponiendo el encabezado y
la prueba de humo lo sigue leyendo, por si un endpoint nuevo vuelve a necesitarlo.
"""

MOCK_HEADER = "X-Fieldshift-Mock"
