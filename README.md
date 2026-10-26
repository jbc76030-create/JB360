# JB Gestión Empresarial 360 · Comercial

Aplicación de gestión comercial para registrar productos, servicios, ventas, devoluciones, existencias, caja, cobros electrónicos, gastos, reservas e informes. Incluye un perfil para distintos actores económicos cubanos y libros auxiliares de ingresos y gastos exportables a CSV.

## Empezar

Abre `index.html` en un navegador moderno. Para usarlo desde GitHub Pages, activa **Settings → Pages → Build and deployment → GitHub Actions** en este repositorio. La publicación existente en `.github/workflows/pages.yml` se ejecuta al actualizar `main`. También puedes descargar `index.html` y abrirlo localmente sin conexión.

1. En **Perfil económico**, selecciona el actor y guarda los datos del negocio.
2. En **Productos** y **Servicios**, crea el catálogo. La instalación nueva empieza vacía.
3. En **Ventas**, añade artículos al comprobante y registra el cobro en efectivo, transferencia, tarjeta o una combinación. Las devoluciones parciales reponen existencias y distribuyen el reembolso entre los medios originales.
4. Consulta **Caja y Banco**, **Informes** y el libro auxiliar **Tributos**.
5. En **Respaldo**, descarga periódicamente el JSON. Contiene los datos comerciales y el perfil económico. Para cambiar de equipo, importa ese archivo en el otro navegador; la importación reemplaza sus datos comerciales.

Los datos se almacenan **solo en el navegador y origen desde el que se usa la aplicación**. La dirección de GitHub Pages, un archivo abierto desde el disco y otra dirección de alojamiento mantienen almacenes distintos. No hay sincronización, cuentas de usuario ni permisos entre empleados. Si se borra el almacenamiento del navegador, se pierden los cambios posteriores al último respaldo. Guarda los JSON con cuidado porque contienen información del negocio.

Los cobros por transferencia o tarjeta son importes declarados en las ventas; no confirman abonos bancarios. Los informes y libros son auxiliares comerciales. La aplicación no calcula impuestos según un vector fiscal verificado, no genera modelos ONAT ni presenta declaraciones oficiales. Los comprobantes impresos no son facturas fiscales.

## Verificación técnica

El archivo es autónomo, sin librerías remotas. El motor se comprobó con una secuencia de producto + servicio, pago mixto, devolución parcial, ajuste de existencias, caja, cobros electrónicos, gastos, informes y respaldo. Ejecuta `node tests/smoke.cjs` en una copia de este repositorio para repetir la comprobación.
