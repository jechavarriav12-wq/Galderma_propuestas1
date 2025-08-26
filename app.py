from flask import Flask, render_template, request, send_file, jsonify
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
import tempfile
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'clave_temporal_123')

def calcular_descuento(producto, unidades):
    """Calcula el descuento basado en el producto y la cantidad de unidades"""
    reglas_descuento = {
        'sculptra': [
            {'min': 2, 'max': 10, 'descuento': 0.34},
            {'min': 11, 'max': 21, 'descuento': 0.37},
            {'min': 22, 'max': 35, 'descuento': 0.39},
            {'min': 36, 'max': 55, 'descuento': 0.40},
            {'min': 56, 'max': float('inf'), 'descuento': 0.44}
        ],
        'restylane': [
            {'min': 2, 'max': 10, 'descuento': 0.32},
            {'min': 11, 'max': 21, 'descuento': 0.34},
            {'min': 22, 'max': 35, 'descuento': 0.40},
            {'min': 36, 'max': 55, 'descuento': 0.44},
            {'min': 56, 'max': float('inf'), 'descuento': 0.48}
        ],
        'skinboosters': [
            {'min': 2, 'max': 10, 'descuento': 0.32},
            {'min': 11, 'max': 21, 'descuento': 0.34},
            {'min': 22, 'max': 35, 'descuento': 0.40},
            {'min': 36, 'max': 55, 'descuento': 0.44},
            {'min': 56, 'max': float('inf'), 'descuento': 0.48}
        ]
    }
    
    if producto.lower() not in reglas_descuento:
        return 0.0
    
    if not isinstance(unidades, int) or unidades < 2:
        return 0.0
    
    reglas = reglas_descuento[producto.lower()]
    for regla in reglas:
        if regla['min'] <= unidades <= regla['max']:
            return regla['descuento']
    
    return 0.0

def calcular_descuento_porcentaje(producto, unidades):
    """Calcula el descuento y lo devuelve como porcentaje entero"""
    descuento_decimal = calcular_descuento(producto, unidades)
    return int(descuento_decimal * 100)

