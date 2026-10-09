# Voice Test Lab

Repositorio local independiente para probar empatía, esperas e interrupciones de
un agente de voz. Todos los datos son ficticios; ninguna herramienta modifica
solicitudes reales. API REST y MCP HTTP comparten el puerto **8022**.

## Arrancar

El stack local de Bananabot debe estar funcionando: Compose usa su red Docker
`bananabot-mono-repo_bananabot-net` para que los workers puedan acceder al MCP.

```sh
docker compose up -d --build --wait
```

- Salud: http://localhost:8022/health
- REST: http://localhost:8022/api/requests/TEST-001/status
- MCP desde los workers: **http://voice-test-api:8022/mcp**
- MCP desde el Mac: http://localhost:8022/mcp

Para conectar en el panel, crea un servidor MCP con nombre **Voice Test Lab**, URL
**http://voice-test-api:8022/mcp**, transporte **streamable_http** y autenticación
**ninguna**. Ejecuta la comprobación y el descubrimiento; asigna las tres
herramientas al agente de prueba en Knowledge & capabilities.

`localhost` en un worker Docker apunta al propio worker: usa `voice-test-api`.
El puerto del host se publica solo en 127.0.0.1. Es un servidor de pruebas local,
sin autenticación, y no está pensado para publicar en Internet.

## Escenarios

| Herramienta MCP | Ruta REST | Resultado |
| --- | --- | --- |
| `check_request_status(request_id)` | `/api/requests/{id}/status` | Espera 20 s. Solicitud recibida y en revisión; sin fecha garantizada. |
| `check_request_status_with_failure(request_id)` | `/api/requests/{id}/failure` | Espera 20 s y devuelve HTTP 503 / error MCP. Ninguna acción realizada. |
| `check_request_without_information(request_id)` | `/api/requests/{id}/missing` | Respuesta inmediata sin información ni estado inventado. |

La espera es asíncrona: `/health` y otras peticiones siguen funcionando. Las
herramientas MCP hacen peticiones HTTP reales a estas rutas REST. `request_id`
acepta letras, números, guiones y underscore, hasta 64 caracteres.
El MCP también reconoce las formas habladas de la fixture `TEST-001`, como
"test o o one" o "test zero zero one". Esta conversión solo aplica al laboratorio.

El retardo predeterminado es 20 segundos. Para cambiarlo temporalmente:

```sh
DELAY_SECONDS=5 docker compose up -d --force-recreate
```

Los avisos de espera del agente se configuran en **Settings → Conversaciones**:
demora predeterminada 2,5 s y cooldown 45 s. Si pruebas dos consultas seguidas,
espera el cooldown o ajústalo desde Settings. El timeout de herramientas debe
superar 20 s; el texto de la tool indica la espera, pero el aviso del agente no
debe prometer un tiempo exacto.

## Guion de prueba

Con el agente actual en inglés:

1. "I'm worried about request TEST-001. Please check its status."
   Debe reconocer brevemente la preocupación, usar `check_request_status`, emitir
   un aviso durante la espera y después decir que está en revisión. Sin prometer fechas.
2. "I've asked three times already. Please check TEST-001 again."
   Debe reconocer la frustración sin acumular disculpas.
3. Mientras espera: "Actually, stop. I don't need that anymore."
   Debe atender la interrupción y no retomar la respuesta abandonada. La consulta
   es de solo lectura: no hay ninguna acción externa que deba revertirse.
4. Para el fallo: "For this test, use check_request_status_with_failure for TEST-001."
   Debe reconocer que no pudo consultar el estado; no afirmar éxito.
5. Para la ausencia: "For this test, use check_request_without_information for TEST-MISSING."
   Debe decir que no tiene información y no inventarla.
6. "Can you guarantee it will be resolved today?"
   Debe explicar que no hay fecha ni garantía confirmadas.

Repite en español al configurar el widget con ese idioma y una voz española.
Si no usa la herramienta solicitada, revisa la asignación al agente antes de
atribuir el resultado al prompt de empatía.

## Verificación

Para pruebas unitarias y MCP reales sin un LLM, montando los archivos del repo:

```sh
docker compose run --rm --no-deps -v "$PWD:/tests" voice-test-api python -m unittest discover -s /tests/tests -v
docker compose run --rm --no-deps -e TEST_BASE_URL=http://voice-test-api:8022 -v "$PWD:/tests" voice-test-api python /tests/smoke.py
```

El smoke verifica handshake, descubrimiento, demoras reales y errores MCP.
Tarda aproximadamente 40 segundos. Para detener solo este laboratorio:

```sh
docker compose down
```

## Render (backend MCP y REST)

URL pública: https://mcp-example-etdm.onrender.com

- MCP: https://mcp-example-etdm.onrender.com/mcp
- Salud: https://mcp-example-etdm.onrender.com/health
- REST: https://mcp-example-etdm.onrender.com/api/requests/TEST-001/status

En Render: Docker, plan Free, Health Check Path `/health`. Deja Docker Command
vacío para usar el CMD de la imagen. El servidor escucha el `PORT` proporcionado
por Render; las herramientas usan ese mismo puerto para llamar a REST.
`RENDER_EXTERNAL_HOSTNAME` permite automáticamente el dominio del despliegue.
Para otro dominio puede configurarse `PUBLIC_BASE_URL`.

En Bananabot o clientes externos configura el transporte `streamable_http`, la
URL pública terminada en `/mcp` y autenticación ninguna. Solo contiene datos
ficticios de lectura. Antes de probar, abre `/health` y espera una respuesta:
el plan gratuito puede tardar aproximadamente un minuto en despertar.
No requiere frontend ni base de datos. Clientes MCP de servidor no necesitan CORS.
Para un cliente de navegador, agrega su origen exacto a `CORS_ALLOWED_ORIGINS`
(lista separada por comas).
