#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Storyboard PDF Export — AI Studio Elsewhere
Production-ready PDF generation for director presentations
"""

import os
import io
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from PIL import Image as PILImage


class StoryboardPDFExporter:
    """Export storyboards to professional PDF documents"""
    
    def __init__(self, output_dir: str = "exports"):
        """Initialize exporter with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_styles(self):
        """Create custom ReportLab styles"""
        styles = getSampleStyleSheet()
        
        # Title style
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Title'],
            fontSize=28,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section heading
        styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#e74c3c'),
            borderWidth=2,
            borderPadding=6,
            borderRadius=3
        ))
        
        # Panel number
        styles.add(ParagraphStyle(
            name='PanelNumber',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))
        
        # Description
        styles.add(ParagraphStyle(
            name='Description',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            fontName='Helvetica'
        ))
        
        # Prompt (small, subtle)
        styles.add(ParagraphStyle(
            name='Prompt',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#95a5a6'),
            spaceAfter=4,
            fontName='Courier',
            fontName='Helvetica-Oblique'
        ))
        
        # Camera direction
        styles.add(ParagraphStyle(
            name='CameraDirection',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#3498db'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        return styles
    
    def resize_image(self, image_path: str, max_width: float = 5.5, max_height: float = 3.5) -> str:
        """
        Resize image for PDF and return path
        
        Args:
            image_path: Path to image file
            max_width: Max width in inches
            max_height: Max height in inches
        
        Returns:
            Path to resized image
        """
        try:
            img = PILImage.open(image_path)
            
            # Calculate aspect ratio
            aspect_ratio = img.width / img.height
            
            # Calculate new size
            if aspect_ratio > (max_width / max_height):
                new_width = int(max_width * 72)  # Convert to pixels
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = int(max_height * 72)
                new_width = int(new_height * aspect_ratio)
            
            # Resize
            img_resized = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            
            # Save to temp location
            temp_path = self.output_dir / f"temp_{Path(image_path).stem}.png"
            img_resized.save(temp_path, quality=95)
            
            return str(temp_path)
        
        except Exception as e:
            print(f"⚠️ Image resize error: {e}")
            return None
    
    def export_storyboard(
        self,
        storyboard: List[Dict[str, Any]],
        image_paths: List[Optional[str]],
        title: str = "Storyboard",
        director: str = "",
        scene_number: str = "",
        project_name: str = ""
    ) -> Optional[str]:
        """
        Export storyboard to PDF
        
        Args:
            storyboard: List of panel dicts with shot, description, prompt
            image_paths: List of image file paths
            title: Storyboard title
            director: Director name
            scene_number: Scene identifier
            project_name: Project name
        
        Returns:
            Path to generated PDF
        """
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"storyboard_{timestamp}.pdf"
        filepath = self.output_dir / filename
        
        # Create document
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        styles = self.create_styles()
        elements = []
        
        # ==================== TITLE PAGE ====================
        
        elements.append(Paragraph(title, styles['CustomTitle']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Project info
        if project_name or director or scene_number:
            info_text = []
            if project_name:
                info_text.append(f"<b>Project:</b> {project_name}")
            if director:
                info_text.append(f"<b>Director:</b> {director}")
            if scene_number:
                info_text.append(f"<b>Scene:</b> {scene_number}")
            
            info_para = Paragraph(" | ".join(info_text), styles['Normal'])
            elements.append(info_para)
            elements.append(Spacer(1, 0.1*inch))
        
        # Timestamp
        timestamp_text = f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}"
        elements.append(Paragraph(timestamp_text, styles['Italic']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Panel count
        panel_count = f"Total Panels: {len(storyboard)}"
        elements.append(Paragraph(panel_count, styles['Heading2']))
        
        elements.append(PageBreak())
        
        # ==================== PANELS ====================
        
        for i, panel in enumerate(storyboard):
            
            # Panel number and shot type
            panel_num = f"Panel {i+1} — {panel.get('shot', 'Shot')}"
            elements.append(Paragraph(panel_num, styles['SectionHeading']))
            
            # Description
            description = panel.get('description', '')
            if description:
                elements.append(Paragraph(description, styles['Description']))
            
            # Camera direction
            camera_dir = panel.get('camera_direction', '')
            if camera_dir:
                camera_text = f"📹 {camera_dir}"
                elements.append(Paragraph(camera_text, styles['CameraDirection']))
            
            elements.append(Spacer(1, 0.1*inch))
            
            # Image
            if i < len(image_paths) and image_paths[i]:
                try:
                    resized_path = self.resize_image(image_paths[i])
                    if resized_path and os.path.exists(resized_path):
                        img = Image(resized_path, width=5.5*inch, height=3.5*inch)
                        elements.append(img)
                        elements.append(Spacer(1, 0.15*inch))
                
                except Exception as e:
                    placeholder = f"[Image: {Path(image_paths[i]).name}]"
                    elements.append(Paragraph(placeholder, styles['Italic']))
                    elements.append(Spacer(1, 0.1*inch))
            
            # Prompt (technical layer for reference)
            prompt = panel.get('prompt', '')
            if prompt:
                prompt_text = f"<b>Prompt:</b> {prompt[:200]}{'...' if len(prompt) > 200 else ''}"
                elements.append(Paragraph(prompt_text, styles['Prompt']))
            
            elements.append(Spacer(1, 0.25*inch))
            
            # Page break every 2 panels for clean layout
            if (i + 1) % 2 == 0 and i < len(storyboard) - 1:
                elements.append(PageBreak())
        
        # ==================== BUILD PDF ====================
        
        try:
            doc.build(elements)
            print(f"✅ PDF generated: {filepath}")
            return str(filepath)
        
        except Exception as e:
            print(f"❌ PDF generation error: {e}")
            return None


# Convenience function
def export_storyboard_pdf(
    storyboard: List[Dict[str, Any]],
    image_paths: List[Optional[str]],
    title: str = "Storyboard",
    director: str = "",
    scene_number: str = "",
    project_name: str = "",
    output_dir: str = "exports"
) -> Optional[str]:
    """
    Convenience function to export storyboard PDF
    
    Args:
        storyboard: List of panel dicts
        image_paths: List of image paths
        title: PDF title
        director: Director name
        scene_number: Scene identifier
        project_name: Project name
        output_dir: Output directory
    
    Returns:
        Path to PDF file
    """
    exporter = StoryboardPDFExporter(output_dir)
    return exporter.export_storyboard(
        storyboard,
        image_paths,
        title=title,
        director=director,
        scene_number=scene_number,
        project_name=project_name
    )
