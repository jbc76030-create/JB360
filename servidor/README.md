# JB360 · Servidor de administración y clientes (revisión técnica)

Este paquete ofrece **una misma dirección de acceso para varios negocios**. Cada negocio tiene una base SQLite separada, sus usuarios y su licencia semestral. El administrador general registra negocios, controla las cuentas operadoras y confirma las renovaciones. Incluye productos, inventario, ventas de bienes, servicios, pagos mixtos, reversión íntegra de tickets, otros ingresos y gastos, terceros, documentos comerciales borrador, informes y simulación fiscal condicionada de 2026.

Para probar el acceso remoto **sin dominio ni servidor propio**, usa [PILOTO_GRATUITO_PYTHONANYWHERE.md](PILOTO_GRATUITO_PYTHONANYWHERE.md). Incluye un adaptador WSGI para el servidor existente, persistencia SQLite y una URL HTTPS gratuita, con límites de espacio, capacidad y caducidad mensual. Necesita que el titular cree su cuenta de alojamiento y active su subdominio; este paquete aún no está desplegado en una URL pública. Para una instalación en servidor y dominio propios, consulta [OPERACION_EN_INTERNET.md](OPERACION_EN_INTERNET.md) y su plantilla Docker/Caddy.

## Instalación local para evaluación

Para instalar una copia por cliente y acceder desde otros dispositivos, sigue [INSTALACION_POR_CLIENTE.md](INSTALACION_POR_CLIENTE.md). Incluye lanzadores de Windows y macOS/Linux. La app funciona como servidor web local; teléfono y tableta acceden mediante navegador cuando el servidor esté disponible por una red segura. No contiene una app nativa autónoma para Android/iOS.

Requiere Python 3.11 o posterior. Desde esta carpeta:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python iniciar.py
```

En Windows abre `INSTALAR_WINDOWS.cmd` y luego `ABRIR_WINDOWS.cmd` en las siguientes sesiones. En macOS/Linux usa `sh INSTALAR_MAC_LINUX.sh` y luego `sh ABRIR_MAC_LINUX.sh`. El iniciador solicita la contraseña del administrador solo cuando la base todavía no tiene usuarios; no la escribe en un archivo. Abre `http://127.0.0.1:8000/` en el equipo servidor. **No expongas este servidor de desarrollo directamente a Internet.** Para acceso desde otros equipos se requiere red adecuada, HTTPS, protección de la base y copias de seguridad.

## Acceso de administrador y clientes

La dirección local `http://127.0.0.1:8000/` es la interfaz de todos los negocios en el equipo que ejecuta el servidor. Cada cliente introduce su **código de negocio, usuario y contraseña** en esa misma pantalla. Pueden entrar al mismo tiempo, incluso dos negocios con un usuario del mismo nombre, sin cruzar registros. El servidor asocia cada sesión al negocio de origen y usa su base separada para cada operación. El administrador general inicia con código vacío, elige un negocio y puede crear usuarios, revisar vectores, renovar o respaldar solo el negocio elegido. Para acceso remoto por **un mismo enlace público**, se debe alojar este servidor en un entorno permanente con HTTPS y dominio propio. GitHub Pages puede publicar archivos estáticos, pero no ejecuta este servidor ni comparte las bases.

## Activación de clientes

1. Entra como `admin` general con código de cliente vacío y la contraseña configurada en el servidor. En **Negocios independientes**, crea un código, un nombre, un usuario inicial y su contraseña. El negocio comienza con licencia pendiente.
2. Selecciona ese negocio en la misma pantalla. Ya puedes crear usuarios adicionales para él. Facilita a cada usuario la dirección compartida, el código de su negocio y sus credenciales propias.
3. Tras comprobar el pago por un procedimiento externo, registra la referencia y marca la confirmación en Administración del negocio seleccionado. El servidor añade exactamente seis meses desde el vencimiento vigente o desde el día de la activación si ya venció.
4. El operador puede consultar la fecha de licencia cuando venza, pero el servidor bloquea sus operaciones hasta la renovación. Solo el administrador puede renovarla; queda una bitácora de referencias y fechas. El panel general resume vencimientos y cantidad de usuarios/ventas por negocio; también permite suspender o habilitar operadores.

La app **no cobra, verifica transferencias ni emite un comprobante fiscal del pago de licencia**. La confirmación del administrador es una declaración manual. La misma referencia de cobro no activa dos veces. El código público y una instalación que el cliente controle no constituyen una protección antipiratería; para licencias exigibles, conserva el servidor y sus credenciales bajo control del administrador.

## Vector fiscal por negocio

1. El cliente u operador carga en **Tributos** el PDF, PNG o JPEG del vector fiscal aprobado, su NIT y fecha de aprobación. Tamaño máximo 5 MiB. La base guarda el original y su huella SHA-256; la descarga comprueba la integridad.
2. Si el administrador ya configuró el emisor, actor y NIT deben coincidir. El administrador coteja el documento real y registra los conceptos, la situación y fechas de vigencia. La carga nueva queda pendiente sin sustituir al último vector revisado; el cálculo anterior conserva su vigencia hasta que el administrador active la nueva revisión.
3. La simulación solo admite el actor, situación, mes completo y conceptos de la revisión vigente. El operador revisa las bases propuestas y las condiciones particulares antes de obtener importes. El archivo **no se interpreta automáticamente** y esta clasificación administrativa no es una aprobación de ONAT.

