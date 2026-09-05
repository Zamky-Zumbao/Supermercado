import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import base64
import unicodedata

# === CONFIGURACIÓN DE PÁGINA (MÓVIL) ===
st.set_page_config(
    page_title="Cuadro de Compras · Alvi",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# === PALETA DE MARCA ===
INK = "#17241D"
GREEN = "#2E6B4F"
GREEN_DARK = "#1F4A37"
MUSTARD = "#E2A73B"
CLAY = "#C24C3A"
PAPER = "#F3F5EE"

# === CSS MEJORADO PARA MÓVIL ===
st.markdown(f"""
<style>
    /* Ocultar elementos de Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* Fondo general */
    .stApp {{
        background-color: {PAPER};
    }}
    
    /* Contenedor principal - responsive */
    .main-container {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 0.5rem 5rem;
    }}
    
    /* Encabezado de marca - solo título */
    .marca {{
        background: {GREEN_DARK};
        color: white;
        padding: 0.9rem 1rem;
        border-radius: 10px 10px 0 0;
        border-bottom: 4px solid {MUSTARD};
        margin-bottom: 1rem;
        text-align: center;
    }}
    .marca h1 {{
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        font-family: 'Georgia', serif;
        line-height: 1.2;
    }}
    
    /* Buscador - responsive */
    .buscador {{
        width: 100%;
        padding: 0.7rem 0.8rem;
        border: 1.5px solid #ddd;
        border-radius: 8px;
        font-size: 0.9rem;
        margin-bottom: 0.8rem;
        background: white;
    }}
    .buscador:focus {{
        border-color: {GREEN};
        outline: none;
    }}
    
    /* Tabla - responsive móvil */
    .table-container {{
        background: white;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
        margin-bottom: 1rem;
    }}
    .table-scroll {{
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }}
    
    .precio {{
        font-weight: 700;
        color: {INK};
        text-align: right;
        white-space: nowrap;
        font-size: 0.8rem;
    }}
    .producto-img {{ display: none; }}
    .nombre-producto {{
        font-size: 0.8rem;
        line-height: 1.2;
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }}
    .header-celda {{
        font-size: 0.7rem;
        font-weight: 700;
        color: {GREEN_DARK};
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    .numero {{
        color: #9AA394;
        font-size: 0.7rem;
        white-space: nowrap;
    }}
    
    /* === FORZAR UNA SOLA FILA POR ARTÍCULO, TAMBIÉN EN MÓVIL ===
       Por defecto, Streamlit apila las columnas verticalmente en pantallas
       angostas. Esto rompe el diseño de "un producto = una fila". Las
       reglas de abajo obligan a que las columnas se mantengan en línea
       (row) y solo se encojan, sin apilarse, en cualquier ancho. */
    div[data-testid="stHorizontalBlock"] {{
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0.3rem !important;
    }}
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
        min-width: 0 !important;
        width: auto !important;
        flex: 1 1 0 !important;
    }}
    div[data-testid="stColumn"] div[data-testid="stNumberInput"] input {{
        padding: 0.15rem 0.1rem;
        font-size: 0.75rem;
        min-height: 0;
    }}
    div[data-testid="stColumn"] div[data-testid="stNumberInput"] button {{
        display: none;
    }}
    div[data-testid="stColumn"] button {{
        padding: 0.25rem 0.2rem !important;
        font-size: 0.85rem !important;
        min-height: 0 !important;
    }}
    
    
    /* Carrito flotante - colapsable, ocupa poco espacio por defecto */
    details.carrito-flotante {{
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        border-top: 3px solid {MUSTARD};
        box-shadow: 0 -4px 20px rgba(0,0,0,0.1);
        z-index: 1000;
        border-radius: 12px 12px 0 0;
        overflow: hidden;
    }}
    /* Barra siempre visible (cerrada): compacta, no tapa la pantalla */
    details.carrito-flotante > summary {{
        list-style: none;
        cursor: pointer;
        padding: 0.6rem 0.8rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    details.carrito-flotante > summary::-webkit-details-marker {{ display: none; }}
    details.carrito-flotante > summary .carrito-header h3 {{
        font-size: 0.9rem;
    }}
    /* Contenido expandido: limitado a una porción razonable de la pantalla */
    .carrito-body {{
        padding: 0 0.8rem 0.7rem;
        max-height: 45vh;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
    }}
    .carrito-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.3rem;
        flex: 1;
    }}
    .carrito-header h3 {{
        font-size: 0.95rem;
        font-weight: 700;
        color: {GREEN_DARK};
        margin: 0;
    }}
    .carrito-chevron {{
        font-size: 0.75rem;
        color: #999;
        margin-left: 0.5rem;
        transition: transform 0.2s;
    }}
    details[open].carrito-flotante .carrito-chevron {{
        transform: rotate(180deg);
    }}
    .badge {{
        background: {GREEN};
        color: white;
        padding: 0.05rem 0.6rem;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
    }}
    .carrito-items {{
        font-size: 0.75rem;
        margin-bottom: 0.3rem;
    }}
    .carrito-item {{
        display: flex;
        justify-content: space-between;
        padding: 0.2rem 0;
        border-bottom: 1px solid #eee;
        gap: 0.5rem;
    }}
    .carrito-item .nombre {{
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .carrito-total {{
        font-weight: 700;
        font-size: 0.95rem;
        color: {MUSTARD};
        text-align: right;
        padding-top: 0.3rem;
        border-top: 2px solid #eee;
        margin-top: 0.3rem;
    }}
    .carrito-actions {{
        display: flex;
        gap: 0.4rem;
        margin-top: 0.3rem;
    }}
    .btn-pdf {{
        background: {INK};
        color: white;
        border: none;
        padding: 0.4rem 0;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        cursor: pointer;
        flex: 1;
    }}
    .btn-pdf:hover {{ opacity: 0.85; }}
    .btn-vaciar {{
        background: transparent;
        color: {CLAY};
        border: 1.5px solid {CLAY};
        padding: 0.4rem 0;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        cursor: pointer;
        flex: 1;
    }}
    .btn-vaciar:hover {{
        background: {CLAY};
        color: white;
    }}
    
    
    /* Espaciado para que el carrito (cerrado) no tape el contenido */
    .spacer-bottom {{
        height: 60px;
    }}
    
    /* Scrollbar personalizada */
    ::-webkit-scrollbar {{
        width: 4px;
        height: 4px;
    }}
    ::-webkit-scrollbar-track {{
        background: #f1f1f1;
    }}
    ::-webkit-scrollbar-thumb {{
        background: {GREEN};
        border-radius: 4px;
    }}
    
    /* Mejoras para móvil muy pequeño */
    @media (max-width: 480px) {{
        .marca h1 {{ font-size: 1.3rem; }}
        .nombre-producto {{ font-size: 0.72rem; }}
        .precio {{ font-size: 0.72rem; }}
        div[data-testid="stColumn"] button {{ font-size: 0.75rem !important; }}
        details.carrito-flotante > summary {{ padding: 0.5rem 0.6rem; }}
        .carrito-body {{ padding: 0 0.6rem 0.6rem; }}
        .carrito-header h3 {{ font-size: 0.8rem; }}
        .carrito-total {{ font-size: 0.8rem; }}
        .carrito-actions .btn-pdf, .carrito-actions .btn-vaciar {{ font-size: 0.65rem; padding: 0.3rem 0; }}
    }}
    
    @media (min-width: 769px) {{
        details.carrito-flotante {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            left: auto;
            width: 340px;
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            border-top: 4px solid {MUSTARD};
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }}
        .carrito-body {{
            max-height: 50vh;
        }}
        .spacer-bottom {{
            height: 0;
        }}
        .marca h1 {{ font-size: 2.2rem; }}
        .marca {{ padding: 1.4rem 2rem; }}
    }}
</style>
""", unsafe_allow_html=True)

# === INICIALIZAR ESTADO DE SESIÓN ===
if 'carrito' not in st.session_state:
    st.session_state.carrito = []
if 'productos' not in st.session_state:
    st.session_state.productos = []
if 'busqueda' not in st.session_state:
    st.session_state.busqueda = ""
if 'pagina' not in st.session_state:
    st.session_state.pagina = 1
if 'carrito_abierto' not in st.session_state:
    st.session_state.carrito_abierto = False

# === FUNCIONES ===
def normalizar_texto(texto):
    """Normaliza texto eliminando acentos y convirtiendo a minúsculas."""
    return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('ascii').lower()

@st.cache_data(show_spinner=False)
def cargar_productos():
    """Carga los productos desde los archivos pag*.json (cacheado para no releer en cada rerun)."""
    todos = []
    for i in range(1, 20):
        archivo = f'pag{i}.json'
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    if isinstance(datos, list):
                        todos.extend(datos)
            except Exception:
                pass
    return todos

def generar_pdf_bytes(productos):
    """Genera un PDF en memoria y retorna los bytes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    titulo_style = ParagraphStyle('Titulo', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER, fontName='Helvetica-Bold')
    encabezado_style = ParagraphStyle('Encabezado', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold')
    celda_style = ParagraphStyle('Celda', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT, fontName='Helvetica')
    precio_style = ParagraphStyle('Precio', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT, fontName='Helvetica')
    
    data = [[
        Paragraph('N°', encabezado_style),
        Paragraph('Producto', encabezado_style),
        Paragraph('Cant.', encabezado_style),
        Paragraph('Precio', encabezado_style),
        Paragraph('Subtotal', encabezado_style)
    ]]
    
    total = 0
    for idx, p in enumerate(productos, 1):
        subtotal = p['precio'] * p['cantidad']
        total += subtotal
        data.append([
            Paragraph(str(idx), celda_style),
            Paragraph(p['nombre'], celda_style),
            Paragraph(str(p['cantidad']), celda_style),
            Paragraph(f"${p['precio']:,.0f}", precio_style),
            Paragraph(f"${subtotal:,.0f}", precio_style)
        ])
    
    data.append(['', '', '', Paragraph('TOTAL', encabezado_style), Paragraph(f"${total:,.0f}", precio_style)])
    
    tabla = Table(data, colWidths=[0.5*inch, 3.5*inch, 0.7*inch, 1*inch, 1.2*inch])
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E6B4F')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (3, -1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    
    elementos = []
    elementos.append(Paragraph('LISTA DE COMPRAS - ALVI', titulo_style))
    elementos.append(Paragraph(f'Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}', titulo_style))
    elementos.append(Spacer(1, 0.2*inch))
    elementos.append(tabla)
    
    doc.build(elementos)
    return buffer.getvalue()

# === CARGAR PRODUCTOS ===
if not st.session_state.productos:
    with st.spinner('Cargando productos...'):
        st.session_state.productos = cargar_productos()

productos = st.session_state.productos

# === INTERFAZ PRINCIPAL ===
# Encabezado: solo el título "Compras"
st.markdown(f"""
<div class="marca">
    <h1>Compras</h1>
</div>
""", unsafe_allow_html=True)

# Buscador
busqueda = st.text_input("", placeholder="🔍 Buscar producto...", key="busqueda_input", label_visibility="collapsed")

# Si cambia la búsqueda, volvemos a la página 1
if busqueda != st.session_state.busqueda:
    st.session_state.pagina = 1
st.session_state.busqueda = busqueda

# Filtrar productos
productos_filtrados = productos
if busqueda:
    busq_norm = normalizar_texto(busqueda)
    productos_filtrados = [p for p in productos if busq_norm in normalizar_texto(p.get('nombre', ''))]

# === PAGINACIÓN ===
# Renderizar cientos de filas (con su imagen y widgets) de una sola vez es la
# principal causa de que la app se sienta lenta. Mostramos de a POR_PAGINA
# productos y dejamos que el usuario avance/retroceda.
POR_PAGINA = 20
total_productos_filtrados = len(productos_filtrados)
total_paginas = max(1, (total_productos_filtrados - 1) // POR_PAGINA + 1)
st.session_state.pagina = min(max(1, st.session_state.pagina), total_paginas)

inicio = (st.session_state.pagina - 1) * POR_PAGINA
fin = inicio + POR_PAGINA
productos_pagina = productos_filtrados[inicio:fin]

# Tabla de productos
st.markdown('<div class="table-container"><div class="table-scroll">', unsafe_allow_html=True)

# Encabezados de tabla
cols = st.columns([0.4, 3.2, 1.1, 1, 1.1])
with cols[0]:
    st.markdown('<span class="header-celda">N°</span>', unsafe_allow_html=True)
with cols[1]:
    st.markdown('<span class="header-celda">Producto</span>', unsafe_allow_html=True)
with cols[2]:
    st.markdown('<span class="header-celda" style="text-align:right;display:block;">Precio</span>', unsafe_allow_html=True)
with cols[3]:
    st.markdown('<span class="header-celda" style="text-align:center;display:block;">Cant.</span>', unsafe_allow_html=True)
with cols[4]:
    st.markdown('<span class="header-celda"></span>', unsafe_allow_html=True)
st.markdown(f'<hr style="margin:0.2rem 0 0.4rem;border:none;border-top:2px solid {GREEN_DARK};">', unsafe_allow_html=True)

for offset, p in enumerate(productos_pagina):
    idx = inicio + offset + 1
    cols = st.columns([0.4, 3.2, 1.1, 1, 1.1])
    with cols[0]:
        st.markdown(f'<span class="numero">{idx}</span>', unsafe_allow_html=True)
    with cols[1]:
        st.markdown(f'<span class="nombre-producto">{p.get("nombre", "")}</span>', unsafe_allow_html=True)
    with cols[2]:
        precio = p.get('precio', 0)
        st.markdown(f'<span class="precio">${precio:,.0f}</span>', unsafe_allow_html=True)
    with cols[3]:
        cant = st.number_input("", min_value=1, max_value=99, value=1, key=f"cant_{idx}", label_visibility="collapsed")
    with cols[4]:
        if st.button("➕", key=f"btn_{idx}", use_container_width=True):
            existente = next((item for item in st.session_state.carrito if item['nombre'] == p.get('nombre')), None)
            if existente:
                existente['cantidad'] += cant
            else:
                st.session_state.carrito.append({
                    'nombre': p.get('nombre'),
                    'precio': precio,
                    'cantidad': cant
                })
            st.rerun()

st.markdown('</div></div>', unsafe_allow_html=True)

# Controles de paginación
if total_paginas > 1:
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("⬅ Anterior", disabled=st.session_state.pagina <= 1, use_container_width=True):
            st.session_state.pagina -= 1
            st.rerun()
    with col_info:
        st.markdown(
            f'<div style="text-align:center;font-size:0.8rem;color:#666;padding-top:0.4rem;">'
            f'Página {st.session_state.pagina} de {total_paginas} '
            f'({total_productos_filtrados} productos)</div>',
            unsafe_allow_html=True,
        )
    with col_next:
        if st.button("Siguiente ➡", disabled=st.session_state.pagina >= total_paginas, use_container_width=True):
            st.session_state.pagina += 1
            st.rerun()

# Espaciador para que el carrito no tape contenido
st.markdown('<div class="spacer-bottom"></div>', unsafe_allow_html=True)

# === CARRITO FLOTANTE ===
carrito = st.session_state.carrito
total_carrito = sum(item['precio'] * item['cantidad'] for item in carrito)
total_items = sum(item['cantidad'] for item in carrito)

# Carrito HTML: <details>/<summary> nativo del navegador.
# Cerrado por defecto muestra solo una barra angosta (título + total), y al
# tocarla se expande. Así en móvil nunca tapa la mayor parte de la pantalla.
carrito_html = f"""
<details class="carrito-flotante">
    <summary>
        <div class="carrito-header">
            <h3>🛒 Carrito <span class="badge">{total_items}</span></h3>
        </div>
        <div style="display:flex;align-items:center;gap:0.4rem;">
            <span class="carrito-total" style="border:none;padding:0;margin:0;">${total_carrito:,.0f}</span>
            <span class="carrito-chevron">▲</span>
        </div>
    </summary>
    <div class="carrito-body">
        <div class="carrito-items">
            {''.join([f'<div class="carrito-item"><span class="nombre">{item["nombre"]}</span><span>x{item["cantidad"]}</span><span>${item["precio"] * item["cantidad"]:,.0f}</span></div>' for item in carrito]) if carrito else '<div style="color:#999;text-align:center;padding:0.5rem 0;font-size:0.8rem;">No hay productos</div>'}
        </div>
        <div class="carrito-total">Total: ${total_carrito:,.0f}</div>
        <div style="color:#999;font-size:0.7rem;text-align:center;margin-top:0.4rem;">
            Usa el menú ☰ (arriba a la izquierda) para descargar el PDF o vaciar el carrito
        </div>
    </div>
</details>
"""

st.markdown(carrito_html, unsafe_allow_html=True)

# === SIDEBAR PARA FUNCIONES ADICIONALES ===
with st.sidebar:
    st.markdown("## 📄 Exportar")
    
    if st.button("📥 Descargar PDF", use_container_width=True):
        if carrito:
            pdf_bytes = generar_pdf_bytes(carrito)
            st.download_button(
                label="⬇️ Click para descargar",
                data=pdf_bytes,
                file_name=f"lista_compras_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.warning("El carrito está vacío")
    
    if st.button("🗑️ Vaciar carrito", use_container_width=True):
        st.session_state.carrito = []
        st.rerun()
    
    st.markdown("---")
    st.caption(f"🛒 {len(carrito)} productos en carrito | Total: ${total_carrito:,.0f}")
