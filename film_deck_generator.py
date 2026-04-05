#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 Film Deck Generator — AI Studio Elsewhere
Production-ready pitch deck PDF for directors and producers
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak,
    Table, TableStyle, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from PIL import Image as PILImage


class FilmDeckGenerator:
    """Generate professional film pitch decks as PDF"""
    
    def __init__(self, output_dir: str = "exports"):
        """Initialize generator with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def create_styles(self):
        """Create professional ReportLab styles"""
        styles = getSampleStyleSheet()
        
        # Cover title
        styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=styles['Heading1'],
            fontSize=48,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=24,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section heading
        styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#e74c3c'),
            borderWidth=3,
            borderPadding=12,
            borderRadius=4
        ))
        
        # Subsection
        styles.add(ParagraphStyle(
            name='SubSection',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=8,
            spaceBefore=8,
            fontName='Helvetica-Bold'
        ))
        
        # Body text
        styles.add(ParagraphStyle(
            name='BodyText',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            fontName='Helvetica',
            leading=14
        ))
        
        # Metadata
        styles.add(ParagraphStyle(
            name='Metadata',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=6,
            fontName='Helvetica'
        ))
        
        # Tagline
        styles.add(ParagraphStyle(
            name='Tagline',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#e74c3c'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))
        
        return styles
    
    def resize_image(self, image_path: str, max_width: float = 6, max_height: float = 4) -> Optional[str]:
        """Resize image for deck"""
        try:
            img = PILImage.open(image_path)
            aspect_ratio = img.width / img.height
            
            if aspect_ratio > (max_width / max_height):
                new_width = int(max_width * 72)
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = int(max_height * 72)
                new_width = int(new_height * aspect_ratio)
            
            img_resized = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            temp_path = self.output_dir / f"temp_{Path(image_path).stem}.png"
            img_resized.save(temp_path, quality=95)
            
            return str(temp_path)
        except Exception as e:
            print(f"⚠️ Image resize error: {e}")
            return None
    
    def export_film_deck(
        self,
        title: str,
        director: str = "",
        logline: str = "",
        vision: str = "",
        tone: List[str] = None,
        scenes: List[Dict[str, Any]] = None,
        storyboard: List[Dict[str, Any]] = None,
        storyboard_images: List[Optional[str]] = None,
        cover_image: Optional[str] = None,
        production_company: str = "",
        year: int = None
    ) -> Optional[str]:
        """
        Export complete film deck to PDF
        
        Args:
            title: Film title
            director: Director name
            logline: One-line description
            vision: Director's vision/statement
            tone: List of mood/tone descriptors
            scenes: List of scene dicts
            storyboard: List of storyboard panel dicts
            storyboard_images: List of storyboard image paths
            cover_image: Optional cover image path
            production_company: Production company name
            year: Production year
        
        Returns:
            Path to generated PDF
        """
        
        if year is None:
            year = datetime.now().year
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"film_deck_{timestamp}.pdf"
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
        
        # ==================== COVER PAGE ====================
        
        elements.append(Spacer(1, 1*inch))
        
        # Cover image if provided
        if cover_image and os.path.exists(cover_image):
            try:
                resized = self.resize_image(cover_image, max_width=5.5, max_height=3)
                if resized:
                    elements.append(Image(resized, width=5.5*inch, height=3*inch))
                    elements.append(Spacer(1, 0.3*inch))
            except:
                pass
        
        # Title
        elements.append(Paragraph(title, styles['CoverTitle']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Director and info
        if director:
            elements.append(Paragraph(f"Director: {director}", styles['Metadata']))
        if production_company:
            elements.append(Paragraph(production_company, styles['Metadata']))
        if year:
            elements.append(Paragraph(str(year), styles['Metadata']))
        
        elements.append(PageBreak())
        
        # ==================== LOGLINE ====================
        
        elements.append(Paragraph("Logline", styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))
        
        if logline:
            elements.append(Paragraph(logline, styles['BodyText']))
        else:
            elements.append(Paragraph("A story waiting to be told.", styles['BodyText']))
        
        elements.append(PageBreak())
        
        # ==================== DIRECTOR VISION ====================
        
        elements.append(Paragraph("Director's Vision", styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))
        
        if vision:
            elements.append(Paragraph(vision, styles['BodyText']))
        else:
            elements.append(Paragraph("A visual exploration of human experience.", styles['BodyText']))
        
        elements.append(PageBreak())
        
        # ==================== MOOD & TONE ====================
        
        elements.append(Paragraph("Mood & Tone", styles['SectionHeading']))
        elements.append(Spacer(1, 0.1*inch))
        
        if tone:
            tone_text = " • ".join(tone)
            elements.append(Paragraph(tone_text, styles['BodyText']))
        else:
            elements.append(Paragraph("Cinematic • Poetic • Immersive", styles['BodyText']))
        
        elements.append(PageBreak())
        
        # ==================== SCENE OVERVIEW ====================
        
        if scenes:
            elements.append(Paragraph("Scene Overview", styles['SectionHeading']))
            elements.append(Spacer(1, 0.1*inch))
            
            for scene in scenes:
                elements.append(Paragraph(
                    f"Scene {scene.get('scene_number', '—')}: {scene.get('heading', 'Scene')}",
                    styles['SubSection']
                ))
                elements.append(Paragraph(
                    f"Location: {scene.get('location', 'N/A')}",
                    styles['Metadata']
                ))
                
                if scene.get('description'):
                    elements.append(Paragraph(scene['description'], styles['BodyText']))
                elif scene.get('action'):
                    elements.append(Paragraph(scene['action'], styles['BodyText']))
                
                elements.append(Spacer(1, 0.15*inch))
            
            elements.append(PageBreak())
        
        # ==================== STORYBOARD ====================
        
        if storyboard:
            elements.append(Paragraph("Storyboard", styles['SectionHeading']))
            elements.append(Spacer(1, 0.1*inch))
            
            storyboard_images = storyboard_images or []
            
            for i, panel in enumerate(storyboard):
                
                elements.append(Paragraph(
                    f"Panel {i+1}: {panel.get('shot', 'Shot')}",
                    styles['SubSection']
                ))
                
                if panel.get('description'):
                    elements.append(Paragraph(panel['description'], styles['BodyText']))
                
                if panel.get('camera_direction'):
                    elements.append(Paragraph(
                        f"<b>Camera:</b> {panel['camera_direction']}",
                        styles['Metadata']
                    ))
                
                elements.append(Spacer(1, 0.1*inch))
                
                # Image
                if i < len(storyboard_images) and storyboard_images[i]:
                    try:
                        resized = self.resize_image(storyboard_images[i])
                        if resized:
                            elements.append(Image(resized, width=5.5*inch, height=3.5*inch))
                            elements.append(Spacer(1, 0.15*inch))
                    except:
                        pass
                
                elements.append(Spacer(1, 0.2*inch))
                
                # Page break every 2 panels
                if (i + 1) % 2 == 0 and i < len(storyboard) - 1:
                    elements.append(PageBreak())
        
        # ==================== BUILD PDF ====================
        
        try:
            doc.build(elements)
            print(f"✅ Film deck generated: {filepath}")
            return str(filepath)
        except Exception as e:
            print(f"❌ PDF generation error: {e}")
            return None


# Convenience function
def export_film_deck(
    title: str,
    director: str = "",
    logline: str = "",
    vision: str = "",
    tone: List[str] = None,
    scenes: List[Dict[str, Any]] = None,
    storyboard: List[Dict[str, Any]] = None,
    storyboard_images: List[Optional[str]] = None,
    cover_image: Optional[str] = None,
    production_company: str = "",
    year: int = None,
    output_dir: str = "exports"
) -> Optional[str]:
    """
    Convenience function to export film deck
    
    Returns:
        Path to generated PDF
    """
    generator = FilmDeckGenerator(output_dir)
    return generator.export_film_deck(
        title=title,
        director=director,
        logline=logline,
        vision=vision,
        tone=tone,
        scenes=scenes,
        storyboard=storyboard,
        storyboard_images=storyboard_images,
        cover_image=cover_image,
        production_company=production_company,
        year=year
    )
