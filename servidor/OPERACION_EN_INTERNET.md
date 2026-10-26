# JB360 · Guía del administrador para varios clientes por Internet

## Modelo de uso

Se instala **una sola copia del servidor** en un equipo permanente bajo tu control. Todos abren la misma dirección HTTPS desde Android, ordenador, laptop o tableta. Cada negocio introduce su **código de cliente** y cada trabajador sus **credenciales personales**. Los usuarios de un negocio comparten sus datos; otro negocio tiene otra base, licencia, vector fiscal y usuarios. El ordenador o teléfono del cliente actúa como navegador, por lo que no recibe la base de datos ni la clave general.

| Persona | Acceso | Lo que puede hacer |
|---|---|---|
| Administrador general (tú) | Usuario `admin`, código vacío | Crear negocios y usuarios, ver el estado de licencias, seleccionar un negocio, confirmar renovaciones, revisar vectores, restablecer o suspender operadores y descargar respaldos. |
| Operador de un negocio | Código del negocio + usuario y clave propios | Trabajar en ese negocio mientras la licencia esté vigente; cambiar su propia contraseña. No puede activar licencias ni entrar a otro negocio. |

Por ahora **no existe un rol de administrador delegado para cada cliente**. Tú creas, suspendes y restableces los usuarios de todos los negocios. El panel general muestra por negocio el vencimiento, la cantidad de operadores y el número de tickets.

## Lo necesario para una dirección pública

1. Un servidor o VPS encendido continuamente que controles, con Docker Engine y Docker Compose disponibles.
2. Un dominio o subdominio tuyo (ejemplo: `app.tudominio.cu`) cuyo DNS señale a la IP pública del servidor.
3. Puertos 80 y 443 accesibles para que Caddy obtenga y renueve el certificado HTTPS; el servicio Python queda solo en la red interna de Docker.
4. Almacenamiento persistente, acceso administrativo al servidor y un destino **externo y privado** para las copias de seguridad.

