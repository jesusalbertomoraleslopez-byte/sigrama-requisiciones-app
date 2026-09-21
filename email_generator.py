"""
=============================================================================
SISTEMA DE REQUISICIONES DE COMPRA - INDUSTRIA SIGRAMA S.A. DE C.V.
Generador Dinámico de Correos Electrónicos (.eml) Estándar RFC 822
=============================================================================
- Asunto normativo estricto: 'REQ XXXXX - Descripción Breve - Fecha - Área'
- Logotipo oficial de SIGRAMA integrado inline (CID) idéntico a Remisiones
- Texto respetuoso y amable solicitando la autorización a Lic. Lorena Hernández
- Codificación UTF-8 segura en Base64 para prevenir corrupción de caracteres en Outlook
- Adjuntos PDF nativos (Requisición original + Cotizaciones)
"""

import os
import io
import re
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import List, Dict, Any, Optional

from PIL import Image

from config import (
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    LOGO_SIGRAMA_PATH,
    DESTINATARIO_PRINCIPAL_DEFAULT,
    DESTINATARIOS_CC_DEFAULT,
    DIRECTORES_DEFAULT,
    get_req_directory
)


def get_user_email(user_name: Optional[str]) -> str:
    """Obtiene el correo institucional @sigrama.com.mx correspondiente a la persona que descarga o solicita."""
    if not user_name:
        return "jesus.morales@sigrama.com.mx"

    u_str = str(user_name).strip()
    match = re.search(r'[\w\.-]+@[\w\.-]+', u_str)
    if match:
        return match.group(0)

    u_lower = u_str.lower()
    for person in DIRECTORES_DEFAULT:
        p_name = person["nombre"].lower()
        parts = [p for p in p_name.split() if len(p) > 3]
        if any(part in u_lower for part in parts):
            return person["correo"]

    if "morales" in u_lower or "jesus" in u_lower or "admin" in u_lower:
        return "jesus.morales@sigrama.com.mx"
    elif "bryan" in u_lower or "mancinas" in u_lower or "flores" in u_lower:
        return "bryan.mancinas@sigrama.com.mx"
    elif "cruz" in u_lower or "carreon" in u_lower:
        return "cruz.carreon@sigrama.com.mx"
    elif "fernandez" in u_lower or "jose" in u_lower:
        return "jose.fernandez@sigrama.com.mx"
    elif "quintana" in u_lower or "luis" in u_lower:
        return "luis.quintana@sigrama.com.mx"

    return "jesus.morales@sigrama.com.mx"


def format_from_header(remitente: Optional[str]) -> str:
    """Construye el encabezado 'From: Nombre <correo@sigrama.com.mx>' con la cuenta corporativa real."""
    rem_target = str(remitente or "").strip()
    if not rem_target:
        rem_target = "Jesus Alberto Morales Lopez"

    if "<" in rem_target and ">" in rem_target:
        return rem_target

    clean_name = rem_target.split("(")[0].strip()
    email = get_user_email(rem_target)
    return f"{clean_name} <{email}>"


def format_fecha_limite_esp(dias: int = 3) -> tuple:
    """Calcula la fecha límite estimada y la formatea en español formal para Outlook."""
    dias_semana_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses_es = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    target_dt = datetime.datetime.now() + datetime.timedelta(days=int(dias))
    dia_nombre = dias_semana_es[target_dt.weekday()]
    mes_nombre = meses_es[target_dt.month - 1]
    fecha_str = f"{dia_nombre}, {target_dt.day} de {mes_nombre} de {target_dt.year}"
    return fecha_str, target_dt


