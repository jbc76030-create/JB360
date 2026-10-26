# JB360 · Pruebas reproducibles y límites (26/10/2026)

Comando: `python -m pytest -q` desde `servidor/`, tras instalar `requirements.txt`. Resultado local de esta versión: **12 pruebas correctas**. `node --check panel.js` pasó. Las pruebas usan bases SQLite temporales; no incluyen información de clientes reales.

| Proceso | Ejemplo comprobado | Resultado |
|---|---|---|
| Inicio y permisos | Administrador crea operador; operador no crea administradores ni renueva licencias | Rechazos 403/422; acceso con sesión |
| Licencia semestral | Pago confirmado con referencia; repetición de la referencia y renovación de 12 meses | Seis meses; referencia repetida 409; 12 meses 422; operador vencido 402 |
| Dos clientes independientes | Dos procesos y bases A/B: se activa A, se carga su vector y vende 100 CUP; B queda vencido y sin esos datos | Licencias, sesiones, vectores y ventas separados |
| Dos negocios en una URL | Ambos entran como `vendedor` con código y clave distintos; el administrador activa uno y el otro queda vencido; venden simultáneamente servicios de 100 y 250 CUP | Sesiones, licencias, informes, vector y PDF normativo aislados. Acceso cruzado 403; operador no renueva 403; respaldo del negocio exige clave general |
| Instalación local y restauración | Arranca con clave inicial, crea operador, activa seis meses, descarga respaldo; reinicia desde la copia sin repetir la variable de la clave | Conserva administrador, operador y licencia activa después de restaurar |
| Claves por negocio | Administrador restablece la del operador de un negocio tras verificar su clave; otro operador intenta y se rechaza | La sesión anterior queda revocada; nueva clave entra y datos del negocio persisten |
| Productos e inventario | 30 ventas simultáneas de un bien con stock 100; devolución de una | Stock 70 y luego 71; no doble devolución |
| Servicio y pagos | Servicio de 150 CUP, costo 30; venta con efectivo/transferencia; reversión de servicio | Informe desglosa servicio; margen 120 antes de reversión; devolución no altera inventario |
| Fecha de Cuba | Servicio vendido a las 01:00 UTC del 1/10 y anulado a las 05:00 UTC | Venta corresponde al 30/9 local y devolución al 1/10 |
| Vector fiscal | Subida PDF con SHA-256, actor y NIT; revisión administrativa; nuevo PDF pendiente | Cálculo solo con vector revisado; documento alterado 409; el pendiente no sustituye el activo |
| Tributación condicionada | MIPYME: bases 1 000 bienes + 500 servicios, 200 utilidad, 100 nómina, 1 500 territorial; TCP: 5 000 ingresos; PDL minindustria noviembre | Conceptos incluidos: 150 ventas, 70 utilidades, 15 territorial, 5 fuerza de trabajo y 14 seguridad social CUP para MIPYME; 500 y 87 CUP para TCP; 50 y 50 CUP en ventas/servicios PDL. No son liquidaciones totales. |
| Normatador | PDF de una norma registrada; lote JSON con uso/contenido, anexo y página; plan propio | Archivo y SHA recuperables; cuentas pendientes de cotejo; rechaza referencia 346/2021 derogada |
| Respaldos y acceso | Cinco claves erróneas, sexta tentativa; respaldo con contraseña administrativa; extracción de SQLite | 429 por intentos; respaldo íntegro con vectores y cero tokens activos |
| Interfaz | Todos los botones `data-action` tienen función registrada y todos los IDs utilizados existen; JS sintácticamente válido | Contrato de pantalla correcto; servidor entrega HTML y JS externo bajo CSP |

También se ejecutó una prueba HTTP real: arranque, entrada de administrador, activación, cuenta cliente, carga/revisión de vector, venta de servicio de 120 CUP y cálculo condicionado de 12 CUP sobre ese ingreso, con el archivo JavaScript servido por el servidor. La prueba verifica las operaciones desde HTTP; **no sustituye pulsar cada botón en todos los navegadores y dispositivos**.

## Sin validación de producción

- El enlace GitHub Pages es comercial y local por navegador. El servidor con roles y vectores necesita alojamiento HTTPS para un enlace común a clientes remotos.
- Se requieren certificado confiable, red o dominio, servidor, copias externas, prueba de restauración y revisión de seguridad en el alojamiento real. Los lanzadores Windows y los navegadores móviles no se ensayaron físicamente.
- El simulador no rellena modelos ONAT. DJ-01 e instructivo se descargan de la ONAT sin modificación; otros modelos y todas las casillas/fórmulas siguen sin cotejo integral.
- El plan y normatador subidos permanecen pendientes; no habilitan comprobantes contables automáticos. El CSV VERSAT es precontabilización revisable, sin importación oficial demostrada.
- No hay pruebas de impresora, teléfono Android, conciliación bancaria real, nómina completa ni autorización de obligaciones fiscales de clientes específicos.
