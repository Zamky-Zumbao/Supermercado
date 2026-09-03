import os
import tempfile
import json
import os
import pandas as pd
from datetime import datetime
import webbrowser
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# === PALETA DE MARCA (compartida entre HTML y PDF) ===
INK = colors.HexColor('#17241D')       # texto principal, casi negro-verde
GREEN = colors.HexColor('#2E6B4F')     # verde mercado (marca)
GREEN_DARK = colors.HexColor('#1F4A37')
MUSTARD = colors.HexColor('#E2A73B')   # acento cálido (precios, total)
CLAY = colors.HexColor('#C24C3A')      # alertas / eliminar
PAPER = colors.HexColor('#F3F5EE')     # fondo pergamino pálido
PAPER_ALT = colors.HexColor('#E9ECDF')
LINE = colors.HexColor('#D9DCCB')

# === REGISTRAR FUENTE (si existe una TTF personalizada, si no cae a Helvetica) ===
FUENTE_REGULAR = 'Helvetica'
FUENTE_BOLD = 'Helvetica-Bold'
try:
    pdfmetrics.registerFont(TTFont('CenturyGothic', 'CenturyGothic.ttf'))
    pdfmetrics.registerFont(TTFont('CenturyGothic-Bold', 'CenturyGothicBold.ttf'))
    FUENTE_REGULAR = 'CenturyGothic'
    FUENTE_BOLD = 'CenturyGothic-Bold'
except Exception:
    pass


# === 1. NORMALIZAR NOMBRES ===
def normalizar_nombre(nombre):
    """Convierte a mayúscula solo la primera letra, el resto minúscula.
    Respeta marcas conocidas como Nescafé, Hellmann's, etc."""

    marcas_respetar = [
        'Nescafé', 'Nescafe', 'Hellmann', "Hellmann's", 'Kellogg', "Kellogg's",
        'Miraflores', 'Bonanza', 'Banquete', 'Coliseo', 'Kardamili',
        'Belmont', 'Natura', 'Merkat', 'Lucchetti', 'Carozzi',
        'Iansa', 'Traverso', 'Tucapel', 'Milo', 'Chocapic', 'Trix',
        'Zucaritas', 'Froot Loops', 'Mono', 'Costa', 'Vivo', 'Check',
        'Nuestra Cocina', 'Dos Caballos', 'Robinson Crusoe', 'San José',
        'Pancho Villa', 'Gourmet', 'Maggi', 'Heinz', 'JB', 'Pomarola',
        'Tento', 'Wasil', 'Esmeralda', 'Aconcagua', 'Uniao', 'Mayaguez'
    ]

    palabras = nombre.split()
    palabras_normalizadas = []

    for palabra in palabras:
        palabra_normalizada = palabra
        for marca in marcas_respetar:
            if palabra.lower() == marca.lower():
                palabra_normalizada = marca
                break
        else:
            if len(palabra) > 1:
                palabra_normalizada = palabra[0].upper() + palabra[1:].lower()
            else:
                palabra_normalizada = palabra.upper()
        palabras_normalizadas.append(palabra_normalizada)

    return ' '.join(palabras_normalizadas)


# === 2. UNIFICAR TODOS LOS ARCHIVOS JSON ===
def unificar_archivos(carpeta='.'):
    """Lee todos los archivos pag*.json y los unifica en una sola lista"""
    todos_los_productos = []
    archivos = sorted([f for f in os.listdir(carpeta) if f.startswith('pag') and f.endswith('.json')])

    print(f"📂 Encontrados {len(archivos)} archivos JSON")

    for archivo in archivos:
        try:
            with open(os.path.join(carpeta, archivo), 'r', encoding='utf-8') as f:
                datos = json.load(f)
                if isinstance(datos, list) and datos:
                    for item in datos:
                        if 'nombre' in item:
                            item['nombre'] = normalizar_nombre(item['nombre'])
                    todos_los_productos.extend(datos)
                    print(f"   ✅ {archivo}: {len(datos)} productos")
                else:
                    print(f"   ⚠️ {archivo}: Vacío o formato no válido")
        except Exception as e:
            print(f"   ❌ Error con {archivo}: {e}")

    return todos_los_productos


