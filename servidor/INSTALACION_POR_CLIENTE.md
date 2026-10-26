# JB360 · Instalación local para cada cliente

## Qué se entrega

Este paquete contiene el servidor y la pantalla web, los lanzadores de ordenador, las reglas operativas y las pruebas. No contiene clientes, vectores fiscales, claves ni bases de datos. Descomprímelo **una vez por negocio** en el equipo que quedará encendido cuando sus usuarios trabajen. Una instalación comienza con la licencia pendiente.

| Equipo | Uso comprobable con este paquete |
|---|---|
| Windows con Python 3.11 o posterior | Ejecuta el servidor local mediante `INSTALAR_WINDOWS.cmd`; después `ABRIR_WINDOWS.cmd`. Los scripts no se probaron físicamente en Windows. |
| macOS o Linux con Python 3.11 o posterior | Ejecuta `sh INSTALAR_MAC_LINUX.sh`; después `sh ABRIR_MAC_LINUX.sh`. La prueba HTTP de arranque y reinicio se hizo en Linux. |
| Teléfono o tableta Android, iPad/iPhone | Entra desde el navegador a un servidor JB360 accesible por HTTPS. No se entrega una aplicación nativa ni un servidor autónomo probado para esos dispositivos. |

La instalación inicial de dependencias requiere conexión para `pip`, a menos que la máquina ya tenga un repositorio de paquetes compatible. No copies una base SQLite en uso entre dispositivos: cada copia pasaría a ser un negocio **sin sincronización**. Para varios usuarios del mismo negocio se comparte la **dirección del mismo servidor**.

## Primer inicio en un ordenador

1. Extrae el ZIP y conserva la carpeta `servidor` en una ubicación privada y estable. No instales encima de una carpeta con datos de otro cliente.
2. En Windows abre `INSTALAR_WINDOWS.cmd`. En macOS/Linux ejecuta `sh INSTALAR_MAC_LINUX.sh` desde la carpeta. Se crea `.venv` y se instalan las dependencias. Si Python no está instalado, instálalo antes de ejecutar el lanzador.
3. Crea una clave administrativa de **14 caracteres o más** cuando la consola la solicite. Consérvala tú. No se escribe en un archivo de configuración. Deja la consola abierta mientras se usa la aplicación.
4. Abre `http://127.0.0.1:8000/` **en ese mismo ordenador**. Entra con código de cliente vacío, usuario `admin` y tu clave.
5. Si esta instalación corresponde a un solo negocio, crea su usuario operador en **Administración**. Si alojas varios negocios en el mismo servidor, créalos en **Negocios independientes** con códigos distintos y selecciona cada uno antes de administrar sus usuarios y licencias.
6. Verifica el pago por tu procedimiento habitual, indica su referencia, marca la casilla de verificación y activa **seis meses**. El operador ve su licencia, pero no puede renovarla. Una segunda renovación añade otros seis meses desde el vencimiento aún vigente, o desde la fecha de renovación cuando ya venció.

Para reiniciar, usa `ABRIR_WINDOWS.cmd` o `sh ABRIR_MAC_LINUX.sh`. La clave administrativa no vuelve a pedirse en la consola cuando la base ya existe; se usa en la pantalla de entrada. Cada operador puede cambiar su clave. El administrador puede listar operadores y restablecerles la clave previa confirmación de la suya; se cierran sus sesiones anteriores.

## Mismo negocio en varios dispositivos

El ordenador que ejecuta JB360 debe permanecer encendido. Para que otros ordenadores, teléfonos o tabletas entren, el servidor debe estar disponible en la red con una dirección alcanzable. Por defecto solo escucha `127.0.0.1`, por lo que **no** se abre por sí solo a otros dispositivos.

La opción avanzada de red utiliza `JB360_BIND=0.0.0.0`, `JB360_ALLOW_LAN=1` y `JB360_ALLOWED_HOSTS` con la IP o dominio que usarán los clientes. Para claves y documentos reales, configura además HTTPS mediante un certificado confiable, con `JB360_TLS_CERT` y `JB360_TLS_KEY`, o un proxy inverso HTTPS administrado. Ajusta el cortafuegos para admitir solo la red deseada. El acceso sin TLS por una red privada solo sirve para demostración con datos de prueba. No expongas Uvicorn directamente a Internet.

Ejemplo de variables para un servidor Linux con certificado que incluya `192.168.1.20`:

```sh
export JB360_BIND=0.0.0.0
export JB360_ALLOW_LAN=1
export JB360_ALLOWED_HOSTS=192.168.1.20,localhost,127.0.0.1
export JB360_TLS_CERT=/ruta/segura/cert.pem
export JB360_TLS_KEY=/ruta/segura/key.pem
sh ABRIR_MAC_LINUX.sh
```

En el teléfono o la tableta se abriría `https://192.168.1.20:8000/` si la red, el cortafuegos y el certificado confiable están configurados. La URL no funciona fuera de esa red salvo que se prepare un alojamiento o acceso seguro. El certificado y su clave privada no vienen en el ZIP.

## Licencias y control del administrador

Cada base tiene su propia fecha de vencimiento y registro de renovaciones. El operador vencido conserva acceso a consultar el estado de la licencia, pero no puede registrar ventas, productos ni vectores hasta que el administrador confirme el pago y la renovación. Se rechaza reutilizar una referencia de pago **en el mismo negocio**. El software no procesa cobros, no comprueba abonos bancarios ni factura por sí mismo el servicio de licencia. Si deseas cobrar una anualidad, administra dos períodos consecutivos de seis meses y sus referencias según el acuerdo comercial.

Cuando el cliente controla físicamente el ordenador y recibe el código fuente, puede modificar el programa, la base o reinstalarlo. **La clave administrativa protege las funciones de la aplicación, pero no garantiza el cobro de una licencia contra alteraciones del propietario del equipo.** Para control comercial exigible conserva el servidor y sus copias bajo tu administración. Aun instalado en el equipo de un cliente, no le entregues la clave de `admin`.

## Datos y respaldos

En una instalación de un negocio, la base se crea en `servidor/datos/jb360.sqlite3`. La descarga desde **Administración → Copia de seguridad** requiere repetir tu clave y excluye los tokens de sesión. Guárdala fuera de ese ordenador. Si usas el modo multiempresa, la base general guarda el directorio de negocios y cada negocio tiene otra base en `datos/jb360-tenants/`; respalda **todas** ellas. Cierra el servidor antes de copiar o restaurar manualmente bases. Protege también los PDF de vectores y normas, pues se guardan dentro de la base de cada negocio.

## Alcance funcional

Ventas de bienes y servicios, inventario, pagos, reversión íntegra, informes, terceros, auxiliares fiscales y documentos de soporte son funciones operativas en revisión. El vector fiscal se sube y se revisa manualmente; la simulación tributaria es acotada. Los planes de cuentas cargados quedan pendientes de cotejo. El paquete **no genera ni presenta las declaraciones juradas originales de ONAT** ni certifica comprobantes contables oficiales. Ver `PRUEBAS_Y_ALCANCE.md` para ejemplos y límites.
