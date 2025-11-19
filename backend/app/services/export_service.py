from fastapi.responses import StreamingResponse
from io import BytesIO
import csv
from datetime import datetime
from typing import List, Dict
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

class ExportService:
    
    def export_to_csv(self, data: List[Dict]) -> StreamingResponse:
        """Export data to CSV format"""
        if not data:
            # Return empty CSV with headers only
            output = BytesIO()
            output.write('No data to export\n'.encode('utf-8'))
            output.seek(0)
            filename = f"wifi_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            return StreamingResponse(
                output,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Type": "text/csv; charset=utf-8"
                }
            )
        
        # Create CSV in memory using StringIO then encode
        from io import StringIO
        string_output = StringIO()
        
        writer = csv.DictWriter(
            string_output,
            fieldnames=data[0].keys(),
            quoting=csv.QUOTE_ALL
        )
        
        writer.writeheader()
        for row in data:
            writer.writerow(row)
        
        # Convert to bytes with BOM for Excel
        output = BytesIO()
        output.write('\ufeff'.encode('utf-8'))  # UTF-8 BOM
        output.write(string_output.getvalue().encode('utf-8'))
        output.seek(0)
        
        # Generate filename with timestamp
        filename = f"wifi_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    
    def export_to_excel(self, data: List[Dict]) -> StreamingResponse:
        """Export data to Excel format"""
        if not data:
            # Create empty Excel file
            df = pd.DataFrame({'Message': ['No data to export']})
        else:
            # Create DataFrame
            df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='WiFi Sessions', index=False)
            
            # Get workbook and worksheet objects
            workbook = writer.book
            worksheet = writer.sheets['WiFi Sessions']
            
            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'text_wrap': True,
                'valign': 'top',
                'fg_color': '#1890ff',
                'font_color': 'white',
                'border': 1
            })
            
            # Format header row
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                
                # Auto-adjust column width
                column_len = max(df[value].astype(str).str.len().max(), len(value)) + 2
                worksheet.set_column(col_num, col_num, min(column_len, 50))
            
            # Freeze first row
            worksheet.freeze_panes(1, 0)
            
            # Add filters
            worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)
        
        output.seek(0)
        
        # Generate filename
        filename = f"wifi_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    def export_to_pdf(self, data: List[Dict]) -> StreamingResponse:
        """Export data to PDF format"""
        # Create PDF in memory
        output = BytesIO()
        
        # Create document with landscape orientation
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1890ff'),
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Add title
        title = Paragraph("WiFi Sessions Report", title_style)
        elements.append(title)
        
        # Add generation date
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1  # Center
        )
        date_text = Paragraph(
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            date_style
        )
        elements.append(date_text)
        elements.append(Spacer(1, 20))
        
        if not data:
            # Add no data message
            no_data_style = ParagraphStyle(
                'NoData',
                parent=styles['Normal'],
                fontSize=12,
                alignment=1
            )
            elements.append(Paragraph("No data to export", no_data_style))
        else:
            # Prepare table data - limit columns for PDF
            table_data = []
            
            # Select key columns for PDF (to fit on page)
            key_columns = [
                "User Name", "Mobile", "MAC Address",
                "Start Time", "Duration (sec)", "Total Data (bytes)", "Status"
            ]
            
            # Header row
            table_data.append(key_columns)
            
            # Data rows
            for row in data:
                table_data.append([
                    str(row.get(col, "N/A")) for col in key_columns
                ])
            
            # Create table
            table = Table(table_data, repeatRows=1)
            
            # Table style
            table.setStyle(TableStyle([
                # Header style
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1890ff')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Data style
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f2f5')]),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            
            elements.append(table)
        
        # Add footer with page numbers
        def add_page_number(canvas, doc):
            page_num = canvas.getPageNumber()
            text = f"Page {page_num}"
            canvas.saveState()
            canvas.setFont('Helvetica', 9)
            canvas.drawRightString(
                landscape(A4)[0] - 30,
                20,
                text
            )
            canvas.restoreState()
        
        # Build PDF
        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
        
        output.seek(0)
        
        # Generate filename
        filename = f"wifi_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        return StreamingResponse(
            output,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
