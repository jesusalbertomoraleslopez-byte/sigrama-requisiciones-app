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
    DESTINATARIOS_CC_DEFAULT
)


def build_requisition_eml(
    req_data: Dict[str, Any],
    cotizaciones_data: List[Dict[str, Any]],
    pdf_requisicion_bytes: Optional[bytes] = None,
    pdf_requisicion_name: str = "requisicion_original.pdf",
    cotizaciones_attachments: Optional[List[Dict[str, Any]]] = None,
    destinatario_to: Optional[Dict[str, str]] = None,
    destinatarios_cc: Optional[List[Dict[str, str]]] = None
) -> bytes:
    """
    Construye y compila un archivo .eml compatible con Outlook con el logotipo
    oficial de SIGRAMA embebido inline y solicitud amable de autorización.
    """
    # Usar multipart/related como raíz para soporte nativo de imágenes inline (CID)
    msg = MIMEMultipart("related")

    # 1. Asunto Normativo Estricto: 'REQ XXXXX - Descripción Breve - Fecha - Área'
    req_id = req_data.get("id_requisicion", "REQ-00000")
    descripcion = req_data.get("descripcion_breve", "Suministro de Materiales")
    fecha = req_data.get("fecha_requisicion", datetime.date.today().strftime("%Y-%m-%d"))
    area = req_data.get("area_impacto", "Materiales")

    subject_clean = f"{req_id} - {descripcion} - {fecha} - {area}"
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

    solicitante = req_data.get("solicitante", "Ing. Jesús Alberto Morales")
    msg["From"] = "sistema.requisiciones@sigrama.com.mx"
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="sigrama.com.mx")
    msg["X-Priority"] = "1" if req_data.get("prioridad") == "Urgente" else "3"
    msg["X-Unsent"] = "1"  # Permite que Outlook lo abra directamente como borrador listo

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

Estimada Lic. {to_info['nombre']},

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

Lic. Lorena, le agradeceríamos enormemente si nos puede apoyar confirmando por este medio su amable visto bueno y autorización para la Requisición {req_id}, con el fin de poder continuar con el proceso y formalizar la correspondiente Orden de Compra (PO).

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
                    Estimada Lic. {to_info['nombre']},
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

                <!-- CAJA DESTACADA DE SOLICITUD AMABLE DE VISTO BUENO -->
                <div style="background-color:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #10B981; border-radius:6px; padding:18px; margin:24px 0;">
                    <div style="font-weight:bold; font-size:14.5px; color:#166534;">
                        ✓ Solicitud de Visto Bueno y Autorización
                    </div>
                    <div style="font-size:13.5px; color:#15803D; margin-top:6px; line-height:1.5;">
                        Lic. Lorena, le agradeceríamos enormemente si nos puede apoyar confirmando por este medio su <strong>amable visto bueno y autorización</strong> para la <strong>Requisición {req_id}</strong>, con el fin de poder continuar con el proceso y formalizar la correspondiente Orden de Compra (PO).
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
