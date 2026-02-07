"""
Professional PDF Generator Service for SERVONIX
Generates detailed log reports for Complaints, Users, and Admins
"""
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab not installed - PDFs will be text files")

# SERVONIX Brand Colors
BRAND_COLORS = {
    'primary': colors.HexColor('#00C8FF') if REPORTLAB_AVAILABLE else None,
    'secondary': colors.HexColor('#FFD100') if REPORTLAB_AVAILABLE else None,
    'header_bg': colors.HexColor('#1E3A5F') if REPORTLAB_AVAILABLE else None,
    'success': colors.HexColor('#10B981') if REPORTLAB_AVAILABLE else None,
    'accent': colors.HexColor('#8B5CF6') if REPORTLAB_AVAILABLE else None,
    'danger': colors.HexColor('#EF4444') if REPORTLAB_AVAILABLE else None,
    'warning': colors.HexColor('#F59E0B') if REPORTLAB_AVAILABLE else None,
    'text': colors.HexColor('#1F2937') if REPORTLAB_AVAILABLE else None,
    'row_alt': colors.HexColor('#F8FAFC') if REPORTLAB_AVAILABLE else None,
}


def _create_header(canvas_obj, doc, title):
    """Create a professional header for each page"""
    canvas_obj.saveState()
    
    # Header background
    canvas_obj.setFillColor(BRAND_COLORS['header_bg'])
    canvas_obj.rect(0, A4[1] - 80, A4[0], 80, fill=1)
    
    # Logo/Brand name
    canvas_obj.setFillColor(BRAND_COLORS['primary'])
    canvas_obj.setFont("Helvetica-Bold", 24)
    canvas_obj.drawString(40, A4[1] - 45, "SERVONIX")
    
    # Subtitle
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawString(40, A4[1] - 60, "Complaint Management System")
    
    # Report title (right side)
    canvas_obj.setFillColor(BRAND_COLORS['secondary'])
    canvas_obj.setFont("Helvetica-Bold", 16)
    canvas_obj.drawRightString(A4[0] - 40, A4[1] - 45, title)
    
    # Date
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.drawRightString(A4[0] - 40, A4[1] - 60, f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    
    # Footer
    canvas_obj.setFillColor(colors.HexColor('#6B7280'))
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawString(40, 25, f"SERVONIX - Confidential Report")
    canvas_obj.drawRightString(A4[0] - 40, 25, f"Page {doc.page}")
    
    canvas_obj.restoreState()


def _get_styles():
    """Get custom paragraph styles"""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Summary',
        parent=styles['Normal'],
        fontSize=11,
        textColor=BRAND_COLORS['text'],
        spaceBefore=10,
        spaceAfter=10
    ))
    return styles


def generate_complaints_pdf(complaints, output_path=None):
    """Generate a professional PDF report for complaints"""
    if not REPORTLAB_AVAILABLE:
        return _generate_text_fallback(complaints, output_path, 'Complaints')
    
    try:
        if not output_path:
            output_path = os.path.join(os.path.dirname(__file__), 'uploads', f'complaints_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=100, bottomMargin=50, leftMargin=30, rightMargin=30)
        styles = _get_styles()
        elements = []
        
        # Summary section
        total = len(complaints)
        pending = sum(1 for c in complaints if c.get('status') == 'pending')
        in_progress = sum(1 for c in complaints if c.get('status') in ['in-progress', 'in_progress'])
        resolved = sum(1 for c in complaints if c.get('status') == 'resolved')
        rejected = sum(1 for c in complaints if c.get('status') == 'rejected')
        
        summary_text = f"""<b>Report Summary:</b><br/>
        Total Complaints: <b>{total}</b> | 
        Pending: <font color="#F59E0B"><b>{pending}</b></font> | 
        In Progress: <font color="#00C8FF"><b>{in_progress}</b></font> | 
        Resolved: <font color="#10B981"><b>{resolved}</b></font> | 
        Rejected: <font color="#EF4444"><b>{rejected}</b></font>"""
        elements.append(Paragraph(summary_text, styles['Summary']))
        elements.append(Spacer(1, 20))
        
        # Table data
        header = ['ID', 'User', 'Bus No.', 'Category', 'Status', 'Date', 'District']
        table_data = [header]
        
        for c in complaints:
            status = c.get('status', 'pending')
            status_display = {'pending': 'Pending', 'in-progress': 'In Progress', 'in_progress': 'In Progress', 'resolved': 'Resolved', 'rejected': 'Rejected'}.get(status, status)
            
            created = c.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(str(created).replace('Z', '+00:00'))
                    created = dt.strftime('%m/%d/%y')
                except:
                    created = str(created)[:10]
            
            table_data.append([
                str(c.get('id', '')),
                str(c.get('username', c.get('user_name', 'N/A')))[:20],
                str(c.get('bus_number', 'N/A')),
                str(c.get('category', 'N/A'))[:15],
                status_display,
                created,
                str(c.get('district', 'N/A'))[:12]
            ])
        
        # Create table with styling
        table = Table(table_data, colWidths=[35, 90, 55, 70, 75, 60, 70], repeatRows=1)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_COLORS['header_bg']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (5, 0), (5, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, BRAND_COLORS['primary']),
        ])
        
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), BRAND_COLORS['row_alt'])
        
        table.setStyle(table_style)
        elements.append(table)
        
        def add_header(canvas, doc):
            _create_header(canvas, doc, "COMPLAINTS LOG")
        
        doc.build(elements, onFirstPage=add_header, onLaterPages=add_header)
        logger.info(f"Generated complaints PDF: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating complaints PDF: {e}")
        return _generate_text_fallback(complaints, output_path, 'Complaints')


