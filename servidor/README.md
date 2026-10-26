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

## Activación de clientes

1. La base nueva empieza con licencia pendiente. Entra como `admin` con la contraseña configurada en el servidor.
2. Crea un usuario operador para el cliente. Cada negocio debe tener una base/instancia separada; no compartas una base entre empresas independientes.
3. Tras comprobar el pago por un procedimiento externo, registra la referencia y marca la confirmación en Administración. El servidor añade exactamente seis meses desde el vencimiento vigente o desde el día de la activación si ya venció.
4. El operador puede consultar la fecha de licencia cuando venza, pero el servidor bloquea sus operaciones hasta la renovación. Solo el administrador puede renovarla; queda una bitácora de referencias y fechas.

La app **no cobra, verifica transferencias ni emite un comprobante fiscal del pago de licencia**. La confirmación del administrador es una declaración manual. El código público y una instalación que el cliente controle no constituyen una protección antipiratería; para licencias exigibles, conserva el servidor y sus credenciales bajo control del administrador.

## Tributación y validación

Lee [NORMAS_FISCALES_2026.md](NORMAS_FISCALES_2026.md). La app propone importes operativos del mes y solo calcula conceptos acotados después de revisar las bases y el régimen. No genera una DJ oficial ni cubre excepciones individuales. No llames “aprobado” a un cálculo por haber pasado una prueba de software.

Pruebas de API: `python -m pytest -q`. Siete escenarios automatizados incluyen 30 ventas concurrentes, stock, reversión, servicio, pagos mixtos, terceros, roles, vencimiento/renovación, informes con separación de bienes y servicios, cambio de día local de Cuba, CSV de precontabilización y ejemplos fiscales. No equivalen a un ensayo de producción con equipos, impresoras, estados bancarios, vector fiscal y contador de cada cliente.

## Alcance que aún impide explotación pública como sistema completo

No hay alojamiento productivo ni dominio/HTTPS asignado; tampoco hay aislamiento multiempresa dentro de una sola instancia, pago bancario confirmado automáticamente, devolución parcial de tickets en este servidor, nómina/retenciones completas, declaraciones ONAT ni certificación de software contable. El puente VERSAT es una exportación genérica para revisión, sin formato oficial de importación comprobado. Antes de trabajar con datos reales hace falta validar restauración de respaldo, seguridad y dispositivos en el entorno de destino.

La página pública de GitHub Pages `Web/jb360/` es una aplicación local de navegador distinta: sus datos no se sincronizan con este servidor y su licencia no está controlada por él.
