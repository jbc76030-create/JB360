# JB360 · Servidor de administración y clientes (revisión técnica)

Este paquete aloja una **instalación por negocio/cliente** con base SQLite independiente. El administrador controla el acceso de operadores y la licencia semestral desde el servidor. Incluye productos, inventario, ventas de bienes, servicios, pagos mixtos, reversión íntegra de tickets, otros ingresos y gastos, terceros, documentos comerciales borrador, informes y simulación fiscal condicionada de 2026.

## Instalación local para evaluación

Requiere Python 3.11 o posterior. Desde esta carpeta:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
export JB360_ADMIN_PASSWORD='una-clave-propia-larga-de-al-menos-14-caracteres'
export JB360_DB="$PWD/datos/jb360.sqlite3"
mkdir -p datos
.venv/bin/python iniciar.py
```

En Windows PowerShell, desde esta carpeta: `py -m venv .venv`, luego `./.venv/Scripts/python.exe -m pip install -r requirements.txt` y `./.venv/Scripts/python.exe iniciar.py`. El iniciador solicita la contraseña del administrador sin mostrarla y crea `datos/jb360.sqlite3`. Si configura las variables de entorno antes, las respeta. Abre `http://127.0.0.1:8000/` en el equipo servidor. La app cliente utiliza la misma dirección con su usuario operador; la sección Administración solo aparece al administrador. **No expongas este servidor de desarrollo directamente a Internet.** Para acceso desde otros equipos se requiere alojamiento permanente, HTTPS, protección de la base y copias de seguridad.

## Acceso de administrador y clientes

La dirección local `http://127.0.0.1:8000/` es la interfaz de ambos roles en el equipo que ejecuta el servidor. Para que personas en otros equipos entren simultáneamente por **un mismo enlace público**, el administrador debe alojar esta instancia en un servidor permanente, con HTTPS y un dominio propio. El iniciador local escucha solo en `127.0.0.1` deliberadamente. GitHub Pages puede publicar los archivos estáticos, pero no ejecuta este servidor ni comparte la base SQLite.

## Activación de clientes

1. La base nueva empieza con licencia pendiente. Entra como `admin` con la contraseña configurada en el servidor.
2. Crea un usuario operador para el cliente. Cada negocio debe tener una base/instancia separada; no compartas una base entre empresas independientes.
3. Tras comprobar el pago por un procedimiento externo, registra la referencia y marca la confirmación en Administración. El servidor añade exactamente seis meses desde el vencimiento vigente o desde el día de la activación si ya venció.
4. El operador puede consultar la fecha de licencia cuando venza, pero el servidor bloquea sus operaciones hasta la renovación. Solo el administrador puede renovarla; queda una bitácora de referencias y fechas.

La app **no cobra, verifica transferencias ni emite un comprobante fiscal del pago de licencia**. La confirmación del administrador es una declaración manual. La misma referencia de cobro no activa dos veces. El código público y una instalación que el cliente controle no constituyen una protección antipiratería; para licencias exigibles, conserva el servidor y sus credenciales bajo control del administrador.

## Vector fiscal por negocio

1. El cliente u operador carga en **Tributos** el PDF, PNG o JPEG del vector fiscal aprobado, su NIT y fecha de aprobación. Tamaño máximo 5 MiB. La base guarda el original y su huella SHA-256; la descarga comprueba la integridad.
2. Si el administrador ya configuró el emisor, actor y NIT deben coincidir. El administrador coteja el documento real y registra los conceptos, la situación y fechas de vigencia. La carga nueva queda pendiente sin sustituir al último vector revisado; el cálculo anterior conserva su vigencia hasta que el administrador active la nueva revisión.
3. La simulación solo admite el actor, situación, mes completo y conceptos de la revisión vigente. El operador revisa las bases propuestas y las condiciones particulares antes de obtener importes. El archivo **no se interpreta automáticamente** y esta clasificación administrativa no es una aprobación de ONAT.