def generate_users_pdf(users, output_path=None):
    """Generate a professional PDF report for users"""
    if not REPORTLAB_AVAILABLE:
        return _generate_text_fallback(users, output_path, 'Users')
    
    try:
        if not output_path:
            output_path = os.path.join(os.path.dirname(__file__), 'uploads', f'users_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=100, bottomMargin=50, leftMargin=30, rightMargin=30)
        styles = _get_styles()
        elements = []
        
        # Summary
        summary_text = f"<b>Total Registered Users: {len(users)}</b>"
        elements.append(Paragraph(summary_text, styles['Summary']))
        elements.append(Spacer(1, 20))
        
        # Table
        header = ['ID', 'Name', 'Email', 'Phone', 'District', 'Registered']
        table_data = [header]
        
        for u in users:
            created = u.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(str(created).replace('Z', '+00:00'))
                    created = dt.strftime('%m/%d/%Y')
                except:
                    created = str(created)[:10]
            
            table_data.append([
                str(u.get('id', '')),
                str(u.get('name', 'N/A'))[:25],
                str(u.get('email', 'N/A'))[:30],
                str(u.get('phone', 'N/A') or 'N/A'),
                str(u.get('district', 'N/A') or 'N/A')[:15],
                created
            ])
        
        table = Table(table_data, colWidths=[35, 100, 150, 80, 80, 70], repeatRows=1)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_COLORS['header_bg']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (5, 0), (5, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, BRAND_COLORS['success']),
        ])
        
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), BRAND_COLORS['row_alt'])
        
        table.setStyle(table_style)
        elements.append(table)
        
        def add_header(canvas, doc):
            _create_header(canvas, doc, "USERS LOG")
        
        doc.build(elements, onFirstPage=add_header, onLaterPages=add_header)
        logger.info(f"Generated users PDF: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating users PDF: {e}")
        return _generate_text_fallback(users, output_path, 'Users')


