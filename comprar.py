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

# === CONFIGURACIÓN DE PÁGINA ===
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

# === ESTILOS CSS PERSONALIZADOS ===
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
    
    /* Contenedor principal */
    .main-container {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 1rem 2rem;
    }}
    
    /* Encabezado de marca */
    .marca {{
        background: {GREEN_DARK};
        color: white;
        padding: 2rem 2rem 1.5rem;
        border-radius: 12px 12px 0 0;
        border-bottom: 5px solid {MUSTARD};
        margin-bottom: 1.5rem;
    }}
    .marca h1 {{
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        font-family: 'Georgia', serif;
    }}
    .marca .kicker {{
        font-size: 0.85rem;
        opacity: 0.8;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}
    .marca .meta {{
        text-align: right;
        opacity: 0.85;
        font-size: 0.9rem;
    }}
    
    /* Stats */
    .stats {{
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
    }}
    .stat-card {{
        background: white;
        padding: 0.8rem 1.5rem;
        border-radius: 8px;
        border-left: 4px solid {MUSTARD};
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }}
    .stat-card .num {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {GREEN_DARK};
    }}
    .stat-card .label {{
        font-size: 0.8rem;
        color: #666;
    }}
    
    /* Tabla */
    .table-container {{
        background: white;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        overflow: hidden;
    }}
    .table-scroll {{
        max-height: 500px;
        overflow-y: auto;
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
    }}
    th {{
        background: {GREEN_DARK};
        color: white;
        padding: 0.7rem 0.8rem;
        text-align: left;
        position: sticky;
        top: 0;
        z-index: 10;
        font-weight: 600;
    }}
    td {{
        padding: 0.6rem 0.8rem;
        border-bottom: 1px solid #eee;
        vertical-align: middle;
    }}
    tbody tr:nth-child(even) {{ background: #f8faf7; }}
    tbody tr:hover {{ background: #eaf2ec; }}
    
    .precio {{
        font-weight: 700;
        color: {INK};
        text-align: right;
    }}
    .producto-img {{
        width: 40px;
        height: 40px;
        object-fit: contain;
        border-radius: 4px;
        background: #f0f2ee;
        border: 1px solid #e0e0e0;
    }}
    
    /* Carrito flotante */
    .carrito-flotante {{
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: white;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        border-top: 4px solid {MUSTARD};
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        width: 320px;
        max-height: 60vh;
        display: flex;
        flex-direction: column;
        z-index: 1000;
        padding: 1rem;
    }}
    .carrito-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }}
    .carrito-header h3 {{
        font-size: 1.1rem;
        font-weight: 700;
        color: {GREEN_DARK};
        margin: 0;
    }}
    .badge {{
        background: {GREEN};
        color: white;
        padding: 0.1rem 0.7rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }}
    .carrito-items {{
        flex: 1;
        overflow-y: auto;
        max-height: 200px;
        font-size: 0.85rem;
    }}
    .carrito-item {{
        display: flex;
        justify-content: space-between;
        padding: 0.3rem 0;
        border-bottom: 1px solid #eee;
    }}
    .carrito-total {{
        font-weight: 700;
        font-size: 1.1rem;
        color: {MUSTARD};
        padding-top: 0.5rem;
        border-top: 2px solid #eee;
        margin-top: 0.5rem;
        text-align: right;
    }}
    .btn-pdf {{
        background: {INK};
        color: white;
        border: none;
        padding: 0.5rem;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
        margin-top: 0.5rem;
    }}
    .btn-pdf:hover {{
        opacity: 0.85;
    }}
    .btn-vaciar {{
        background: transparent;
        color: {CLAY};
        border: 1.5px solid {CLAY};
        padding: 0.4rem;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
        margin-top: 0.3rem;
    }}
    .btn-vaciar:hover {{
        background: {CLAY};
        color: white;
    }}
    
    /* Botón de cantidad */
    .cantidad-input {{
        width: 48px;
        padding: 0.25rem 0.2rem;
        border: 1.5px solid #ddd;
        border-radius: 4px;
        text-align: center;
        font-size: 0.85rem;
    }}
    .btn-agregar {{
        background: {MUSTARD};
        color: {INK};
        border: none;
        padding: 0.25rem 0.7rem;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.75rem;
        cursor: pointer;
        transition: background 0.15s;
    }}
    .btn-agregar:hover {{
        background: #d49a2e;
    }}
    .btn-agregar.agregado {{
        background: #e0e0e0;
        color: #888;
        cursor: default;
    }}
    
    /* Buscador */
    .buscador {{
        width: 100%;
        padding: 0.6rem 1rem;
        border: 1.5px solid #ddd;
        border-radius: 6px;
        font-size: 0.95rem;
        margin-bottom: 1rem;
    }}
    .buscador:focus {{
        border-color: {GREEN};
        outline: none;
    }}
    
    /* Responsive */
    @media (max-width: 768px) {{
        .marca h1 {{ font-size: 1.6rem; }}
        .marca .meta {{ text-align: left; margin-top: 0.5rem; }}
        .carrito-flotante {{
            width: calc(100% - 2rem);
            right: 1rem;
            bottom: 1rem;
            max-height: 50vh;
        }}
        .stats {{ gap: 0.5rem; }}
        .stat-card {{ padding: 0.5rem 1rem; }}
        .stat-card .num {{ font-size: 1.2rem; }}
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

# === FUNCIONES ===
def normalizar_texto(texto):
    """Normaliza texto eliminando acentos y convirtiendo a minúsculas."""
    import unicodedata
    return unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('ascii').lower()

def cargar_productos():
    """Carga los productos desde los archivos pag*.json"""
    todos = []
    for i in range(1, 20):
        archivo = f'pag{i}.json'
        if os.path.exists(archivo):
            try:
                with open(archivo, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    if isinstance(datos, list):
                        todos.extend(datos)
            except:
                pass
    return todos

def generar_pdf_bytes(productos):
    """Genera un PDF en memoria y retorna los bytes"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Estilos
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
        # Normalizar nombres
        for p in st.session_state.productos:
            if 'nombre' in p:
                # Normalización básica (puedes usar tu función normalizar_nombre aquí)
                pass

productos = st.session_state.productos

# === INTERFAZ ===
# Encabezado
st.markdown(f"""
<div class="marca">
    <div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;">
        <div>
            <div class="kicker">Cuadro de compras</div>
            <h1>Alvi</h1>
        </div>
        <div class="meta">
            {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
            {len(productos)} productos disponibles
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Stats
precios = [p.get('precio', 0) for p in productos if p.get('precio', 0) > 0]
st.markdown(f"""
<div class="stats">
    <div class="stat-card"><div class="num">{len(productos)}</div><div class="label">Total productos</div></div>
    <div class="stat-card"><div class="num">${min(precios) if precios else 0:,.0f}</div><div class="label">Más barato</div></div>
    <div class="stat-card"><div class="num">${max(precios) if precios else 0:,.0f}</div><div class="label">Más caro</div></div>
    <div class="stat-card"><div class="num">${sum(precios)//len(precios) if precios else 0:,.0f}</div><div class="label">Precio promedio</div></div>
</div>
""", unsafe_allow_html=True)

# Buscador
busqueda = st.text_input("", placeholder="🔍 Buscar producto...", key="busqueda_input", label_visibility="collapsed")
st.session_state.busqueda = busqueda

# Filtrar productos
productos_filtrados = productos
if busqueda:
    busq_norm = normalizar_texto(busqueda)
    productos_filtrados = [p for p in productos if busq_norm in normalizar_texto(p.get('nombre', ''))]

# Tabla de productos
st.markdown('<div class="table-container"><div class="table-scroll">', unsafe_allow_html=True)

cols = st.columns([0.4, 0.4, 0.8, 4, 1.2, 1.8])
with cols[0]:
    st.markdown("**N°**")
with cols[1]:
    st.markdown("**✓**")
with cols[2]:
    st.markdown("**Img**")
with cols[3]:
    st.markdown("**Producto**")
with cols[4]:
    st.markdown("**Precio**")
with cols[5]:
    st.markdown("**Acción**")

for idx, p in enumerate(productos_filtrados, 1):
    cols = st.columns([0.4, 0.4, 0.8, 4, 1.2, 1.8])
    with cols[0]:
        st.markdown(f'<span style="color:#9AA394;font-size:0.9rem;">{idx}</span>', unsafe_allow_html=True)
    with cols[1]:
        checked = st.checkbox("", key=f"chk_{idx}", label_visibility="collapsed")
    with cols[2]:
        imagen = p.get('imagen', '')
        if imagen:
            st.image(imagen, width=40)
        else:
            st.markdown('<span style="color:#ccc;">📦</span>', unsafe_allow_html=True)
    with cols[3]:
        st.markdown(f'<span style="font-size:0.9rem;">{p.get("nombre", "")}</span>', unsafe_allow_html=True)
    with cols[4]:
        precio = p.get('precio', 0)
        st.markdown(f'<span style="font-weight:700;color:{INK};text-align:right;display:block;">${precio:,.0f}</span>', unsafe_allow_html=True)
    with cols[5]:
        cant = st.number_input("", min_value=1, max_value=99, value=1, key=f"cant_{idx}", label_visibility="collapsed")
        if st.button("Agregar", key=f"btn_{idx}"):
            # Verificar si ya está en el carrito
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

# === CARRITO FLOTANTE ===
carrito = st.session_state.carrito
total_carrito = sum(item['precio'] * item['cantidad'] for item in carrito)

st.markdown(f"""
<div class="carrito-flotante">
    <div class="carrito-header">
        <h3>🛒 Carrito</h3>
        <span class="badge">{sum(item['cantidad'] for item in carrito)}</span>
    </div>
    <div class="carrito-items">
        {''.join([f'<div class="carrito-item"><span>{item["nombre"]} x{item["cantidad"]}</span><span>${item["precio"] * item["cantidad"]:,.0f}</span></div>' for item in carrito]) if carrito else '<div style="color:#999;text-align:center;padding:1rem 0;">No hay productos</div>'}
    </div>
    <div class="carrito-total">Total: ${total_carrito:,.0f}</div>
    <button class="btn-pdf" onclick="alert('Descargando PDF...')">📄 Descargar PDF</button>
    <button class="btn-vaciar" onclick="alert('Vaciar carrito')">🗑️ Vaciar carrito</button>
</div>
""", unsafe_allow_html=True)

# === SIDEBAR PARA PDF ===
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