def build_requisition_eml(
    req_data: Dict[str, Any],
    cotizaciones_data: List[Dict[str, Any]],
    pdf_requisicion_bytes: Optional[bytes] = None,
    pdf_requisicion_name: str = "requisicion_original.pdf",
    cotizaciones_attachments: Optional[List[Dict[str, Any]]] = None,
    destinatario_to: Optional[Dict[str, str]] = None,
    destinatarios_cc: Optional[List[Dict[str, str]]] = None,
    remitente_from: Optional[str] = None,
    planta: str = "Planta Metales",
    dias_autorizacion: int = 3,
    plazo_po: str = "1 semana posterior a autorización"
) -> bytes:
    """
    Construye y compila un archivo .eml compatible con Outlook con el logotipo
    oficial de SIGRAMA embebido inline, solicitud amable de autorización,
    asunto con SOL-XXXXX primero y marca de seguimiento para Outlook.
    """
    # Usar multipart/related como raíz para soporte nativo de imágenes inline (CID)
    msg = MIMEMultipart("related")

    # 1. Asunto Normativo Estricto: 'SOL-XXXXX - REQ-XXXXX - Descripción - Fecha - Área'
    req_id = req_data.get("id_requisicion", "REQ-00000")
    sol_id = str(req_data.get("folio_solicitud", "") or "").strip()
    descripcion = req_data.get("descripcion_breve", "Suministro de Materiales")
    fecha = req_data.get("fecha_requisicion", datetime.date.today().strftime("%Y-%m-%d"))
    area = req_data.get("area_impacto", "Materiales")

    sol_part = f"{sol_id} - " if sol_id else ""
    subject_clean = f"{sol_part}{req_id} - {descripcion} - {fecha} - {area}"
    msg["Subject"] = subject_clean

    # 2. Destinatarios y Encabezados de Correo
    to_info = destinatario_to or DESTINATARIO_PRINCIPAL_DEFAULT
    cc_list = destinatarios_cc if destinatarios_cc is not None else DESTINATARIOS_CC_DEFAULT

    msg["To"] = f"{to_info['nombre']} <{to_info['correo']}>"
    
    cc_strings = []
    for c in cc_list:
        if c.get("nombre") and c.get("nombre") != c.get("correo"):
            cc_strings.append(f"{c['nombre']} <{c['correo']}>")
        else:
            cc_strings.append(c["correo"])
    msg["Cc"] = "; ".join(cc_strings)

    solicitante = req_data.get("solicitante", "Jesus Alberto Morales Lopez")
    msg["From"] = format_from_header(remitente_from or solicitante)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="sigrama.com.mx")
    msg["X-Priority"] = "1" if req_data.get("prioridad") == "Urgente" else "3"
    msg["X-Unsent"] = "1"  # Permite que Outlook lo abra directamente como borrador listo

    # Encabezados de Seguimiento para Microsoft Outlook
    fecha_limite_str, target_dt = format_fecha_limite_esp(dias_autorizacion)
    msg["X-Message-Flag"] = "Seguimiento"
    msg["Reply-By"] = formatdate(target_dt.timestamp(), localtime=True)

    # 3. Contenedor multipart/alternative para texto y HTML
    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)

    # 4. Datos del Cuerpo
    justificacion = req_data.get("justificacion", "Sin observaciones adicionales.")
    prioridad = req_data.get("prioridad", "Media")
    monto_est = float(req_data.get("monto_estimado", 0.0))
    moneda = req_data.get("moneda", "MXN")

    cc_names = ", ".join([c["nombre"] for c in cc_list])

    # Texto Plano de Respaldo
    plain_text = f"""SOLICITUD DE VISTO BUENO Y AUTORIZACIÓN DE COMPRA
INDUSTRIA SIGRAMA S.A. DE C.V.
----------------------------------------------------------------------
Para: {to_info['nombre']} <{to_info['correo']}>
Con copia: {cc_names}

Estimada {to_info['nombre']},

Buen día. Esperando que se encuentre muy bien, por medio de la presente nos dirigimos a usted de la manera más atenta y cordial para solicitar su amable visto bueno y autorización para la Requisición {req_id}.

Dicha requisición corresponde a: {descripcion} para el área de {area}, con un monto sugerido de ${monto_est:,.2f} {moneda}.

DATOS GENERALES DE LA REQUISICIÓN:
- Folio: {req_id}
- Fecha: {fecha}
- Solicitante: {solicitante}
- Área de Impacto: {area}
- Prioridad: {prioridad}
- Descripción: {descripcion}
- Justificación / Observaciones: {justificacion}
- Monto Estimado Sugerido: ${monto_est:,.2f} {moneda}

RESUMEN DE COTIZACIONES DE PROVEEDORES:
"""
    for idx, cot in enumerate(cotizaciones_data, 1):
        sel_mark = "[RECOMENDADA] " if cot.get("seleccionada") == "Sí" else ""
        monto_cot = float(cot.get("monto", 0.0))
        mon_cot = cot.get("moneda", "MXN")
        prov = cot.get("proveedor", "N/A")
        t_ent = cot.get("tiempo_entrega_dias", 0)
        plain_text += f"\n{idx}. {sel_mark}{prov} | ${monto_cot:,.2f} {mon_cot} | Entrega: {t_ent} días"

    plain_text += f"""

PLAZOS DE SEGUIMIENTO Y COMPROMISO:
- Visto Bueno / Autorización: {dias_autorizacion} días hábiles (Fecha límite estimada: {fecha_limite_str})
- Emisión estimada de Orden de Compra (PO): {plazo_po}

Ing. Lorena, le agradeceríamos enormemente si nos puede apoyar confirmando por este medio su amable visto bueno y autorización para la Requisición {req_id} dentro de un plazo estimado de {dias_autorizacion} días hábiles (a más tardar el {fecha_limite_str}), con el fin de poder continuar con el proceso y formalizar la correspondiente Orden de Compra (PO) en un plazo de {plazo_po}.

Adjunto encontrará el expediente original en PDF y las cotizaciones de los proveedores para su debida revisión.

Agradecemos de antemano su valioso apoyo.

Atentamente,
{solicitante}
Industria Sigrama S.A. de C.V.
"""
    part_text = MIMEText(plain_text, "plain", "utf-8")
    part_text.replace_header("Content-Transfer-Encoding", "base64")
    msg_alt.attach(part_text)

    # 5. Filas HTML de Cotizaciones
    rows_html = ""
    for idx, cot in enumerate(cotizaciones_data, 1):
        es_sel = cot.get("seleccionada") == "Sí"
        bg_row = "#F0FDF4" if es_sel else "#FFFFFF"
        badge_sel = """<span style="background-color:#10B981; color:#ffffff; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">RECOMENDADA</span>""" if es_sel else """<span style="color:#64748B; font-size:11px;">Alternativa</span>"""
        m_val = float(cot.get("monto", 0.0))
        m_mon = cot.get("moneda", "MXN")
        t_dias = cot.get("tiempo_entrega_dias", 0)
        rows_html += f"""
        <tr style="background-color:{bg_row}; border-bottom:1px solid #E2E8F0;">
            <td style="padding:10px 12px; font-weight:600; color:#1E293B;">{idx}. {cot.get('proveedor', 'N/A')}</td>
            <td style="padding:10px 12px; font-weight:bold; color:#0F172A; text-align:right;">${m_val:,.2f} {m_mon}</td>
            <td style="padding:10px 12px; text-align:center; color:#475569;">{t_dias} días</td>
            <td style="padding:10px 12px; text-align:center;">{badge_sel}</td>
        </tr>
        """

    if not rows_html:
        rows_html = """
        <tr>
            <td colspan="4" style="padding:14px; text-align:center; color:#94A3B8; font-style:italic;">
                En proceso de recepción de cotizaciones comerciales formales.
            </td>
        </tr>
        """

    cc_html_badges = " ".join([f"""<span style="background-color:#F1F5F9; color:#475569; padding:3px 7px; border-radius:4px; font-size:11px; margin-right:4px; border:1px solid #E2E8F0;">{c['nombre']}</span>""" for c in cc_list])

    sol_badge_header = f"""<div style="font-size:12px; color:#EC2024; margin-top:3px; font-weight:800; font-family:'Montserrat', sans-serif;">{sol_id}</div>""" if sol_id else ""

    # 6. Cuerpo HTML Profesional con Logotipo SIGRAMA exacto como en Remisiones (width="160")
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{subject_clean}</title>
</head>
<body style="font-family:'Segoe UI', Arial, sans-serif; background-color:#F8FAFC; margin:0; padding:20px; color:#1E293B; line-height:1.6;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width:750px; margin:0 auto; background-color:#FFFFFF; border-radius:8px; overflow:hidden; box-shadow:0 3px 12px rgba(0,0,0,0.06); border:1px solid #E2E8F0;">
        
        <!-- ENCABEZADO CON LOGOTIPO SIGRAMA (RÉPLICA EXACTA DE APP DE REMISIONES) -->
        <tr>
            <td style="padding:20px 30px 15px 30px; border-bottom:4px solid #EC2024; background-color:#FFFFFF;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td valign="middle">
                            <img src="cid:logo_sigrama_cid" width="160" alt="Industria Sigrama" style="display:block; border:0; width:160px; max-width:160px; height:auto;">
                        </td>
                        <td valign="middle" align="right">
                            <div style="font-size:11px; color:#64748B; font-weight:700; text-transform:uppercase; letter-spacing:0.5px;">Control de Requisiciones</div>
                            <div style="display:inline-block; background-color:#0F172A; color:#FFFFFF; padding:5px 12px; border-radius:6px; font-weight:bold; font-size:14px; margin-top:4px; letter-spacing:0.5px;">
                                {req_id}
                            </div>
                            {sol_badge_header}
                            <div style="font-size:11px; color:#64748B; margin-top:3px; font-weight:600;">
                                {planta}
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>

        <!-- DESTINATARIOS Y COPIAS -->
        <tr>
            <td style="background-color:#F8FAFC; padding:12px 30px; border-bottom:1px solid #E2E8F0; font-size:12px; color:#475569;">
                <div><strong>Para:</strong> <span style="color:#0F172A; font-weight:bold;">{to_info['nombre']}</span> &lt;{to_info['correo']}&gt;</div>
                <div style="margin-top:6px;"><strong>Con copia:</strong> {cc_html_badges}</div>
            </td>
        </tr>

        <!-- CUERPO PRINCIPAL -->
        <tr>
            <td style="padding:28px 30px;">
                
                <!-- SALUDO AMABLE Y ATENTO -->
                <p style="font-size:15px; color:#1E293B; margin-top:0; font-weight:600;">
                    Estimada {to_info['nombre']},
                </p>
                <p style="font-size:14px; color:#334155; line-height:1.6;">
                    Buen día. Esperando que se encuentre muy bien al recibir el presente, nos dirigimos a usted de la manera más atenta y cordial para solicitar su <strong>amable visto bueno y autorización</strong> para la <strong>Requisición {req_id}</strong>.
                </p>
                <p style="font-size:14px; color:#334155; line-height:1.6;">
                    Dicha adquisición corresponde a: <strong>{descripcion}</strong> para el área de <strong>{area}</strong>, con un monto sugerido de <strong>${monto_est:,.2f} {moneda}</strong>.
                </p>

                <!-- TABLA DE DETALLES TÉCNICOS Y OPERATIVOS -->
                <div style="margin:20px 0; border:1px solid #E2E8F0; border-radius:6px; overflow:hidden;">
                    <div style="background-color:#F1F5F9; padding:10px 14px; font-size:12px; font-weight:800; color:#334155; text-transform:uppercase; letter-spacing:0.5px; border-bottom:1px solid #E2E8F0;">
                        📋 Resumen de la Requisición
                    </div>
                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#FFFFFF;">
                        <tr>
                            <td style="padding:9px 14px; font-size:13px; color:#64748B; width:35%; border-bottom:1px solid #F1F5F9; font-weight:600;">Consecutivo Interno:</td>
                            <td style="padding:9px 14px; font-size:13px; color:#0F172A; border-bottom:1px solid #F1F5F9; font-weight:800;">{sol_id if sol_id else '-'}</td>
                        </tr>
                        <tr>
                            <td style="padding:9px 14px; font-size:13px; color:#64748B; width:35%; border-bottom:1px solid #F1F5F9; font-weight:600;">Área de Impacto:</td>
                            <td style="padding:9px 14px; font-size:13px; color:#0F172A; border-bottom:1px solid #F1F5F9; font-weight:700;">{area}</td>
                        </tr>
                        <tr>
                            <td style="padding:9px 14px; font-size:13px; color:#64748B; border-bottom:1px solid #F1F5F9; font-weight:600;">Solicitado por:</td>
                            <td style="padding:9px 14px; font-size:13px; color:#0F172A; border-bottom:1px solid #F1F5F9;">{solicitante}</td>
                        </tr>
                        <tr>
                            <td style="padding:9px 14px; font-size:13px; color:#64748B; border-bottom:1px solid #F1F5F9; font-weight:600;">Fecha de Requisición:</td>
                            <td style="padding:9px 14px; font-size:13px; color:#0F172A; border-bottom:1px solid #F1F5F9;">{fecha}</td>
                        </tr>
                        <tr>
                            <td style="padding:9px 14px; font-size:13px; color:#64748B; border-bottom:1px solid #F1F5F9; font-weight:600;">Nivel de Prioridad:</td>
                            <td style="padding:9px 14px; font-size:13px; border-bottom:1px solid #F1F5F9;">
                                <span style="color:{'#DC2626' if prioridad == 'Urgente' else '#0F172A'}; font-weight:bold;">
                                    {prioridad}
                                </span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:9px 14px; font-size:13px; color:#64748B; border-bottom:1px solid #F1F5F9; font-weight:600;">Descripción Breve:</td>
                            <td style="padding:9px 14px; font-size:13px; color:#0F172A; border-bottom:1px solid #F1F5F9; font-weight:600;">{descripcion}</td>
                        </tr>
                        <tr>
                            <td style="padding:9px 14px; font-size:13px; color:#64748B; font-weight:600;">Observaciones / Justificación:</td>
                            <td style="padding:9px 14px; font-size:13px; color:#334155; line-height:1.5;">{justificacion}</td>
                        </tr>
                    </table>
                </div>

                <!-- RESUMEN DE COTIZACIONES -->
                <div style="font-size:13px; font-weight:800; color:#0F172A; margin:22px 0 8px 0; text-transform:uppercase; letter-spacing:0.5px;">
                    📊 Comparativa de Cotizaciones de Proveedores
                </div>
                <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #CBD5E1; border-radius:6px; overflow:hidden; font-size:13px; margin-bottom:20px;">
                    <thead style="background-color:#E2E8F0; color:#334155;">
                        <tr>
                            <th style="padding:9px 12px; text-align:left;">Proveedor</th>
                            <th style="padding:9px 12px; text-align:right;">Monto Cotizado</th>
                            <th style="padding:9px 12px; text-align:center;">Tiempo Entrega</th>
                            <th style="padding:9px 12px; text-align:center;">Dictamen</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>

                <!-- CONTROL Y PLAZOS DE SEGUIMIENTO -->
                <div style="background-color:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:6px; padding:14px 18px; margin:20px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="vertical-align:middle; width:28px;">
                                <span style="font-size:20px;">🚩</span>
                            </td>
                            <td style="vertical-align:middle;">
                                <div style="font-size:12.5px; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px;">
                                    Control y Plazos de Seguimiento
                                </div>
                                <div style="font-size:13px; color:#78350F; margin-top:5px; line-height:1.5;">
                                    <span style="display:inline-block; margin-right:18px;">
                                        <strong>• Visto Bueno / Autorización:</strong> <strong style="color:#B45309; background-color:#FEF3C7; padding:2px 7px; border-radius:4px; border:1px solid #FCD34D;">{dias_autorizacion} días hábiles</strong> ({fecha_limite_str})
                                    </span>
                                    <span style="display:inline-block;">
                                        <strong>• Emisión estimada de PO:</strong> <strong style="color:#B45309; background-color:#FEF3C7; padding:2px 7px; border-radius:4px; border:1px solid #FCD34D;">{plazo_po}</strong>
                                    </span>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- CAJA DESTACADA DE SOLICITUD AMABLE DE VISTO BUENO -->
                <div style="background-color:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #10B981; border-radius:6px; padding:18px; margin:24px 0;">
                    <div style="font-weight:bold; font-size:14.5px; color:#166534;">
                        ✓ Solicitud de Visto Bueno y Autorización
                    </div>
                    <div style="font-size:13.5px; color:#15803D; margin-top:6px; line-height:1.5;">
                        Ing. Lorena, le agradeceríamos enormemente si nos puede apoyar confirmando por este medio su <strong>amable visto bueno y autorización</strong> para la <strong>Requisición {req_id}</strong> dentro del plazo estimado de <strong>{dias_autorizacion} días hábiles</strong> (a más tardar el <strong>{fecha_limite_str}</strong>), con el fin de poder continuar con el proceso y formalizar la correspondiente Orden de Compra (PO) en un plazo de <strong>{plazo_po}</strong>.
                    </div>
                </div>

                <p style="font-size:14px; color:#334155; line-height:1.6;">
                    Adjunto al presente correo encontrará los expedientes correspondientes en formato PDF (la requisición original y las cotizaciones) para su debida revisión y resguardo documental.
                </p>
                <p style="font-size:14px; color:#334155; line-height:1.6;">
                    Agradecemos de antemano su valioso apoyo y quedamos a sus respetables órdenes para cualquier duda o comentario.
                </p>

                <!-- FIRMA ATENTA -->
                <p style="font-size:14px; color:#1E293B; margin-top:22px; line-height:1.5;">
                    Atentamente,<br>
                    <strong style="color:#0F172A;">{solicitante}</strong><br>
                    <span style="color:#64748B; font-size:12.5px;">Industria Sigrama S.A. de C.V.</span>
                </p>
            </td>
        </tr>

        <!-- PIE DE CORREO INSTITUCIONAL -->
        <tr>
            <td style="background-color:#F8FAFC; padding:16px 30px; border-top:1px solid #E2E8F0; text-align:center; font-size:11px; color:#64748B;">
                INDUSTRIA SIGRAMA S.A. DE C.V. &bull; Módulo de Control de Requisiciones y Compras &bull; México<br>
                Este correo y sus archivos adjuntos son para uso exclusivo de autorización y contienen información confidencial.
            </td>
        </tr>
    </table>