# === 3. ELIMINAR DUPLICADOS ===
def eliminar_duplicados(productos):
    """Elimina productos duplicados por nombre, conservando el precio más bajo"""
    unicos = {}
    for p in productos:
        nombre = p.get('nombre', '').strip()
        precio = p.get('precio', 0)
        imagen = p.get('imagen', '')

        if not nombre or precio == 0:
            continue

        if nombre not in unicos or precio < unicos[nombre]['precio']:
            unicos[nombre] = {'nombre': nombre, 'precio': precio, 'imagen': imagen}

    return list(unicos.values())


# === 4. GENERAR PDF ===
def generar_pdf(productos, nombre_archivo):
    """Genera un PDF con la lista de compras, con la identidad visual del cuadro de compras."""

    doc = SimpleDocTemplate(
        nombre_archivo, pagesize=letter,
        rightMargin=42, leftMargin=42,
        topMargin=42, bottomMargin=42
    )

    styles = getSampleStyleSheet()

    estilo_marca = ParagraphStyle(
        'Marca', parent=styles['Normal'],
        fontSize=10, textColor=colors.white,
        fontName=FUENTE_BOLD, alignment=TA_LEFT,
        leading=12,
    )
    estilo_titulo = ParagraphStyle(
        'Titulo', parent=styles['Normal'],
        fontSize=20, textColor=colors.white,
        fontName=FUENTE_BOLD, alignment=TA_LEFT,
        leading=24, spaceBefore=2,
    )
    estilo_meta = ParagraphStyle(
        'Meta', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#CFE0D6'),
        fontName=FUENTE_REGULAR, alignment=TA_RIGHT,
        leading=12,
    )
    estilo_encabezado = ParagraphStyle(
        'Encabezado', parent=styles['Normal'],
        fontSize=9, alignment=TA_LEFT,
        fontName=FUENTE_BOLD, textColor=colors.white,
    )
    estilo_encabezado_centro = ParagraphStyle(
        'EncabezadoCentro', parent=estilo_encabezado, alignment=TA_CENTER,
    )
    estilo_encabezado_der = ParagraphStyle(
        'EncabezadoDer', parent=estilo_encabezado, alignment=TA_RIGHT,
    )
    estilo_celda = ParagraphStyle(
        'Celda', parent=styles['Normal'],
        fontSize=9.5, alignment=TA_LEFT,
        fontName=FUENTE_REGULAR, textColor=INK,
        leading=12,
    )
    estilo_num = ParagraphStyle(
        'Numero', parent=estilo_celda, alignment=TA_CENTER, textColor=colors.HexColor('#8A9186'),
    )
    estilo_precio = ParagraphStyle(
        'Precio', parent=estilo_celda, alignment=TA_RIGHT, fontName=FUENTE_BOLD,
    )
    estilo_total_label = ParagraphStyle(
        'TotalLabel', parent=styles['Normal'],
        fontSize=11, alignment=TA_RIGHT, fontName=FUENTE_BOLD, textColor=INK,
    )
    estilo_total_valor = ParagraphStyle(
        'TotalValor', parent=styles['Normal'],
        fontSize=13, alignment=TA_RIGHT, fontName=FUENTE_BOLD, textColor=GREEN_DARK,
    )
    estilo_footer = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=7.5, alignment=TA_CENTER, textColor=colors.HexColor('#8A9186'),
        fontName=FUENTE_REGULAR,
    )

    elementos = []

    # --- Banner de marca (verde, con acento mostaza) ---
    fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')
    banner_data = [[
        Paragraph('Cuadro de compras', estilo_marca),
        Paragraph(f'{fecha_actual}', estilo_meta),
    ], [
        Paragraph('Alvi', estilo_titulo),
        Paragraph(f'{len(productos)} producto(s)', estilo_meta),
    ]]
    banner = Table(banner_data, colWidths=[3.9 * inch, 2.6 * inch])
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), GREEN_DARK),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 14),
        ('TOPPADDING', (0, 1), (-1, 1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elementos.append(banner)

    # acento mostaza, delgada barra bajo el banner
    acento = Table([['']], colWidths=[6.5 * inch], rowHeights=[4])
    acento.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), MUSTARD)]))
    elementos.append(acento)
    elementos.append(Spacer(1, 16))

    # --- Tabla de productos ---
    data = [[
        Paragraph('N°', estilo_encabezado_centro),
        Paragraph('Producto', estilo_encabezado),
        Paragraph('Cant.', estilo_encabezado_centro),
        Paragraph('Precio unit.', estilo_encabezado_der),
        Paragraph('Subtotal', estilo_encabezado_der),
    ]]

    total_general = 0
    for idx, p in enumerate(productos, 1):
        nombre = p['nombre']
        precio = p['precio']
        cantidad = p.get('cantidad', 1)
        subtotal = precio * cantidad
        total_general += subtotal

        data.append([
            Paragraph(str(idx), estilo_num),
            Paragraph(nombre, estilo_celda),
            Paragraph(str(cantidad), estilo_num),
            Paragraph(f'${precio:,.0f}', estilo_celda),
            Paragraph(f'${subtotal:,.0f}', estilo_precio),
        ])

    fila_total_idx = len(data)
    data.append([
        '', '', '',
        Paragraph('TOTAL', estilo_total_label),
        Paragraph(f'${total_general:,.0f}', estilo_total_valor),
    ])

    tabla = Table(data, colWidths=[0.4 * inch, 3.35 * inch, 0.55 * inch, 1.1 * inch, 1.1 * inch], repeatRows=1)

    estilos_tabla = [
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), GREEN),
        ('TOPPADDING', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 9),
        # Cuerpo
        ('LINEBELOW', (0, 1), (-1, -2), 0.5, LINE),
        ('TOPPADDING', (0, 1), (-1, -2), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -2), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Total
        ('LINEABOVE', (3, fila_total_idx), (-1, fila_total_idx), 1.2, GREEN_DARK),
        ('TOPPADDING', (0, fila_total_idx), (-1, fila_total_idx), 12),
        ('BACKGROUND', (3, fila_total_idx), (-1, fila_total_idx), colors.HexColor('#FBF3E3')),
    ]
    # Franjas alternadas para filas de producto
    for i in range(1, len(data) - 1):
        if i % 2 == 0:
            estilos_tabla.append(('BACKGROUND', (0, i), (-1, i), PAPER))

    tabla.setStyle(TableStyle(estilos_tabla))
    elementos.append(tabla)
    elementos.append(Spacer(1, 22))
    elementos.append(Paragraph(
        'Generado automáticamente por Cuadro de Compras · Alvi', estilo_footer
    ))

    def _pie_pagina(canvas, doc_):
        canvas.saveState()
        canvas.setFont(FUENTE_REGULAR, 7.5)
        canvas.setFillColor(colors.HexColor('#8A9186'))
        canvas.drawRightString(letter[0] - 42, 24, f'Página {doc_.page}')
        canvas.restoreState()

    doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
    print(f"📄 PDF generado: {nombre_archivo}")