GitHub Pages publica la versión estática anterior, pero no ejecuta el servidor multiusuario. Este paquete prepara el despliegue; **no contiene ni puede inventar un servidor, dominio o dirección pública ya activados**. Caddy obtiene HTTPS automáticamente cuando el dominio y la conectividad están configurados. [Documentación oficial de Caddy](https://caddyserver.com/docs/automatic-https). Docker Compose conserva la base en un volumen, separado de los contenedores. [Documentación oficial de Docker](https://docs.docker.com/reference/compose-file/volumes/).

## Despliegue inicial en el servidor

Desde la carpeta `servidor` descargada:

```sh
cp .env.example .env
```

Edita `.env` y cambia `JB360_DOMAIN=app.ejemplo.com` por **tu dominio real**, sin `https://` ni ruta. No incluyas contraseñas en ese archivo. Configura el DNS, comprueba que apunta al servidor y que los puertos 80/443 llegan a él. Después:

```sh
docker compose build app
docker compose run --rm -it app python bootstrap.py
docker compose up -d
docker compose ps
```

`bootstrap.py` solicita y confirma tu clave general de al menos 14 caracteres sin guardarla en Compose. Hazlo una vez, antes de levantar el servicio. Entra en `https://TU_DOMINIO/` con usuario `admin`, código vacío y la clave que creaste. Comprueba desde un teléfono por datos móviles y desde un ordenador que la página abre mediante HTTPS. No uses el enlace público para datos reales hasta confirmar DNS, certificado, copias, permisos y funcionamiento en esos dispositivos. Los contenedores de esta plantilla **no se pudieron ejecutar en el entorno de elaboración** porque Docker no estaba instalado allí; valida el despliegue en tu servidor.

## Alta de un cliente y sus trabajadores

1. Entra como administrador general. En **Negocios independientes**, escribe un código único en minúsculas sin espacios (por ejemplo `tienda-rosa`), nombre comercial, un usuario inicial y una contraseña temporal larga. Pulsa **Crear negocio y usuario**.
2. Elige ese negocio en el selector y pulsa **Entrar al negocio seleccionado**. Verifica que aparece su licencia pendiente. En **Administración**, crea un usuario distinto para cada trabajador. Entrega a cada cual solamente la dirección HTTPS, el código del negocio, su usuario y su clave. Que cambie su clave al primer acceso.
3. Coteja el pago por un medio externo. En ese negocio registra una referencia única, marca **Confirmo que verifiqué el pago** y pulsa **Activar / renovar seis meses**. Comprueba la nueva fecha en el panel. Un operador vencido puede ver su estado, pero no registrar operaciones.
4. Repite estos pasos para otros clientes. Pueden conectarse simultáneamente a la **misma URL**; su código y sesión deciden a qué base entran. Si un cliente tiene cinco empleados, crea cinco operadores dentro de ese negocio.

Ejemplo: `tienda-rosa` con `ana` y `carlos` comparte sus ventas e inventario entre ambos. `taller-azul` con otro usuario `ana` conserva sus propios datos y licencia. Incluso si se repite el nombre de usuario, la clave y el código de negocio determinan la cuenta correcta.

## Renovaciones y usuarios

El período fijo es de **seis meses calendario**. Se añade a la fecha de vencimiento vigente, o a la fecha actual si ya venció. Para un año se requieren dos períodos semestrales. La misma referencia no puede activar dos veces el **mismo negocio**. El sistema no cobra, no verifica el banco ni emite factura por la licencia; tú confirmas cada pago y conservas el soporte comercial externo.

Para controlar la cartera, entra como `admin` y pulsa **Actualizar lista** en **Negocios independientes**. Allí verás licencias activas, pendientes o vencidas. Selecciona un negocio para abrir **Historial de renovaciones**, **Listar usuarios del negocio**, **Restablecer clave** o **Habilitar o suspender operador**. La suspensión cierra las sesiones de ese operador. Cada usuario puede cambiar su propia contraseña; al hacerlo también se cierran sus sesiones anteriores.

## Acceso desde Android, laptop y tableta

Abre `https://TU_DOMINIO/` en el navegador actualizado del dispositivo; inicia sesión con el código del negocio, usuario y contraseña. El mismo negocio puede tener varios dispositivos y trabajadores conectados al mismo tiempo. Los cambios se guardan en el servidor central y se ven al consultar o actualizar las pantallas. No depende de una copia local distinta por teléfono. Se requiere conectividad con el servidor; este paquete no ofrece operación fuera de línea ni una aplicación nativa Android/iOS.

La cuenta general también entra por HTTPS desde donde tengas conectividad. Conserva su contraseña solo tú y no la compartas con trabajadores. Esta versión aún no tiene autenticación multifactor; usa una clave larga y única, actualiza servidor y dependencias y revisa el acceso antes de poner datos reales en producción.

## Copias, recuperación y actualizaciones

Además de la descarga de respaldo por negocio desde la pantalla, el servidor incluye una copia transaccional de **la base general y todas las bases cliente**. En una terminal segura del servidor:

```sh
mkdir -p respaldos
docker compose exec -T app python backup_all.py > respaldos/JB360-copia.zip
unzip -t respaldos/JB360-copia.zip
```

El ZIP contiene `manifest.json` con el hash SHA-256 de cada base; omite las sesiones y fallos de acceso. **Contiene datos y documentos fiscales sensibles:** tras comprobarlo, muévelo a un almacenamiento privado externo y cifrado. Haz copias periódicas según tu operación; prueba una restauración en un servidor de ensayo. Para restaurar en producción, detén el servicio, conserva los archivos existentes, verifica el manifiesto y coloca la base general y cada base cliente en sus rutas correspondientes antes de reabrir el acceso. Nunca sustituyas una SQLite mientras la app la está usando.

Antes de actualizar el código, crea una copia y pruébala. Luego actualiza el paquete y ejecuta `docker compose up -d --build`; conserva los volúmenes `jb360_data`, `caddy_data` y `caddy_config`. No uses `docker compose down -v`, que elimina los volúmenes. Si una base falta o se altera, el panel marcará el negocio como no disponible; restaura su respaldo después de investigar la causa.

## Alcance que debe explicarse al cliente

La aplicación registra operaciones e informes operativos. El vector fiscal necesita revisión administrativa; el simulador tributario cubre solo reglas acotadas. Las declaraciones juradas originales de ONAT y los comprobantes contables certificados **no están generados automáticamente**. Consulta `PRUEBAS_Y_ALCANCE.md` y las normas enlazadas antes de vender esas funciones como terminadas. Las pruebas automatizadas no sustituyen un ensayo de producción en el servidor y dispositivos reales.