def generate_admin_pdf(admins, output_path=None):
    """Generate a professional PDF report for admins"""
    if not REPORTLAB_AVAILABLE:
        return _generate_text_fallback(admins, output_path, 'Admins')
    
    try:
        if not output_path:
            output_path = os.path.join(os.path.dirname(__file__), 'uploads', f'admins_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=100, bottomMargin=50, leftMargin=30, rightMargin=30)
        styles = _get_styles()
        elements = []
        
        # Summary
        total = len(admins)
        active = sum(1 for a in admins if a.get('is_active', True))
        inactive = total - active
        
        summary_text = f"""<b>Admin Overview:</b><br/>
        Total Admins: <b>{total}</b> | 
        Active: <font color="#10B981"><b>{active}</b></font> | 
        Inactive: <font color="#EF4444"><b>{inactive}</b></font>"""
        elements.append(Paragraph(summary_text, styles['Summary']))
        elements.append(Spacer(1, 20))
        
        # Table
        header = ['ID', 'Name', 'Email', 'Phone', 'Status', 'Created']
        table_data = [header]
        
        for a in admins:
            is_active = a.get('is_active', True)
            status = 'Active' if is_active else 'Inactive'
            
            created = a.get('created_at', '')
            if created:
                try:
                    dt = datetime.fromisoformat(str(created).replace('Z', '+00:00'))
                    created = dt.strftime('%m/%d/%Y')
                except:
                    created = str(created)[:10]
            
            table_data.append([
                str(a.get('id', '')),
                str(a.get('name', 'N/A'))[:25],
                str(a.get('email', 'N/A'))[:30],
                str(a.get('phone', 'N/A') or 'N/A'),
                status,
                created
            ])
        
        table = Table(table_data, colWidths=[35, 110, 160, 80, 70, 70], repeatRows=1)
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_COLORS['header_bg']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (4, 0), (5, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, BRAND_COLORS['accent']),
        ])
        
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), BRAND_COLORS['row_alt'])
        
        table.setStyle(table_style)
        elements.append(table)
        
        def add_header(canvas, doc):
            _create_header(canvas, doc, "ADMINS LOG")
        
        doc.build(elements, onFirstPage=add_header, onLaterPages=add_header)
        logger.info(f"Generated admins PDF: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating admins PDF: {e}")
        return _generate_text_fallback(admins, output_path, 'Admins')


def generate_complaint_detail_pdf(complaint, output_path):
    """Generate a detailed PDF for a single complaint"""
    if not REPORTLAB_AVAILABLE:
        return None
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=100, bottomMargin=50, leftMargin=40, rightMargin=40)
        styles = _get_styles()
        elements = []
        
        # Complaint ID
        elements.append(Paragraph(f"<font color='#00C8FF'><b>Complaint #{complaint.get('id', 'N/A')}</b></font>",
            ParagraphStyle('ID', fontSize=18, alignment=TA_CENTER, spaceAfter=20)))
        
        # Status
        status = complaint.get('status', 'pending')
        status_colors = {'pending': '#F59E0B', 'in-progress': '#00C8FF', 'in_progress': '#00C8FF', 'resolved': '#10B981', 'rejected': '#EF4444'}
        elements.append(Paragraph(f"<font color='{status_colors.get(status, '#6B7280')}'><b>Status: {status.upper()}</b></font>",
            ParagraphStyle('Status', fontSize=12, alignment=TA_CENTER, spaceAfter=25)))
        
        # Details table
        details = [
            ['Field', 'Value'],
            ['User', str(complaint.get('username', complaint.get('user_name', 'N/A')))],
            ['Email', str(complaint.get('email', 'N/A'))],
            ['Bus Number', str(complaint.get('bus_number', 'N/A'))],
            ['Route', str(complaint.get('route_name', complaint.get('route', 'N/A')))],
            ['District', str(complaint.get('district', 'N/A'))],
            ['Category', str(complaint.get('category', 'N/A'))],
            ['Created', str(complaint.get('created_at', 'N/A'))],
        ]
        
        table = Table(details, colWidths=[120, 350])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BRAND_COLORS['header_bg']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#F3F4F6')),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 20))
        
        # Description
        elements.append(Paragraph("<b>Description:</b>", styles['Summary']))
        elements.append(Paragraph(str(complaint.get('description', 'No description')),
            ParagraphStyle('Desc', fontSize=10, leading=14)))
        
        # Admin response
        if complaint.get('admin_response'):
            elements.append(Spacer(1, 15))
            elements.append(Paragraph("<b>Admin Response:</b>", styles['Summary']))
            elements.append(Paragraph(str(complaint.get('admin_response')),
                ParagraphStyle('Response', fontSize=10, leading=14, textColor=BRAND_COLORS['success'])))
        
        def add_header(canvas, doc):
            _create_header(canvas, doc, "COMPLAINT DETAIL")
        
        doc.build(elements, onFirstPage=add_header, onLaterPages=add_header)
        logger.info(f"Generated complaint detail PDF: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating complaint detail PDF: {e}")
        return None


def _generate_text_fallback(data, output_path, report_type):
    """Fallback to text file if reportlab is not available"""
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        output_path = output_path.replace('.pdf', '.txt')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"SERVONIX - {report_type} Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Total Records: {len(data)}\n\n")
            
            for item in data:
                for key, value in item.items():
                    f.write(f"{key}: {value}\n")
                f.write("-" * 40 + "\n")
        
        logger.info(f"Generated text fallback: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating text fallback: {e}")
        return None
