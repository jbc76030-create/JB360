"""Cálculos acotados de 2026. No es una declaración jurada ni valida el vector fiscal."""
import datetime
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from fastapi import Header, HTTPException
from pydantic import BaseModel, Field

from server import app, conn
from extension import licensed


FUENTES = {
    'presupuesto': {
        'norma': 'Ley 181/2025, Presupuesto del Estado 2026, artículos 53, 58 a 61',
        'url': 'https://www.gacetaoficial.gob.cu/sites/default/files/goc-2025-o99_1.pdf',
    },
    'tcp': {
        'norma': 'Resolución MFP 271/2024, artículos 19 y 20',
        'url': 'https://www.gacetaoficial.gob.cu/sites/default/files/goc-2024-o78_0.pdf',
    },
    'mipyme': {
        'norma': 'Resolución MFP 306/2023, apartado Segundo, incisos a) a e)',
        'url': 'https://www.gacetaoficial.gob.cu/sites/default/files/goc-2024-o5-_0.pdf',
    },
    'pdl': {
        'norma': 'Resolución MFP 202/2026, artículos 6, 7 y 13',
        'url': 'https://www.gacetaoficial.gob.cu/sites/default/files/goc-2026-o87_0.pdf',
    },
}


def amount(value, name, optional=False):
    if value is None and optional:
        return None
    try:
        d = Decimal(str(value))
        if not d.is_finite() or d < 0 or d != d.quantize(Decimal('0.01')):
            raise ValueError()
        return int(d * 100)
    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(422, f'{name}: importe no negativo con dos decimales como máximo')