Cada instalación tiene una base para **un negocio/contribuyente**. Si el administrador atiende varios actores económicos independientes, debe desplegar una instancia separada por cada uno, con su vector y sus usuarios. Puede usar `JB360_PORT` y `JB360_DB` distintos para iniciar dos instalaciones en un equipo; el acceso público requiere rutas o subdominios HTTPS separados. No mezcle empresas distintas en la misma base. `test_multiclient.py` comprueba con dos procesos que licencia, sesión, vector y ventas no se comparten.

## Plan y normatador de cuentas

La sección Administración custodia el PDF del normatador identificado por norma, tamaño máximo 5 MiB, con huella SHA-256 y descarga íntegra. Acepta además dos archivos JSON estructurados: el plan propio (`regimen`, `version`, `cuentas` con `codigo`, `nombre`, `naturaleza`, `uso`, `fuente`) y un lote normativo (`version`, `cuentas` con `codigo`, `nombre`, `naturaleza`, `uso_contenido`, `norma`, `anexo`, `pagina`, `regimen`). La API valida la estructura y deja todo **pendiente de cotejo**. El catálogo referencial TCP antiguo basado en la Resolución 346/2021 fue retirado porque esa norma quedó derogada por la 272/2024. La app no genera asientos usando transcripciones no aprobadas ni promete un nomenclador consolidado completo. El puente VERSAT permanece como precontabilización para revisión.

## Seguridad y respaldos

La API exige sesión para operaciones, limita cinco intentos fallidos de acceso por usuario e IP en quince minutos, caduca sesiones a las doce horas y registra acciones sensibles. El navegador conserva el token solo en memoria hasta salir o recargar. La pantalla carga un archivo JavaScript propio y la política de contenido bloquea scripts incrustados. Solo el administrador renueva, revisa vectores o descarga una copia de la base; para el respaldo debe repetir su contraseña. El respaldo SQLite se genera con la API transaccional de SQLite, comprueba su integridad e incluye el vector fiscal, pero elimina las sesiones activas. La descarga debe guardarse fuera del servidor en un lugar privado; para restaurarla, detenga el proceso y reemplace la base tras conservar la anterior.

El alojamiento debe terminar TLS/HTTPS, proteger los respaldos, actualizar dependencias y limitar el acceso a la base. Configure `JB360_ALLOWED_HOSTS` con el dominio real (lista separada por comas); por defecto se aceptan solo `localhost`, `127.0.0.1` y `testserver` para pruebas. No publique directamente Uvicorn ni convierta `iniciar.py` en un servidor abierto. Estas medidas reducen riesgos conocidos, pero ninguna aplicación puede prometer ausencia total de intrusiones o errores.

## Tributación y validación

Lee [NORMAS_FISCALES_2026.md](NORMAS_FISCALES_2026.md). La app propone importes operativos del mes y solo calcula conceptos acotados después de revisar las bases y el régimen. No genera una DJ oficial ni cubre excepciones individuales. No llames “aprobado” a un cálculo por haber pasado una prueba de software.

Los [modelos originales ONAT localizados](MODELOS_ONAT.md) se enlazan sin modificar; la app aún no rellena ni presenta sus declaraciones.

Pruebas de API: `python -m pytest -q`. Diez escenarios automatizados incluyen 30 ventas concurrentes, stock, reversión, servicio, pagos mixtos, terceros, roles, licencias de dos negocios aislados, informes con separación de bienes y servicios, cambio de día local de Cuba, vector y respaldo, límite de acceso, enlaces de botones, CSV de precontabilización y ejemplos fiscales. No equivalen a un ensayo de producción con equipos, impresoras, estados bancarios, vector fiscal real y contador de cada cliente.

## Alcance que aún impide explotación pública como sistema completo

No hay alojamiento productivo ni dominio/HTTPS asignado; tampoco hay aislamiento multiempresa dentro de una sola instancia, pago bancario confirmado automáticamente, devolución parcial de tickets en este servidor, nómina/retenciones completas, declaraciones ONAT ni certificación de software contable. El puente VERSAT es una exportación genérica para revisión, sin formato oficial de importación comprobado. Antes de trabajar con datos reales hace falta validar restauración de respaldo, seguridad y dispositivos en el entorno de destino.

La página pública de GitHub Pages `Web/jb360/` es una aplicación local de navegador distinta: sus datos no se sincronizan con este servidor y su licencia no está controlada por él.
