# JB Gestión Empresarial 360 · Comercial

Aplicación de gestión comercial para registrar productos, servicios, ventas, devoluciones, existencias, caja, cobros electrónicos, gastos, reservas e informes. Incluye un perfil para distintos actores económicos cubanos y libros auxiliares de ingresos y gastos exportables a CSV.

## Abrir la app

Abre **[JB360 en el navegador](https://jbc76030-create.github.io/Web/jb360/)**. El código principal está en este repositorio y la copia publicada está en la carpeta `jb360/` del repositorio `Web`, que ya tiene GitHub Pages habilitado. La página `Web/oficina/` es un proyecto independiente. Al cambiar el código, hay que actualizar `index.html` en ambos repositorios; las modificaciones en uno no se copian al otro automáticamente.

También puedes descargar `index.html` y abrirlo localmente sin conexión; algunos navegadores limitan el almacenamiento de archivos `file://`, así que comprueba que tus registros sigan allí después de cerrar y volver a abrir, y conserva un respaldo JSON.

### Administración, usuarios y vectores fiscales

La [versión de servidor en revisión](https://github.com/jbc76030-create/JB360/tree/servidor-2026-en-revision/servidor) ofrece cuentas de administrador y operador, licencia semestral controlada en el servidor, carga del vector fiscal aprobado por contribuyente, revisión administrativa de sus conceptos y simulación tributaria condicionada. [Descargar esa rama](https://github.com/jbc76030-create/JB360/archive/refs/heads/servidor-2026-en-revision.zip). La rama en revisión admite varios negocios con la misma dirección del servidor, cada uno con código, usuario, contraseña, base y licencia independientes; aún no está alojada en una dirección pública con HTTPS. El enlace de GitHub Pages de arriba es la versión comercial local del navegador, sin esas cuentas compartidas ni el archivo del vector.

1. En **Perfil económico**, selecciona el actor y guarda los datos del negocio.
2. En **Productos** y **Servicios**, crea y actualiza el catálogo. La instalación nueva empieza vacía. Las existencias se cambian con movimientos de inventario y las ventas anteriores conservan sus importes originales.
3. En **Ventas**, añade artículos al comprobante y registra el cobro en efectivo, transferencia, tarjeta o una combinación. Las devoluciones parciales reponen existencias y distribuyen el reembolso entre los medios originales.
4. Consulta **Caja y Banco**, **Informes** y el libro auxiliar **Tributos**. El informe general de ventas y el de costos identifican cada línea como producto o servicio; **Ventas y rentabilidad de servicios** resume las unidades, ingresos, costos directos y margen. El CSV auxiliar de ingresos también incluye el tipo y distingue las devoluciones.
5. En **Respaldo**, descarga periódicamente el JSON. Contiene los datos comerciales y el perfil económico. Para cambiar de equipo, importa ese archivo en el otro navegador; la importación reemplaza sus datos comerciales.

Los datos se almacenan **solo en el navegador y origen desde el que se usa la aplicación**. La dirección de GitHub Pages, un archivo abierto desde el disco y otra dirección de alojamiento mantienen almacenes distintos. No hay sincronización, cuentas de usuario ni permisos entre empleados. Si se borra el almacenamiento del navegador, se pierden los cambios posteriores al último respaldo. Guarda los JSON con cuidado porque contienen información del negocio.

Los cobros por transferencia o tarjeta son importes declarados en las ventas; no confirman abonos bancarios. Los informes y libros son auxiliares comerciales. La aplicación no calcula impuestos según un vector fiscal verificado, no genera modelos ONAT ni presenta declaraciones oficiales. Los comprobantes impresos no son facturas fiscales.

## Verificación técnica

El archivo es autónomo, sin librerías remotas. El motor se comprobó en Node con un DOM simulado, mediante una secuencia de producto + servicio, pago mixto, devolución parcial, ajuste de existencias, caja, cobros electrónicos, edición de catálogo, gastos, informes y respaldo. También se probó una venta solo de servicios con devolución y códigos iguales en ambos catálogos, verificando informes y CSV. En la página publicada se repitió la venta con devolución, se comprobó la persistencia al recargar y se descargó y restauró un respaldo JSON en Chrome de escritorio. Ejecuta `node tests/smoke.cjs` en una copia de este repositorio para repetir la prueba del motor. Quedan pendientes pruebas físicas en Android y tabletas y pruebas de impresión en esos equipos.
