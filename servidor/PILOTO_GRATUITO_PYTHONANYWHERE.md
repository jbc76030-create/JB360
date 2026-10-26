# JB360 en Internet sin dominio ni servidor propio: piloto

## Qué se obtiene y cuál es el límite

PythonAnywhere ofrece a una cuenta gratuita una dirección como
`https://TUUSUARIO.pythonanywhere.com/`, certificado HTTPS para ese subdominio,
un proceso web y espacio persistente donde guardar las bases SQLite. En una
cuenta europea la dirección puede ser `https://TUUSUARIO.eu.pythonanywhere.com/`.
**El enlace real nace al registrar TU cuenta; no está creado en este paquete.**

La cuenta gratuita actual tiene **512 MiB de disco**, **un proceso web** y
caducidad de la web gratuita tras **un mes** si no se renueva en el panel. Las
peticiones de varios usuarios entran en una cola y pueden volverse lentas. Es
una forma de probar JB360 contigo y con tus usuarios; no hay garantía de
capacidad o continuidad para vender licencias semestrales a muchos negocios.
Comprueba personalmente que el alta del servicio y su acceso funcionen desde
Cuba antes de cargar información real.

Fuentes del proveedor (consultadas el 26 de octubre de 2026):

- https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- https://help.pythonanywhere.com/pages/HowManyHitsCanMySiteHandle/
- https://help.pythonanywhere.com/pages/HTTPSSetup
- https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- https://blog.pythonanywhere.com/129/
- https://help.pythonanywhere.com/pages/ExternalVCS/

## Preparación en la cuenta gratuita

1. Registra una cuenta en `https://www.pythonanywhere.com/` y elige un nombre
   de usuario que quieras conservar en la dirección. La verificación de correo
   y cualquier validación de la cuenta la hace el titular. No compartas la
   contraseña de PythonAnywhere con los clientes.
2. En **Consoles → Bash** ejecuta, reemplazando `TUUSUARIO` por tu usuario real:

   ```bash
   git clone --branch servidor-2026-en-revision --single-branch https://github.com/jbc76030-create/JB360.git ~/JB360
   python3.11 -m venv ~/jb360_venv
   ~/jb360_venv/bin/python -m pip install --no-cache-dir -r ~/JB360/servidor/requirements-pythonanywhere.txt
   mkdir -m 700 -p ~/jb360_private
   ```

   Si `python3.11` no existe en esa cuenta, usa una versión disponible de
   Python 3.11 o posterior y selecciona **la misma versión** en la web.
3. Crea el administrador general **una vez** en la consola. El siguiente
   comando pide dos veces una clave de al menos 14 caracteres; no la pongas
   en GitHub, en la configuración WSGI ni en el historial de la consola:

   ```bash
   cd ~/JB360/servidor
   export JB360_DB="$HOME/jb360_private/jb360.sqlite3"
   ~/jb360_venv/bin/python bootstrap.py
   ```

4. En **Web → Add a new web app**, selecciona el subdominio gratuito, la
   configuración **Manual** y el Python que usaste en el entorno virtual.
   En **Virtualenv**, indica `/home/TUUSUARIO/jb360_venv`. Edita el archivo
   WSGI que ofrece la página **Web**. Sustituye su contenido por esto, con
   TUUSUARIO y el host real de tu cuenta (incluye `.eu` si corresponde):

   ```python
   import os
   import sys

   sys.path.insert(0, '/home/TUUSUARIO/JB360/servidor')
   os.environ['JB360_DB'] = '/home/TUUSUARIO/jb360_private/jb360.sqlite3'
   os.environ['JB360_ALLOWED_HOSTS'] = 'TUUSUARIO.pythonanywhere.com'
   from pythonanywhere_wsgi import application
   ```

   La base y documentos quedan bajo `jb360_private`, fuera del repositorio.
   Si hay un error, consulta el **error log** de la web. En **Web → Security**,
   activa **Force HTTPS** y pulsa **Reload**. No escribas el nombre de ejemplo
   `TUUSUARIO` literalmente.
5. Abre `https://TUUSUARIO.pythonanywhere.com/` en un navegador. Entra como
   `admin`, deja vacío **código de negocio**, y usa la clave del paso 3.
   El panel general permite crear tu propio negocio como primer cliente.
   Después selecciona ese negocio y confirma manualmente su licencia tras
   registrar el pago o, para tu prueba, su referencia interna.
6. Crea operadores adicionales dentro del negocio. Cada uno usa **la misma
   dirección HTTPS**, el **código del negocio** y sus credenciales personales
   desde Android, Windows o tableta. Prueba desde dos dispositivos la creación
   y lectura de una venta; comprueba inventario, informe y respaldo.

### Datos, copias y administración

Tu negocio es un cliente más. El administrador general conserva el acceso con
código vacío; puede dar de alta otros negocios, revisar su información y
renovar su licencia individual exactamente seis meses después de confirmar
manualmente el pago. El sistema no recibe ni verifica pagos automáticamente.
No entregues la clave general ni el acceso a la cuenta de alojamiento.

Cada día que trabajes con datos reales, descarga una copia integral en un
almacenamiento privado, **fuera del alojamiento**. En la consola:

```bash
cd ~/JB360/servidor
export JB360_DB="$HOME/jb360_private/jb360.sqlite3"
~/jb360_venv/bin/python backup_all.py > ~/jb360_private/respaldo-jb360.zip
```

Descarga el ZIP desde **Files** y luego borra esa copia temporal del servidor
para no agotar el espacio. El ZIP contiene el directorio de todos los clientes
y hashes para comprobar integridad; guárdalo cifrado y prueba su restauración
antes de depender de él. La cuenta gratuita nueva no incluye una tarea diaria
automática, por lo que este respaldo es manual. Nunca subas la base, el vector
fiscal ni los respaldos al repositorio público de GitHub.

Vigila el espacio usado en el panel. La base general, las bases de cada
cliente, los PDF que se guardan dentro de ellas, el entorno virtual y sus
archivos temporales comparten la cuota. El panel puede requerir que renueves
mensualmente la web gratuita; si se suspende por caducidad, los usuarios no
podrán entrar hasta reactivarla.

### Antes de comercializar

Esta ruta sirve para una prueba real de bajo volumen. El proveedor informa
que su plan de pago comienza en **10 USD/mes**; cuando puedas sostener el
costo con ingresos, aumenta trabajadores y disco en esa misma plataforma y
mantén la dirección del subdominio, sujeto al plan y disponibilidad. Si no
puedes asumir ese importe, ofrece solo pilotos cuya posible interrupción y
volumen estén claros para el cliente. Evita prometer seis meses ininterrumpidos
si dependes de renovar una web gratis cada mes.

GitHub almacena el **código**, no el servidor ni los datos de los usuarios.
Sus condiciones de Pages excluyen la comercialización de software SaaS en ese
alojamiento gratuito: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
La app visible en GitHub Pages guarda los datos en cada navegador y no es la
versión para licencias de varios clientes.

Los cálculos fiscales de JB360 son ejemplos condicionados a la revisión del
vector real de cada actor, sin declaraciones ONAT oficiales ni certificación.
Consulta `README.md`, `NORMAS_FISCALES_2026.md` y `PRUEBAS_Y_ALCANCE.md`.

### Actualizar el código sin perder datos

Desde la consola, con las bases fuera del repositorio:

```bash
cd ~/JB360
git pull --ff-only
```

Luego pulsa **Reload** en **Web**. Descarga una copia antes de cada actualización.
Si la rama de revisión cambia, prueba las migraciones y restauración de la
copia antes de llevarla a usuarios de pago.