def generar_carta_pdf(data):
    """Genera el PDF y lo retorna como bytes en memoria"""
    
    # Crear PDF en memoria
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 72
    y = height - margin
    line_height = 18

    PRECIOS_LISTA = {
        'sculptra': 850000,
        'restylane': 320000,
        'skinboosters': 280000
    }

    IVA = 0.19
    DESCUENTO_PRONTO_PAGO = 0.05
    DESCUENTO_CROSS_SELLING = 0.03

    c.setFont("Helvetica", 11)

    # Encabezado
    encabezado = [
        "Carta de compromiso", "",
        f"Fecha: {data['Fecha actual']}",
        f"Cliente: {data['Cliente']}", "Ciudad:", "",
        "ASUNTO: PROPUESTA COMERCIAL PORTAFOLIO GALDERMA", "",
        "Estimados Doctores,", "",
        "Somos una compañía de origen suizo, con una gran trayectoria de más de 25 años, con tecnologías ",
        "patentadas y presencia a nivel mundial. Todas nuestras referencias tienen aprobación de la FDA, ",
        "otorgando el perfil de seguridad más alto para sus pacientes, resultados prolongados y naturales. ",
        "También contamos con un gran soporte científico, para el caso de Sculptra con más de 450 estudios ",
        "clínicos y para Restylane más de 150", "",
        "En esta oportunidad queremos agradecerle por confiar en nosotros permitiéndonos presentarle la ",
        "siguiente propuesta comercial:", ""
    ]

    for line in encabezado:
        if y < margin + 250:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - margin
        c.drawString(margin, y, line)
        y -= line_height

    # Tabla de productos
    productos_tabla = []
    productos_info = [
        ('sculptra', 'Sculptra', data['Sculptra Unidades'], data['Sculptra Descuento']),
        ('restylane', 'Restylane', data['Restylane Unidades'], data['Restylane Descuento']),
        ('skinboosters', 'Skinboosters', data['Skinboosters Unidades'], data['Skinboosters Descuento'])
    ]

    cross_selling_aplica = data['Cross-selling'] == 'Sí'

    for key, nombre, unidades, dcto in productos_info:
        if unidades > 0:
            precio_lista = PRECIOS_LISTA[key]
            dcto_vol = dcto / 100
            precio_desc_vol = precio_lista * (1 - dcto_vol)
            precio_cross = precio_lista * (1 - DESCUENTO_CROSS_SELLING) if cross_selling_aplica else precio_desc_vol
            precio_final_base = min(precio_desc_vol, precio_cross) if cross_selling_aplica else precio_desc_vol
            precio_con_iva = precio_final_base * (1 + IVA)

            if cross_selling_aplica:
                precio_pronto_base = precio_lista * (1 - DESCUENTO_PRONTO_PAGO - DESCUENTO_CROSS_SELLING)
            else:
                precio_pronto_base = precio_lista * (1 - DESCUENTO_PRONTO_PAGO - dcto_vol)

            precio_pronto_pago = precio_pronto_base * (1 + IVA)

            valor_normal = precio_con_iva * unidades
            valor_pronto_pago = precio_pronto_pago * unidades

            productos_tabla.append([
                nombre,
                str(unidades),
                f"${precio_lista:,.0f}",
                f"{dcto}%",
                f"{3 if cross_selling_aplica else 0}%",
                f"${precio_con_iva:,.0f}",
                f"${precio_pronto_pago:,.0f}",
                f"${valor_normal:,.0f}",
                f"${valor_pronto_pago:,.0f}"
            ])

    # Dibujar tabla si hay productos
    if productos_tabla:
        y -= 20
        headers = [
            "REF", "UND", "PRECIO\nLISTA", "% DCTO\nVOL", "% DCTO\nADIC",
            "PRECIO UN\nIVA", "PRECIO UN\n(IVA+PP)", "VALOR\nMES", "VALOR MES\n(P.PAGO)"
        ]
        col_widths = [50, 35, 60, 45, 45, 65, 70, 65, 75]
        row_height = 30
        header_height = 40
        tabla_height = header_height + len(productos_tabla) * row_height

        if y - tabla_height < margin + 150:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - margin - 20

        x_start = margin
        c.setFont("Helvetica-Bold", 8)
        c.setFillColorRGB(0.8, 0.8, 0.8)
        c.rect(x_start, y - header_height, sum(col_widths), header_height, fill=1)
        c.setFillColorRGB(0, 0, 0)
        x_pos = x_start
        for i, header in enumerate(headers):
            text_x = x_pos + col_widths[i] / 2
            for j, line in enumerate(header.split('\n')):
                c.drawString(text_x - c.stringWidth(line, "Helvetica-Bold", 8)/2, y - 15 - j*10, line)
            x_pos += col_widths[i]
        y -= header_height

        c.setFont("Helvetica", 7)
        for row in productos_tabla:
            c.setFillColorRGB(0.95, 0.95, 0.95)
            c.rect(x_start, y - row_height, sum(col_widths), row_height, fill=1)
            c.setFillColorRGB(0, 0, 0)
            x_pos = x_start
            for i, cell in enumerate(row):
                c.drawString(
                    x_pos + col_widths[i]/2 - c.stringWidth(cell, "Helvetica", 7)/2,
                    y - 18,
                    cell
                )
                x_pos += col_widths[i]
            y -= row_height

    y -= 30

    # Mensaje de cross-selling
    if cross_selling_aplica:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, "✓ Cross-selling aplicado: 3% de descuento adicional sobre precio de lista")
        y -= line_height * 2

    # Condiciones y términos
    condiciones = [
        "", "Condiciones:",
        f"  -   Vigencia de la propuesta: {data['Fecha inicio']} - {data['Fecha finalizacion']}",
        "  -   Esta propuesta no incluye ningún descuento comercial adicional",
        "  -   En caso de no cumplir con la propuesta al finalizar el año, no podrá acceder a este beneficio",
        " durante el siguiente año",
        "  -   Para obtener el precio propuesto, es importante que el promedio de las unidades acordadas ",
        "      sea solicitado durante el mes. En caso contrario, el precio facturado corresponderá al de la ",
        "      lista de precios",
        "  -   Esta negociación es personal e intransferible, por lo que no permite tener compras ",
        "      compartidas, sub-distribución o reventa de los productos; de ocurrir, se procederá a ",
        "      terminar la presente propuesta. ",
        "  -   Galderma, en cualquier tiempo, podrá modificar, eliminar o revertir la presente propuesta.",
        "", "Términos:", "",
        "  -   Precio: Se mantendrán los precios hasta la fecha de finalización de este acuerdo siempre y",
        "      cuando el cliente cumpla con las compras descritas en el mismo",
        "  -   Plazo de pago: 60 días plazo con valor neto y 45 días para el plazo de pago de las facturas con ",
        "      el 5% de descuento (valor que se toma sin incluir)",
        "  -   Cancelación del acuerdo: Galderma puede dar finalizado este acuerdo y sus beneficios",
        "      cuando el cliente incumpla 3 meses al mismo en el año y perderá el beneficio del mismo para el ",
        "      siguiente periodo (año)",
        "  -   Cartera: para poder realizar los pedidos y cumplir con el acuerdo el cliente debe estar al dia en",
        "      cartera, de lo contrario no se despacharan los pedidos."
    ]

    c.setFont("Helvetica", 11)
    for line in condiciones:
        if y < margin + 120:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - margin
        c.drawString(margin, y, line)
        y -= line_height

    # Área de firmas
    espacio_necesario_firmas = 150
    if y < margin + espacio_necesario_firmas:
        c.showPage()
        y = height - margin

    y -= 60
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    c.line(margin, y, width - margin, y)
    y -= 30

    # Firmas
    y -= 70
    ancho_disponible = width - 2 * margin
    x_firma_izq = margin + 20
    x_firma_der = margin + ancho_disponible / 2 + 20
    line_y = y
    label_y = line_y - 18
    name_y = label_y - 15
    org_y = name_y - 15

    c.setFont("Helvetica", 11)
    c.drawString(x_firma_izq, line_y, "_________________________")
    c.drawString(x_firma_izq, label_y, "Ejecutiva Comercial:")
    c.drawString(x_firma_izq, name_y, f"{data['Representante']}")
    c.drawString(x_firma_izq, org_y, "Galderma")

    c.drawString(x_firma_der, line_y, "_________________________")
    c.drawString(x_firma_der, label_y, "Cliente:")
    c.drawString(x_firma_der, name_y, f"Dr(a). {data['Cliente']}")
    c.drawString(x_firma_der, org_y, "Firma y Sello")

    c.save()
    buffer.seek(0)
    return buffer