# === 5. GENERAR HTML ===
def generar_html(productos):
    """Genera un HTML interactivo con todos los productos, con diseño propio de marca."""

    total = len(productos)
    if total == 0:
        print("❌ No hay productos para mostrar")
        return None

    productos.sort(key=lambda x: x['nombre'].lower())

    fecha_actual = datetime.now().strftime('%d/%m/%Y %H:%M')

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cuadro de Compras · Alvi</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --ink: #17241D;
            --ink-soft: #4C5A50;
            --green: #2E6B4F;
            --green-dark: #1F4A37;
            --mustard: #E2A73B;
            --mustard-deep: #C98826;
            --clay: #C24C3A;
            --paper: #F3F5EE;
            --paper-alt: #EAEDE1;
            --line: #DBDECF;
            --white: #FFFFFF;
            --font-display: 'Fraunces', Georgia, serif;
            --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: var(--font-body);
            background: var(--paper);
            color: var(--ink);
            padding: 0 0 120px;
        }}

        /* ===== Encabezado de marca ===== */
        .marca {{
            background: var(--green-dark);
            color: var(--white);
            padding: 34px 28px 26px;
            border-bottom: 5px solid var(--mustard);
        }}
        .marca-inner {{
            max-width: 1180px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .marca h1 {{
            font-family: var(--font-display);
            font-weight: 600;
            font-size: clamp(1.8em, 4vw, 2.6em);
            line-height: 1.05;
        }}
        .marca .kicker {{
            font-size: 0.85em;
            letter-spacing: 0.02em;
            color: #BFE0CD;
            margin-bottom: 6px;
        }}
        .marca .meta {{
            font-size: 0.95em;
            color: #CFE0D6;
            text-align: right;
        }}

        .envoltura {{
            max-width: 1180px;
            margin: 0 auto;
            padding: 24px 28px 0;
        }}

        /* ===== Barra de filtro ===== */
        .filtro {{
            display: flex;
            gap: 12px;
            margin-bottom: 22px;
            flex-wrap: wrap;
            align-items: center;
        }}
        .filtro input {{
            padding: 12px 16px;
            border: 1.5px solid var(--line);
            border-radius: 8px;
            font-family: var(--font-body);
            font-size: 15px;
            flex: 1;
            min-width: 220px;
            background: var(--white);
            color: var(--ink);
        }}
        .filtro input:focus {{
            border-color: var(--green);
            outline: none;
        }}
        .filtro button {{
            padding: 11px 18px;
            border-radius: 8px;
            font-family: var(--font-body);
            font-weight: 600;
            font-size: 14px;
            cursor: pointer;
            border: 1.5px solid var(--line);
            background: var(--white);
            color: var(--ink);
            transition: border-color 0.15s, color 0.15s;
        }}
        .filtro button:hover {{ border-color: var(--green); color: var(--green-dark); }}
        .filtro button.principal {{
            background: var(--green);
            border-color: var(--green);
            color: var(--white);
        }}
        .filtro button.principal:hover {{ background: var(--green-dark); border-color: var(--green-dark); color: var(--white); }}

        /* ===== Tabla ===== */
        .table-container {{
            background: var(--white);
            border: 1px solid var(--line);
            border-radius: 10px;
            overflow: hidden;
        }}
        .table-scroll {{
            overflow-x: auto;
            max-height: 68vh;
            overflow-y: auto;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 720px;
        }}
        th {{
            background: var(--green-dark);
            color: var(--white);
            font-family: var(--font-body);
            font-weight: 600;
            font-size: 0.85em;
            padding: 13px 16px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 11px 16px;
            border-bottom: 1px solid var(--line);
            vertical-align: middle;
            font-size: 0.95em;
        }}
        tbody tr:nth-child(even) {{ background: var(--paper); }}
        tbody tr:hover {{ background: #EAF2EC; }}

        .producto-img {{
            width: 46px;
            height: 46px;
            object-fit: contain;
            border-radius: 6px;
            background: var(--paper-alt);
            border: 1px solid var(--line);
        }}
        .precio {{
            font-weight: 700;
            color: var(--ink);
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}
        .numero {{ color: #9AA394; font-size: 0.9em; font-variant-numeric: tabular-nums; }}

        .cantidad-input {{
            width: 48px;
            padding: 6px 4px;
            border: 1.5px solid var(--line);
            border-radius: 6px;
            text-align: center;
            font-family: var(--font-body);
            font-size: 13px;
        }}
        .cantidad-input:focus {{ border-color: var(--green); outline: none; }}

        .btn-agregar {{
            padding: 7px 14px;
            background: var(--mustard);
            color: var(--ink);
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-family: var(--font-body);
            font-size: 12.5px;
            font-weight: 700;
            transition: background 0.15s;
        }}
        .btn-agregar:hover {{ background: var(--mustard-deep); }}
        .btn-agregar.agregado {{ background: var(--paper-alt); color: var(--ink-soft); cursor: default; }}

        .checkbox {{ width: 17px; height: 17px; cursor: pointer; accent-color: var(--green); }}

        /* ===== Carrito ===== */
        .carrito {{
            position: fixed;
            right: 24px;
            bottom: 24px;
            background: var(--white);
            border: 1.5px solid var(--line);
            border-top: 4px solid var(--mustard);
            border-radius: 12px;
            width: 340px;
            max-height: 62vh;
            box-shadow: 0 12px 30px rgba(23, 36, 29, 0.16);
            z-index: 1000;
            display: flex;
            flex-direction: column;
        }}
        .carrito-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 18px 10px;
        }}
        .carrito-header h3 {{
            font-family: var(--font-display);
            font-weight: 600;
            font-size: 1.15em;
            color: var(--green-dark);
        }}
        .badge {{
            background: var(--green);
            color: var(--white);
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 700;
            font-family: var(--font-body);
        }}
        #listaCarrito {{
            padding: 0 18px;
            overflow-y: auto;
            flex: 1;
        }}
        .carrito-item {{
            display: flex;
            justify-content: space-between;
            gap: 8px;
            padding: 7px 0;
            border-bottom: 1px solid var(--line);
            font-size: 13px;
        }}
        .carrito-item span:first-child {{ color: var(--ink-soft); }}
        .carrito-item span:last-child {{ font-weight: 600; white-space: nowrap; }}
        .carrito-vacio {{ color: #9AA394; text-align: center; padding: 18px 0; font-size: 14px; }}

        .carrito-footer {{ padding: 12px 18px 16px; }}
        .carrito-total {{
            font-family: var(--font-display);
            font-weight: 600;
            font-size: 1.3em;
            color: var(--mustard-deep);
            padding: 10px 0;
            border-top: 1.5px solid var(--line);
            margin-bottom: 8px;
        }}
        .carrito-footer button {{
            border: none;
            border-radius: 7px;
            width: 100%;
            padding: 9px;
            cursor: pointer;
            font-family: var(--font-body);
            font-weight: 700;
            font-size: 13px;
            margin-top: 6px;
            transition: filter 0.15s;
        }}
        .carrito-footer button:hover {{ filter: brightness(0.94); }}
        .btn-resumen {{ background: var(--green); color: var(--white); }}
        .btn-pdf {{ background: var(--ink); color: var(--white); }}
        .btn-vaciar {{ background: transparent; color: var(--clay); border: 1.5px solid var(--clay) !important; }}

        @media (max-width: 768px) {{
            .envoltura {{ padding: 20px 16px 0; }}
            .marca {{ padding: 26px 16px 20px; }}
            .carrito {{ left: 12px; right: 12px; bottom: 12px; width: auto; max-height: 55vh; }}
        }}
    </style>
</head>
<body>
    <header class="marca">
        <div class="marca-inner">
            <div>
                <div class="kicker">Cuadro de compras</div>
                <h1>Alvi</h1>
            </div>
            <div class="meta">{fecha_actual}<br>{total} productos disponibles</div>
        </div>
    </header>

    <div class="envoltura">
        <div class="filtro">
            <input type="text" id="buscar" placeholder="Buscar producto..." onkeyup="filtrar()">
            <button class="principal" onclick="seleccionarTodos()">Seleccionar todos</button>
            <button onclick="limpiarSeleccion()">Limpiar</button>
        </div>

        <div class="table-container">
            <div class="table-scroll">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 40px;">N°</th>
                            <th style="width: 40px;"></th>
                            <th style="width: 58px;">Imagen</th>
                            <th>Producto</th>
                            <th style="text-align: right; width: 110px;">Precio</th>
                            <th style="width: 150px; text-align: center;">Acción</th>
                        </tr>
                    </thead>
                    <tbody id="tabla">
"""

    for idx, p in enumerate(productos, 1):
        nombre = p['nombre']
        precio = p['precio']
        imagen = p.get('imagen', '')
        nombre_js = nombre.replace("'", "\\'")

        html += f"""
                        <tr>
                            <td><span class="numero">{idx}</span></td>
                            <td><input type="checkbox" class="checkbox" onchange="actualizarContador()"></td>
                            <td><img class="producto-img" src="{imagen}" alt="{nombre}" loading="lazy" onerror="this.style.display='none'"></td>
                            <td>{nombre}</td>
                            <td class="precio" style="text-align: right;">${precio:,.0f}</td>
                            <td style="text-align: center;">
                                <input type="number" class="cantidad-input" id="cantidad_{idx}" value="1" min="1" max="99">
                                <button class="btn-agregar" onclick="agregarAlCarrito('{nombre_js}', {precio}, this, {idx})">Agregar</button>
                            </td>
                        </tr>
        """

    html += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="carrito" id="carrito">
        <div class="carrito-header">
            <h3>Carrito</h3>
            <span class="badge" id="badge">0</span>
        </div>
        <div id="listaCarrito">
            <p class="carrito-vacio">No hay productos</p>
        </div>
        <div class="carrito-footer">
            <div class="carrito-total" id="totalCarrito">Total: $0</div>
            <button class="btn-resumen" onclick="generarResumen()">Generar resumen</button>
            <button class="btn-pdf" onclick="generarPDF()">Descargar PDF</button>
            <button class="btn-vaciar" onclick="vaciarCarrito()">Vaciar carrito</button>
        </div>
    </div>

    <script>
        let carrito = [];

        function agregarAlCarrito(nombre, precio, btn, idx) {
            const cantidadInput = document.getElementById('cantidad_' + idx);
            const cantidad = parseInt(cantidadInput.value) || 1;

            const existente = carrito.find(item => item.nombre === nombre);
            if (existente) {
                existente.cantidad += cantidad;
                actualizarCarrito();
                btn.textContent = 'Actualizado';
                setTimeout(() => { btn.textContent = 'Agregar'; }, 1600);
                return;
            }

            carrito.push({nombre, precio, cantidad});
            btn.textContent = 'Agregado';
            btn.className = 'btn-agregar agregado';
            btn.disabled = true;
            actualizarCarrito();
        }

        function actualizarCarrito() {
            const lista = document.getElementById('listaCarrito');
            const totalEl = document.getElementById('totalCarrito');
            const badge = document.getElementById('badge');

            if (carrito.length === 0) {
                lista.innerHTML = '<p class="carrito-vacio">No hay productos</p>';
                totalEl.textContent = 'Total: $0';
                badge.textContent = '0';
                return;
            }

            let html = '';
            let total = 0;
            carrito.forEach((item) => {
                const subtotal = item.precio * item.cantidad;
                total += subtotal;
                html += `<div class="carrito-item">
                    <span>${item.nombre} x${item.cantidad}</span>
                    <span>$${subtotal.toLocaleString()}</span>
                </div>`;
            });

            lista.innerHTML = html;
            totalEl.textContent = `Total: $${total.toLocaleString()}`;
            badge.textContent = carrito.reduce((sum, item) => sum + item.cantidad, 0);
        }

        function vaciarCarrito() {
            if (carrito.length === 0) return;
            if (!confirm('¿Vaciar carrito?')) return;

            carrito = [];
            document.querySelectorAll('.btn-agregar').forEach(btn => {
                btn.textContent = 'Agregar';
                btn.className = 'btn-agregar';
                btn.disabled = false;
            });
            document.querySelectorAll('.checkbox').forEach(cb => cb.checked = false);
            actualizarCarrito();
            actualizarContador();
        }

        function seleccionarTodos() {
            const checkboxes = document.querySelectorAll('.checkbox');
            checkboxes.forEach((cb) => {
                cb.checked = true;
                const row = cb.closest('tr');
                const btn = row.querySelector('.btn-agregar');
                if (btn && !btn.disabled) btn.click();
            });
            actualizarContador();
        }

        function limpiarSeleccion() {
            vaciarCarrito();
        }

        function actualizarContador() {
            const checkboxes = document.querySelectorAll('.checkbox:checked');
            document.getElementById('badge').textContent = checkboxes.length;
        }

        function normalizarTexto(texto) {
            return texto.normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').toLowerCase();
        }

        function filtrar() {
            const q = normalizarTexto(document.getElementById('buscar').value);
            const rows = document.querySelectorAll('#tabla tr');
            rows.forEach(row => {
                const texto = normalizarTexto(row.textContent);
                row.style.display = texto.includes(q) ? '' : 'none';
            });
        }

        function generarResumen() {
            if (carrito.length === 0) {
                alert('No hay productos en el carrito');
                return;
            }

            let msg = 'LISTA DE COMPRAS\\n';
            msg += '='.repeat(60) + '\\n\\n';
            let total = 0;
            carrito.forEach((item, idx) => {
                const subtotal = item.precio * item.cantidad;
                msg += `${idx+1}. ${item.nombre}\\n`;
                msg += `   Cantidad: ${item.cantidad} x $${item.precio.toLocaleString()} = $${subtotal.toLocaleString()}\\n\\n`;
                total += subtotal;
            });
            msg += '='.repeat(60) + '\\n';
            msg += `TOTAL: $${total.toLocaleString()}\\n`;
            msg += `Productos: ${carrito.reduce((sum, item) => sum + item.cantidad, 0)}`;
            alert(msg);
        }

        function generarPDF() {
            if (carrito.length === 0) {
                alert('No hay productos en el carrito');
                return;
            }

            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/generar_pdf';

            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'carrito';
            input.value = JSON.stringify(carrito);
            form.appendChild(input);

            document.body.appendChild(form);
            form.submit();
            document.body.removeChild(form);
        }
    </script>
</body>
</html>
"""
    return html


# === 6. GENERAR PDF DESDE PYTHON ===
def generar_pdf_desde_carrito(carrito_data):
    """Genera un PDF a partir de los datos del carrito"""
    try:
        productos = json.loads(carrito_data)
        nombre_archivo = f'lista_compras_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        generar_pdf(productos, nombre_archivo)
        return nombre_archivo
    except Exception:
        return None


# === 7. EJECUTAR ===
def main():
    print("=" * 70)
    print("📊 GENERADOR DE CUADRO DE COMPRAS - ALVI")
    print("=" * 70)

    productos_raw = unificar_archivos()
    print(f"\n📦 Total sin limpiar: {len(productos_raw)} productos")

    productos = eliminar_duplicados(productos_raw)
    print(f"✅ Después de limpiar: {len(productos)} productos únicos")

    df = pd.DataFrame(productos)
    df.to_csv('alvi_cuadro_compras.csv', index=False, encoding='utf-8-sig')
    print("💾 CSV guardado: alvi_cuadro_compras.csv")

    with open('alvi_productos_unificados.json', 'w', encoding='utf-8') as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)
    print("💾 JSON guardado: alvi_productos_unificados.json")

    print("\n🌐 Generando HTML interactivo...")
    html = generar_html(productos)
    if html:
        nombre_archivo = f'alvi_cuadro_compras_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        with open(nombre_archivo, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"✅ HTML generado: {nombre_archivo}")
        webbrowser.open(nombre_archivo)
        print("\n🚀 Se abrió el HTML en tu navegador")

    print("\n💡 TIPS:")
    print("   • Usa el buscador para encontrar productos (no distingue acentos)")
    print("   • Ingresa la cantidad deseada antes de agregar")
    print("   • Genera el resumen para ver el total")
    print("   • Descarga el PDF con el botón correspondiente")
    print("=" * 70)


if __name__ == "__main__":
    main()