</body>
</html>
"""
    # Usar Base64 explícito para evitar problemas de Quoted-Printable en Outlook
    part_html = MIMEText(html_body, "html", "utf-8")
    part_html.replace_header("Content-Transfer-Encoding", "base64")
    msg_alt.attach(part_html)

    # 7. Incrustar Logotipo SIGRAMA como Imagen Inline (CID)
    logo_path = LOGO_SIGRAMA_PATH
    if not logo_path.exists():
        # Buscar en ubicaciones posibles
        alt_logo = Path(r"C:\Users\albertol\.gemini\antigravity\scratch\remisiones-de-materiales\logo_sigrama.png")
        if alt_logo.exists():
            logo_path = alt_logo

    if logo_path.exists():
        try:
            with open(logo_path, "rb") as lf:
                logo_bytes = lf.read()
            img_part = MIMEImage(logo_bytes, _subtype="png")
            img_part.add_header("Content-ID", "<logo_sigrama_cid>")
            img_part.add_header("Content-Disposition", "inline", filename="logo_sigrama.png")
            msg.attach(img_part)
        except Exception as e:
            print(f"Aviso: No se pudo incrustar logotipo inline: {e}")

    # 8. Incrustar Adjunto de la Requisición Original (PDF)
    if pdf_requisicion_bytes:
        part_pdf = MIMEBase("application", "pdf")
        part_pdf.set_payload(pdf_requisicion_bytes)
        encoders.encode_base64(part_pdf)
        part_pdf.add_header("Content-Disposition", f'attachment; filename="{pdf_requisicion_name}"')
        msg.attach(part_pdf)

    # 9. Incrustar Adjuntos de las Cotizaciones (PDFs)
    if cotizaciones_attachments:
        for cot_att in cotizaciones_attachments:
            att_name = cot_att.get("filename", "cotizacion.pdf")
            att_bytes = cot_att.get("content")
            if att_bytes:
                part_cot = MIMEBase("application", "pdf")
                part_cot.set_payload(att_bytes)
                encoders.encode_base64(part_cot)
                part_cot.add_header("Content-Disposition", f'attachment; filename="{att_name}"')
                msg.attach(part_cot)

    return msg.as_bytes()


def build_consolidated_requisitions_eml(
    reqs_list: List[Dict[str, Any]],
    destinatario_to: Optional[Any] = None,
    destinatarios_cc: Optional[Any] = None,
    solicitante_remitente: Optional[str] = None,
    remitente_from: Optional[str] = None,
    planta: str = "Planta Metales",
    dias_autorizacion: int = 3,
    plazo_po: str = "1 semana posterior a autorización"
) -> bytes:
    """
    Construye y compila un archivo .eml consolidado para múltiples requisiciones seleccionadas
    con casillas de verificación, adjuntando los PDFs originales y cotizaciones correspondientes.
    Incluye SOL-XXXXX primero en el asunto y plazos personalizados de seguimiento.
    """
    if not reqs_list:
        return b""

    msg = MIMEMultipart("related")

    # 1. Asunto del Correo con SOL-XXXXX al inicio
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    folios = [str(r.get("id_requisicion", "")).strip() for r in reqs_list if r.get("id_requisicion")]
    sol_list = [str(r.get("folio_solicitud", "")).strip() for r in reqs_list if r.get("folio_solicitud")]
    
    if len(reqs_list) == 1:
        r0 = reqs_list[0]
        f0 = r0.get("id_requisicion", "REQ")
        s0 = str(r0.get("folio_solicitud", "") or "").strip()
        d0 = r0.get("descripcion_breve", "Requisición de Compra")
        fe0 = r0.get("fecha_requisicion", today_str)
        a0 = r0.get("area_impacto", "Materiales")
        s0_str = f"{s0} - " if s0 else ""
        subject = f"{s0_str}{f0} - {d0} - {fe0} - {a0}"
    else:
        sol_preview = ", ".join(sol_list[:4]) + (f" (+{len(sol_list)-4} más)" if len(sol_list) > 4 else "")
        folios_preview = ", ".join(folios[:4]) + (f" (+{len(folios)-4} más)" if len(folios) > 4 else "")
        if sol_preview:
            subject = f"{sol_preview} - REQ {folios_preview} - Solicitud de Autorización ({len(reqs_list)} Requisiciones) - {today_str} - Industria SIGRAMA"
        else:
            subject = f"REQ {folios_preview} - Solicitud de Autorización ({len(reqs_list)} Requisiciones) - {today_str} - Industria SIGRAMA"

    msg["Subject"] = subject

    # 2. Destinatarios To y Cc
    if isinstance(destinatario_to, str) and destinatario_to.strip():
        to_header = destinatario_to.strip()
    elif isinstance(destinatario_to, dict):
        to_header = f"{destinatario_to.get('nombre', '')} <{destinatario_to.get('correo', '')}>".strip()
    else:
        to_header = f"{DESTINATARIO_PRINCIPAL_DEFAULT['nombre']} <{DESTINATARIO_PRINCIPAL_DEFAULT['correo']}>"

    msg["To"] = to_header

    if isinstance(destinatarios_cc, str) and destinatarios_cc.strip():
        cc_header = destinatarios_cc.strip()
    elif isinstance(destinatarios_cc, list):
        cc_parts = []
        for c in destinatarios_cc:
            if isinstance(c, dict):
                if c.get("nombre") and c.get("nombre") != c.get("correo"):
                    cc_parts.append(f"{c['nombre']} <{c['correo']}>")
                else:
                    cc_parts.append(c.get("correo", ""))
            elif isinstance(c, str):
                cc_parts.append(c)
        cc_header = "; ".join(cc_parts)
    else:
        cc_header = "; ".join([f"{c['nombre']} <{c['correo']}>" for c in DESTINATARIOS_CC_DEFAULT])

    msg["Cc"] = cc_header
    msg["From"] = format_from_header(remitente_from or solicitante_remitente)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="sigrama.com.mx")
    msg["X-Unsent"] = "1"

    # Encabezados de Seguimiento para Microsoft Outlook
    fecha_limite_str, target_dt = format_fecha_limite_esp(dias_autorizacion)
    msg["X-Message-Flag"] = "Seguimiento"
    msg["Reply-By"] = formatdate(target_dt.timestamp(), localtime=True)

    # 3. Contenedor multipart/alternative
    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)

    # 4. Construcción de Tabla Consolidada
    rows_html = []
    total_monto = 0.0
    for idx, r in enumerate(reqs_list, 1):
        monto_val = float(r.get("monto_estimado", 0.0) or 0.0)
        total_monto += monto_val
        cot_num = int(r.get("num_cotizaciones", 0) or 0)
        solic = str(r.get("solicitante", "")).split("(")[0].strip()
        sol_id = r.get("folio_solicitud", "")
        sol_badge = f"<span style='font-size:11px; font-weight:800; color:#0F172A; background-color:#F1F5F9; border:1px solid #CBD5E1; padding:2px 6px; border-radius:4px;'>{sol_id}</span>" if sol_id else "-"
        bg_row = "#FFFFFF" if idx % 2 != 0 else "#F8FAFC"
        rows_html.append(f"""
        <tr style="background-color:{bg_row}; border-bottom:1px solid #E2E8F0;">
            <td style="padding:10px 8px; text-align:center; font-weight:700; color:#64748B;">{idx}</td>
            <td style="padding:10px 10px; text-align:center;">{sol_badge}</td>
            <td style="padding:10px 10px; font-weight:800; color:#EC2024; font-family:'Montserrat', sans-serif;">{r.get('id_requisicion', '')}</td>
            <td style="padding:10px 10px; text-align:center; color:#334155;">{r.get('fecha_requisicion', '')}</td>
            <td style="padding:10px 10px; color:#0F172A; font-weight:600;">{r.get('area_impacto', '')}</td>
            <td style="padding:10px 10px; color:#475569;">{solic}</td>
            <td style="padding:10px 12px; color:#1E293B;">{r.get('descripcion_breve', '')}</td>
            <td style="padding:10px 8px; text-align:center; color:#0F172A; font-weight:700;">{cot_num}</td>
            <td style="padding:10px 12px; text-align:right; font-weight:700; color:#0F172A;">${monto_val:,.2f}</td>
        </tr>
        """)

    table_rows_str = "".join(rows_html)
    solicitante_firma = solicitante_remitente or "Jesús Alberto Morales López"

    # 5. Cuerpo HTML Consolidado
    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Solicitud de Autorización de Requisiciones - SIGRAMA</title>
</head>
<body style="margin:0; padding:0; background-color:#F1F5F9; font-family:'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; -webkit-font-smoothing:antialiased;">
    <table width="100%" cellpadding="0" cellspacing="0" style="max-width:850px; margin:25px auto; background-color:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; overflow:hidden; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
        <!-- ENCABEZADO INSTITUCIONAL SIGRAMA -->
        <tr>
            <td style="background-color:#FFFFFF; padding:22px 32px; border-bottom:4px solid #EC2024; text-align:left;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td align="left" style="vertical-align:middle;">
                            <img src="cid:logo_sigrama_cid" alt="SIGRAMA" width="160" style="display:block; border:0; outline:none; text-decoration:none;">
                        </td>
                        <td align="right" style="vertical-align:middle;">
                            <div style="font-size:18px; font-weight:900; color:#111111; letter-spacing:0.5px; font-family:'Montserrat', sans-serif;">
                                INDUSTRIA SIGRAMA S.A. DE C.V.
                            </div>
                            <div style="font-size:11px; color:#EC2024; font-weight:800; text-transform:uppercase; letter-spacing:1px; margin-top:2px;">
                                Control y Seguimiento de Requisiciones de Compra
                            </div>
                            <div style="font-size:11px; color:#64748B; margin-top:2px;">
                                Fecha de Emisión: <strong>{today_str}</strong> &bull; {planta}
                            </div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>

        <!-- CONTENIDO PRINCIPAL -->
        <tr>
            <td style="padding:28px 32px;">
                <p style="font-size:15px; color:#1E293B; line-height:1.6; margin-bottom:12px;">
                    <strong>Estimada Ing. Lorena Hernandez,</strong>
                </p>
                <p style="font-size:14px; color:#334155; line-height:1.6; margin-bottom:18px;">
                    Buen día. Esperando que se encuentre muy bien al recibir el presente, nos dirigimos a usted de la manera más atenta y cordial para solicitar su <strong>amable visto bueno y autorización</strong> para el paquete de <strong>{len(reqs_list)} requisición(es) de compra</strong> requeridas para la continuidad operativa y proyectos en planta, detalladas en el siguiente cuadro resumen:
                </p>

                <!-- TABLA CONSOLIDADA -->
                <div style="font-size:13px; font-weight:800; color:#0F172A; margin:20px 0 8px 0; text-transform:uppercase; letter-spacing:0.5px;">
                    📋 Resumen Ejecutivo de Requisiciones Seleccionadas
                </div>
                <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #CBD5E1; border-radius:6px; overflow:hidden; font-size:12px; margin-bottom:16px; border-collapse:collapse;">
                    <thead style="background-color:#0F172A; color:#FFFFFF;">
                        <tr>
                            <th style="padding:10px 8px; text-align:center;">#</th>
                            <th style="padding:10px 10px; text-align:center;">Interno</th>
                            <th style="padding:10px 10px; text-align:left;">Folio REQ</th>
                            <th style="padding:10px 10px; text-align:center;">Fecha</th>
                            <th style="padding:10px 10px; text-align:left;">Área</th>
                            <th style="padding:10px 10px; text-align:left;">Solicitante</th>
                            <th style="padding:10px 12px; text-align:left;">Descripción / Concepto</th>
                            <th style="padding:10px 8px; text-align:center;">Cot.</th>
                            <th style="padding:10px 12px; text-align:right;">Monto Est.</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_str}
                    </tbody>
                    <tfoot>
                        <tr style="background-color:#F8FAFC; font-weight:800;">
                            <td colspan="8" style="padding:11px 12px; text-align:right; border-top:2px solid #CBD5E1; font-size:12.5px; color:#0F172A;">
                                TOTAL ESTIMADO ACUMULADO:
                            </td>
                            <td style="padding:11px 12px; text-align:right; border-top:2px solid #CBD5E1; font-size:14px; color:#EC2024;">
                                ${total_monto:,.2f} MXN
                            </td>
                        </tr>
                    </tfoot>
                </table>

                <!-- CONTROL Y PLAZOS DE SEGUIMIENTO -->
                <div style="background-color:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; border-radius:6px; padding:14px 18px; margin:20px 0;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td style="vertical-align:middle; width:28px;">
                                <span style="font-size:20px;">🚩</span>
                            </td>
                            <td style="vertical-align:middle;">
                                <div style="font-size:12.5px; font-weight:800; color:#92400E; text-transform:uppercase; letter-spacing:0.5px;">
                                    Control y Plazos de Seguimiento
                                </div>
                                <div style="font-size:13px; color:#78350F; margin-top:5px; line-height:1.5;">
                                    <span style="display:inline-block; margin-right:18px;">
                                        <strong>• Visto Bueno / Autorización:</strong> <strong style="color:#B45309; background-color:#FEF3C7; padding:2px 7px; border-radius:4px; border:1px solid #FCD34D;">{dias_autorizacion} días hábiles</strong> ({fecha_limite_str})
                                    </span>
                                    <span style="display:inline-block;">
                                        <strong>• Emisión estimada de PO:</strong> <strong style="color:#B45309; background-color:#FEF3C7; padding:2px 7px; border-radius:4px; border:1px solid #FCD34D;">{plazo_po}</strong>
                                    </span>
                                </div>
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- CAJA DESTACADA DE SOLICITUD AMABLE DE VISTO BUENO -->
                <div style="background-color:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #10B981; border-radius:6px; padding:18px; margin:24px 0;">
                    <div style="font-weight:bold; font-size:14.5px; color:#166534;">
                        ✓ Solicitud de Visto Bueno y Autorización
                    </div>
                    <div style="font-size:13.5px; color:#15803D; margin-top:6px; line-height:1.5;">
                        Ing. Lorena, le agradeceríamos enormemente si nos puede apoyar confirmando por este medio su <strong>amable visto bueno y autorización</strong> para estas <strong>{len(reqs_list)} requisiciones</strong> dentro del plazo estimado de <strong>{dias_autorizacion} días hábiles</strong> (a más tardar el <strong>{fecha_limite_str}</strong>), con el fin de poder continuar con el proceso y formalizar la emisión de las correspondientes Órdenes de Compra (PO) en un plazo estimado de <strong>{plazo_po}</strong>.
                    </div>
                </div>

                <p style="font-size:13.5px; color:#334155; line-height:1.6;">
                    Adjunto a este correo encontrará los expedientes correspondientes en formato PDF (la requisición original de cada folio y las cotizaciones comerciales de los proveedores) para su debida revisión y resguardo documental.
                </p>
                <p style="font-size:13.5px; color:#334155; line-height:1.6;">
                    Agradecemos de antemano su valioso apoyo y quedamos a sus respetables órdenes para cualquier duda o comentario.
                </p>

                <!-- FIRMA ATENTA -->
                <p style="font-size:14px; color:#1E293B; margin-top:22px; line-height:1.5;">
                    Atentamente,<br>
                    <strong style="color:#0F172A;">{solicitante_firma}</strong><br>
                    <span style="color:#64748B; font-size:12.5px;">Industria Sigrama S.A. de C.V.</span>
                </p>
            </td>
        </tr>

        <!-- PIE DE CORREO INSTITUCIONAL -->
        <tr>
            <td style="background-color:#F8FAFC; padding:16px 30px; border-top:1px solid #E2E8F0; text-align:center; font-size:11px; color:#64748B;">
                INDUSTRIA SIGRAMA S.A. DE C.V. &bull; Módulo de Control de Requisiciones y Compras &bull; México<br>
                Este correo y sus archivos adjuntos son para uso exclusivo de autorización y contienen información confidencial.
            </td>
        </tr>
    </table>
</body>
</html>
"""

    part_html = MIMEText(html_body, "html", "utf-8")
    part_html.replace_header("Content-Transfer-Encoding", "base64")
    msg_alt.attach(part_html)

    # 6. Incrustar Logotipo SIGRAMA como Imagen Inline (CID)
    logo_path = LOGO_SIGRAMA_PATH
    if not logo_path.exists():
        alt_logo = Path(r"C:\Users\albertol\.gemini\antigravity\scratch\remisiones-de-materiales\logo_sigrama.png")
        if alt_logo.exists():
            logo_path = alt_logo

    if logo_path.exists():
        try:
            with open(logo_path, "rb") as lf:
                logo_bytes = lf.read()
            img_part = MIMEImage(logo_bytes, _subtype="png")
            img_part.add_header("Content-ID", "<logo_sigrama_cid>")
            img_part.add_header("Content-Disposition", "inline", filename="logo_sigrama.png")
            msg.attach(img_part)
        except Exception as e:
            print(f"Aviso: No se pudo incrustar logotipo inline: {e}")

    # 7. Adjuntar todos los archivos PDF de las requisiciones seleccionadas
    attached_names = set()
    for r in reqs_list:
        rid = r.get("id_requisicion", "")
        folder = get_req_directory(rid)
        if folder.exists():
            for pdf_path in folder.glob("*.pdf"):
                fname = pdf_path.name
                if fname not in attached_names:
                    attached_names.add(fname)
                    try:
                        with open(pdf_path, "rb") as pf:
                            p_bytes = pf.read()
                        part_pdf = MIMEBase("application", "pdf")
                        part_pdf.set_payload(p_bytes)
                        encoders.encode_base64(part_pdf)
                        part_pdf.add_header("Content-Disposition", f'attachment; filename="{fname}"')
                        msg.attach(part_pdf)
                    except Exception as e:
                        print(f"Error adjuntando {fname}: {e}")

    return msg.as_bytes()