def round_tax(base_cents, numerator, denominator=100):
    return int((Decimal(base_cents) * numerator / denominator).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


class Simulation(BaseModel):
    actor: str
    month: str = Field(pattern=r'^2026-(0[1-9]|1[0-2])$')
    goods_base: str = '0'
    services_base: str = '0'
    taxable_profit: str | None = None
    payroll_base: str | None = None
    personal_income_base: str | None = None
    total_activity_income_base: str | None = None
    situation: str = 'standard'
    exceptions_reviewed: bool = False
    bases_reviewed: bool = False


def simulate(x: Simulation):
    if x.actor not in ('tcp', 'mipyme', 'cna', 'pdl', 'estatal'):
        raise HTTPException(422, 'Actor sin regla general verificada; confirme su inscripción y vector fiscal')
    if x.actor == 'pdl' and x.month < '2026-11':
        raise HTTPException(422, 'La Resolución 202/2026 se publicó el 21 de octubre: meses anteriores y el mes de transición requieren revisar las normas y bases por fecha')
    if not x.exceptions_reviewed or not x.bases_reviewed:
        raise HTTPException(422, 'Revise actividad, exenciones, régimen y bases antes de calcular')
    if x.situation not in ('standard', 'pdl_minindustry_food', 'state_retail_to_population'):
        raise HTTPException(422, 'Situación no reconocida')
    if x.situation == 'pdl_minindustry_food' and x.actor != 'pdl':
        raise HTTPException(422, 'El 5 % de minindustrias solo corresponde al caso de PDL previsto en la norma')
    if x.situation == 'state_retail_to_population' and x.actor != 'estatal':
        raise HTTPException(422, 'Esta situación solo corresponde a personas jurídicas estatales')
    if x.actor == 'estatal' and x.situation != 'state_retail_to_population':
        raise HTTPException(422, 'Para estatal se requiere confirmar venta minorista o servicio a la población')
    goods = amount(x.goods_base, 'Ventas gravadas')
    services = amount(x.services_base, 'Servicios gravados')
    profit = amount(x.taxable_profit, 'Utilidad imponible anual', optional=True)
    payroll = amount(x.payroll_base, 'Remuneraciones', optional=True)
    personal = amount(x.personal_income_base, 'Ingresos personales mensuales', optional=True)
    activity_income = amount(x.total_activity_income_base, 'Ingresos totales de la actividad', optional=True)
    if personal is not None and x.actor != 'tcp':
        raise HTTPException(422, 'El anticipo personal implementado corresponde solo a TCP')
    lines = []

    def add(label, base, rate, source, frequency='mensual', fraction=None):
        tax = round_tax(base, *(fraction or (int(rate), 100)))
        lines.append({'concepto': label, 'periodicidad_base': frequency, 'base_cents': base,
                      'tipo': rate, 'estimado_cents': tax, 'fuente': FUENTES[source]})

    if x.actor == 'pdl' and x.situation == 'pdl_minindustry_food':
        add('Ventas minoristas de alimentos de minindustria PDL', goods, '5 %', 'pdl', fraction=(5, 100))
        add('Otros servicios gravados PDL', services, '10 %', 'pdl', fraction=(10, 100))
    else:
        source = 'tcp' if x.actor == 'tcp' else 'pdl' if x.actor == 'pdl' else 'mipyme' if x.actor == 'mipyme' else 'presupuesto'
        add('Ventas y servicios gravados', goods + services, '10 %', source, fraction=(10, 100))

    if x.actor == 'tcp' and personal is not None:
        excess = max(0, personal - 326000)
        add('Anticipo de ingresos personales TCP sobre exceso de 3 260 CUP', excess, '5 %', 'tcp', fraction=(5, 100))
    if x.actor in ('mipyme', 'cna', 'pdl', 'estatal') and profit is not None:
        source = 'mipyme' if x.actor == 'mipyme' else 'pdl' if x.actor == 'pdl' else 'presupuesto'
        add('Impuesto sobre utilidades (base imponible revisada)', profit, '35 %', source, 'anual', (35, 100))
    if x.actor == 'mipyme' and activity_income is not None:
        add('Contribución territorial MIPYME', activity_income, '1 %', 'mipyme', fraction=(1, 100))
    if x.actor in ('mipyme', 'pdl') and payroll is not None:
        source = x.actor
        add('Impuesto por utilización de fuerza de trabajo', payroll, '5 %', source, fraction=(5, 100))
        add('Contribución a seguridad social: 12,5 % al fisco y 1,5 % provisionado', payroll, '14 %', source, fraction=(14, 100))
    return {
        'actor': x.actor, 'mes': x.month, 'situacion': x.situation, 'lineas': lines,
        'advertencia': 'Simulación condicionada a bases y régimen revisados. No incluye todos los tributos, créditos, exenciones, retenciones, cuotas ni la declaración oficial de ONAT. La utilidad comercial no equivale por sí sola a base imponible.',
    }


@app.post('/api/fiscal/simulate')
def fiscal_simulate(x: Simulation, authorization: str | None = Header(None)):
    licensed(authorization)
    return simulate(x)


@app.get('/api/fiscal/proposed')
def fiscal_proposed(month: str, authorization: str | None = Header(None)):
    licensed(authorization)
    if not re.fullmatch(r'2026-(0[1-9]|1[0-2])', month):
        raise HTTPException(422, 'El módulo de propuesta solo admite meses de 2026')
    goods = services = 0
    tz = ZoneInfo('America/Havana')
    with conn() as c:
        for row in c.execute('SELECT kind,subtotal_cents,created_at,reversed_at FROM tickets'):
            sale_date = datetime.datetime.fromisoformat(row['created_at']).astimezone(tz).strftime('%Y-%m')
            if sale_date == month:
                if row['kind'] == 'goods': goods += row['subtotal_cents']
                else: services += row['subtotal_cents']
            if row['reversed_at'] and datetime.datetime.fromisoformat(row['reversed_at']).astimezone(tz).strftime('%Y-%m') == month:
                if row['kind'] == 'goods': goods -= row['subtotal_cents']
                else: services -= row['subtotal_cents']
    return {'mes': month, 'ventas_bienes_cents': goods, 'servicios_cents': services,
            'advertencia': 'Importes operativos para cotejar. Compruebe reembolsos, ingresos no registrados, exenciones, actividad y documentos antes de usarlos como base fiscal. Las bases negativas requieren revisión manual.'}