# =================== RUTAS ===================

@app.route('/')
def formulario():
    """Página principal: formulario"""
    return render_template('form.html')

@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    """Generar y descargar PDF automáticamente"""
    try:
        fecha_actual = datetime.today().strftime('%d/%m/%Y')
        
        # Obtener datos del formulario
        representante = request.form.get('representante', '')
        cliente = request.form.get('cliente', '')
        fecha_inicio = request.form.get('fecha_inicio', '')
        fecha_finalizacion = request.form.get('fecha_finalizacion', '')
        
        # Calcular descuentos
        sculptra_unidades = int(request.form.get('sculptra_unidades', 0) or 0)
        restylane_unidades = int(request.form.get('restylane_unidades', 0) or 0)
        skinboosters_unidades = int(request.form.get('skinboosters_unidades', 0) or 0)
        
        sculptra_descuento = calcular_descuento_porcentaje('sculptra', sculptra_unidades)
        restylane_descuento = calcular_descuento_porcentaje('restylane', restylane_unidades)
        skinboosters_descuento = calcular_descuento_porcentaje('skinboosters', skinboosters_unidades)
        
        cross_selling = 'Sí' if request.form.get('cross_selling') else 'No'

        # Validar que hay al menos un producto
        if sculptra_unidades == 0 and restylane_unidades == 0 and skinboosters_unidades == 0:
            return jsonify({"error": "Debe ingresar al menos un producto con unidades mayor a 0"}), 400

        data = {
            'Representante': representante,
            'Cliente': cliente,
            'Sculptra Unidades': sculptra_unidades,
            'Sculptra Descuento': sculptra_descuento,
            'Skinboosters Unidades': skinboosters_unidades,
            'Skinboosters Descuento': skinboosters_descuento,
            'Restylane Unidades': restylane_unidades,
            'Restylane Descuento': restylane_descuento,
            'Cross-selling': cross_selling,
            'Fecha inicio': fecha_inicio,
            'Fecha finalizacion': fecha_finalizacion,
            'Fecha actual': fecha_actual
        }

        # Generar PDF en memoria
        pdf_buffer = generar_carta_pdf(data)
        
        # Nombre del archivo
        filename = f"Propuesta_Galderma_{cliente}_{datetime.today().strftime('%Y%m%d')}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({"error": f"Error generando PDF: {str(e)}"}), 500

@app.route('/health')
def health():
    """Endpoint de salud para Render"""
    return jsonify({"status": "OK", "message": "App funcionando correctamente"})

if __name__ == '__main__':
    # Para desarrollo local
    app.run(debug=True)
else:
    # Para producción en Render
    pass

# Para que Gunicorn funcione
application = app