Cada negocio tiene **una base propia**, bajo el directorio de clientes situado junto a la base general (`<nombre-base>-tenants/`). Esas bases y sus respaldos requieren control de acceso y copia individual. `test_single_url_tenants.py` comprueba dos negocios simultáneos en la misma URL con usuarios del mismo nombre: licencia, sesión, vector, documento y ventas permanecen separados. `test_multiclient.py` comprueba también instalaciones separadas como alternativa para entornos anteriores.

## Plan y normatador de cuentas

La sección Administración custodia el PDF del normatador identificado por norma, tamaño máximo 5 MiB, con huella SHA-256 y descarga íntegra. Acepta además dos archivos JSON estructurados: el plan propio (`regimen`, `version`, `cuentas` con `codigo`, `nombre`, `naturaleza`, `uso`, `fuente`) y un lote normativo (`version`, `cuentas` con `codigo`, `nombre`, `naturaleza`, `uso_contenido`, `norma`, `anexo`, `pagina`, `regimen`). La API valida la estructura y deja todo **pendiente de cotejo**. El catálogo referencial TCP antiguo basado en la Resolución 346/2021 fue retirado porque esa norma quedó derogada por la 272/2024. La app no genera asientos usando transcripciones no aprobadas ni promete un nomenclador consolidado completo. El puente VERSAT permanece como precontabilización para revisión.

## Seguridad y respaldos

La API exige sesión para operaciones, limita cinco intentos fallidos de acceso por usuario e IP en quince minutos, caduca sesiones a las doce horas y registra acciones sensibles. El navegador conserva el token solo en memoria hasta salir o recargar. La pantalla carga un archivo JavaScript propio y la política de contenido bloquea scripts incrustados. Solo el administrador renueva, revisa vectores o descarga una copia de la base; para el respaldo debe repetir su contraseña. El respaldo SQLite se genera con la API transaccional de SQLite, comprueba su integridad e incluye el vector fiscal, pero elimina las sesiones activas. La descarga debe guardarse fuera del servidor en un lugar privado; para restaurarla, detenga el proceso y reemplace la base tras conservar la anterior.

El alojamiento debe terminar TLS/HTTPS, proteger los respaldos, actualizar dependencias y limitar el acceso a la base. Configure `JB360_ALLOWED_HOSTS` con el dominio real (lista separada por comas); por defecto se aceptan solo `localhost`, `127.0.0.1` y `testserver` para pruebas. No publique directamente Uvicorn ni convierta `iniciar.py` en un servidor abierto. Estas medidas reducen riesgos conocidos, pero ninguna aplicación puede prometer ausencia total de intrusiones o errores.

## Tributación y validación

Lee [NORMAS_FISCALES_2026.md](NORMAS_FISCALES_2026.md). La app propone importes operativos del mes y solo calcula conceptos acotados después de revisar las bases y el régimen. No genera una DJ oficial ni cubre excepciones individuales. No llames “aprobado” a un cálculo por haber pasado una prueba de software.

Los [modelos originales ONAT localizados](MODELOS_ONAT.md) se enlazan sin modificar; la app aún no rellena ni presenta sus declaraciones.

Pruebas de API: `python -m pytest -q`. Catorce escenarios automatizados incluyen creación inicial de la clave general, instalación y reinicio local, dos negocios simultáneos en una URL, respaldo integral de las bases, 30 ventas concurrentes, stock, reversión, servicio, pagos mixtos, terceros, roles, licencias aisladas, informes, cambio de día local de Cuba, vector y respaldo, límite de acceso, enlaces de botones, CSV de precontabilización y ejemplos fiscales. No equivalen a un ensayo de producción con equipos, impresoras, estados bancarios, vector fiscal real y contador de cada cliente.

Consulta [PRUEBAS_Y_ALCANCE.md](PRUEBAS_Y_ALCANCE.md) para ver cada ejemplo, su resultado y los puntos aún sin comprobar.

## Alcance que aún impide explotación pública como sistema completo

No hay alojamiento productivo ni dominio/HTTPS asignado; tampoco hay pago bancario confirmado automáticamente, devolución parcial de tickets en este servidor, nómina/retenciones completas, declaraciones ONAT ni certificación de software contable. El puente VERSAT es una exportación genérica para revisión, sin formato oficial de importación comprobado. Antes de trabajar con datos reales hace falta validar restauración de respaldo, seguridad y dispositivos en el entorno de destino. La pantalla se comprobó por contrato de botones e IDs y la API por ejemplos; no se han pulsado físicamente todos los botones en todos los navegadores.

La página pública de GitHub Pages `Web/jb360/` es una aplicación local de navegador distinta: sus datos no se sincronizan con este servidor y su licencia no está controlada por él. GitHub Pages no permite usar su hospedaje gratuito para software comercial como servicio; no lo utilices como alojamiento de venta de licencias.
