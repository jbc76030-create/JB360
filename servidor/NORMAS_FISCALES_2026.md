# JB360 · Reglas fiscales incorporadas para revisión (2026)

Fecha de cotejo: 26 de octubre de 2026. Fuentes: textos PDF publicados por la Gaceta Oficial. El resultado de la app es una **simulación condicionada**, no una declaración jurada, dictamen, aprobación de la ONAT ni homologación contable.

| Actor / situación | Cálculo incorporado | Soporte oficial | Condición de uso |
|---|---|---|---|
| TCP general | 10 % sobre ventas y servicios gravados del mes; anticipo personal del 5 % sobre el exceso de 3 260 CUP de ingresos mensuales | [MFP 271/2024, arts. 19 y 20](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2024-o78_0.pdf); [Ley 181/2025, art. 61](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2025-o99_1.pdf) | Excluye supuestos expresos de comisiones de telecomunicaciones y seguros y regímenes específicos de pesca comercial y sector artístico. No liquida el impuesto personal anual. |
| MIPYME ordinaria | 10 % sobre ventas y servicios gravados; 35 % de utilidad imponible anual; 1 % territorial sobre ingresos totales de actividad; 5 % por fuerza de trabajo y 14 % de seguridad social sobre remuneraciones (12,5 % se aporta al Presupuesto y 1,5 % se provisiona) | [MFP 306/2023, Segundo a)–e)](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2024-o5-_0.pdf); [Ley 181/2025, arts. 19, 53 y 60](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2025-o99_1.pdf) | Utilidad imponible, ingresos totales y remuneraciones se introducen por separado tras revisión contable. No presupone que el margen comercial sea utilidad fiscal. |
| CNA ordinaria | 10 % sobre ventas y servicios gravados; 35 % general sobre utilidad imponible anual | [Ley 181/2025, arts. 53 y 60](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2025-o99_1.pdf); [Gaceta 5/2024, regulación CNA](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2024-o5-_0.pdf) | Las deducciones, el régimen especial de socios y la nómina no quedan automatizados. |
| PDL ordinario, meses completos desde noviembre de 2026 | 10 % sobre ventas y servicios; 35 % de utilidad imponible; 5 % fuerza de trabajo y 14 % de seguridad social (12,5 % se aporta al Presupuesto y 1,5 % se provisiona) | [MFP 202/2026, arts. 6, 7 y 13](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2026-o87_0.pdf); [Ley 181/2025, arts. 19, 53 y 60](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2025-o99_1.pdf) | La nueva resolución se publicó el 21 de octubre; el simulador bloquea enero a octubre, pues octubre es un mes de transición y requiere conciliar por fecha las normas previas. Puede existir exoneración o bonificación del MFP. |
| PDL: alimentos de minindustria, desde noviembre de 2026 en este simulador | 5 % para venta minorista de esas producciones; otros servicios gravados al 10 % | [MFP 202/2026, art. 6](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2026-o87_0.pdf) | La base del 5 % debe contener solo la venta minorista de productos de la minindustria que califiquen. |
| Entidad estatal: venta minorista o servicio a población | 10 % sobre esos bienes y servicios gravados; 35 % general sobre utilidad imponible | [Ley 181/2025, arts. 53 y 58](https://www.gacetaoficial.gob.cu/sites/default/files/goc-2025-o99_1.pdf) | El cálculo no se habilita para otras ventas estatales; revisar excepciones sectoriales. |
| Trabajador autónomo u otro | Sin cálculo automático | No existe en la información disponible un régimen único que pueda inferirse solo de esa denominación | Se necesita la inscripción y el vector fiscal concreto antes de asignar un régimen. |

## Qué hace la app

- Separa bienes y servicios, propone sus importes desde los tickets y reversiones por mes local de Cuba y deja al responsable revisar la base gravada.
- Aplica aritmética exacta en centavos a los conceptos de la tabla, registra el nombre y enlace de la fuente en cada línea y rechaza actores, períodos o combinaciones no admitidos.
- Requiere dos confirmaciones de revisión de bases y de régimen/excepciones. **Estas marcas no son aprobación jurídica ni sustituyen la revisión documental.**

## Qué falta para una liquidación oficial por contribuyente

Vector fiscal y actividades autorizadas, exenciones y bonificaciones individuales/municipales, tratamiento de devoluciones y documentos justificativos, deducibilidad, ingresos adicionales, nóminas y retenciones de cada trabajador/socio, aportes especiales, cuotas y pagos previos, monedas/tipos de cambio, modelos e instructivos ONAT y reglas sectoriales. Los cálculos no deben trasladarse a una DJ sin contrastar esos datos y la normativa aplicable al ejercicio.

## Ejemplos reproducibles

| Supuesto ilustrativo con bases ya revisadas | Resultado aritmético de conceptos incluidos |
|---|---|
| MIPYME: bienes 1 000, servicios 500, utilidad imponible 200, nómina 100 e ingresos de actividad 1 500 CUP | Ventas/servicios 150; utilidades 70; territorial 15; fuerza de trabajo 5; seguridad social patronal 14 CUP |
| TCP: ingresos y ventas/servicios 5 000 CUP | Ventas/servicios 500 y anticipo personal 87 CUP |
| PDL de minindustria en noviembre de 2026: venta minorista elegible 1 000 y otros servicios 500 CUP | 50 y 50 CUP, respectivamente |

Los ejemplos se verifican en `test_fiscal2026.py` contra el API. No representan pagos totales exigibles ni casos con beneficios fiscales.
