"""
Create Sample PDF Files for Phase 4 Testing
Generates various PDF structures for comprehensive testing
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from pathlib import Path

# Create sample_data directory if it doesn't exist
SAMPLE_DIR = Path(__file__).parent / "sample_data"
SAMPLE_DIR.mkdir(exist_ok=True)


def create_text_document():
    """Create a pure text PDF document"""
    filename = SAMPLE_DIR / "text_document.pdf"
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, spaceAfter=20)
    story.append(Paragraph("DMA Smart City Initiative Guidelines", title_style))
    story.append(Spacer(1, 12))
    
    # Introduction
    story.append(Paragraph("Introduction", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    intro_text = """
    The Directorate of Municipal Administration (DMA) Smart City Initiative aims to transform 
    urban governance through digital innovation and citizen-centric services. This comprehensive 
    guideline outlines the framework, objectives, and implementation strategy for participating 
    municipalities across Maharashtra.
    """
    story.append(Paragraph(intro_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Objectives
    story.append(Paragraph("Key Objectives", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    objectives_text = """
    1. Digital Infrastructure Development: Establish robust digital infrastructure including 
    high-speed internet connectivity, data centers, and smart sensors across the city.
    
    2. E-Governance Services: Implement comprehensive online services for citizens including 
    property tax payment, birth/death certificate issuance, and complaint management systems.
    
    3. Citizen Engagement: Create platforms for direct citizen participation in governance 
    through mobile applications, web portals, and feedback mechanisms.
    
    4. Data-Driven Decision Making: Utilize analytics and AI to optimize city services, 
    traffic management, waste collection, and resource allocation.
    """
    story.append(Paragraph(objectives_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Implementation Strategy
    story.append(Paragraph("Implementation Strategy", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    implementation_text = """
    Phase 1 (Months 1-6): Assessment and Planning
    Conduct city-wide needs assessment, stakeholder consultations, and develop detailed 
    project plans. Identify priority areas and allocate budgets.
    
    Phase 2 (Months 7-18): Infrastructure Setup
    Deploy digital infrastructure, establish data centers, install smart sensors, and 
    set up command and control centers.
    
    Phase 3 (Months 19-30): Service Launch
    Roll out citizen services progressively, starting with high-impact services like 
    online tax payment and grievance redressal.
    
    Phase 4 (Months 31-36): Evaluation and Optimization
    Monitor service performance, gather citizen feedback, and continuously improve 
    based on data insights and user experience.
    """
    story.append(Paragraph(implementation_text, styles['Normal']))
    
    doc.build(story)
    print(f"✓ Created: {filename}")


def create_document_with_tables():
    """Create a PDF with both text and tables"""
    filename = SAMPLE_DIR / "document_with_tables.pdf"
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("Municipal Services Directory", styles['Heading1']))
    story.append(Spacer(1, 12))
    
    # Introduction text
    intro = """
    This directory provides contact information for key municipal departments and officials. 
    Citizens can reach out to the relevant department for services and assistance.
    """
    story.append(Paragraph(intro, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Department Table
    story.append(Paragraph("Department Contact Information", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    dept_data = [
        ['Department', 'Contact Person', 'Phone', 'Email'],
        ['Public Works', 'Rajesh Kumar', '022-12345678', 'rajesh.kumar@dma.gov.in'],
        ['Health Services', 'Priya Sharma', '022-23456789', 'priya.sharma@dma.gov.in'],
        ['Education', 'Amit Patel', '022-34567890', 'amit.patel@dma.gov.in'],
        ['Water Supply', 'Sunita Desai', '022-45678901', 'sunita.desai@dma.gov.in'],
    ]
    
    dept_table = Table(dept_data, colWidths=[2*inch, 1.5*inch, 1.2*inch, 2*inch])
    dept_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(dept_table)
    story.append(Spacer(1, 20))
    
    # Additional text
    footer_text = """
    For urgent matters, citizens can contact the 24/7 helpline at 1800-123-4567 or 
    visit the municipal office during working hours (9 AM to 6 PM, Monday to Friday).
    """
    story.append(Paragraph(footer_text, styles['Normal']))
    
    doc.build(story)
    print(f"✓ Created: {filename}")


def create_mostly_tables():
    """Create a PDF that is mostly tables"""
    filename = SAMPLE_DIR / "mostly_tables.pdf"
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("Municipal Officers Directory", styles['Heading1']))
    story.append(Spacer(1, 12))
    
    # Large table with many officers
    table_data = [
        ['Name', 'Position', 'Department', 'Phone', 'Email']
    ]
    
    officers = [
        ('Rajesh Kumar', 'Chief Engineer', 'Public Works', '9876543210', 'rajesh.k@dma.gov.in'),
        ('Priya Sharma', 'Health Officer', 'Health Services', '9876543211', 'priya.s@dma.gov.in'),
        ('Amit Patel', 'Education Officer', 'Education', '9876543212', 'amit.p@dma.gov.in'),
        ('Sunita Desai', 'Water Supply Manager', 'Water Supply', '9876543213', 'sunita.d@dma.gov.in'),
        ('Vikram Singh', 'Sanitation Officer', 'Sanitation', '9876543214', 'vikram.s@dma.gov.in'),
        ('Meera Joshi', 'Tax Officer', 'Revenue', '9876543215', 'meera.j@dma.gov.in'),
        ('Arun Verma', 'Building Inspector', 'Town Planning', '9876543216', 'arun.v@dma.gov.in'),
        ('Kavita Nair', 'Social Welfare Officer', 'Social Welfare', '9876543217', 'kavita.n@dma.gov.in'),
        ('Suresh Reddy', 'IT Manager', 'IT Department', '9876543218', 'suresh.r@dma.gov.in'),
        ('Anjali Mehta', 'HR Manager', 'Administration', '9876543219', 'anjali.m@dma.gov.in'),
    ]
    
    for officer in officers:
        table_data.append(list(officer))
    
    table = Table(table_data, colWidths=[1.5*inch, 1.5*inch, 1.3*inch, 1.2*inch, 1.8*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    
    story.append(table)
    
    doc.build(story)
    print(f"✓ Created: {filename}")


def create_faq_document():
    """Create a PDF with FAQ format"""
    filename = SAMPLE_DIR / "faq_document.pdf"
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("Frequently Asked Questions - Municipal Services", styles['Heading1']))
    story.append(Spacer(1, 20))
    
    # FAQ pairs (bilingual)
    faqs = [
        {
            'q_en': 'How can I pay my property tax online?',
            'a_en': 'You can pay property tax online by visiting our official website www.dma.gov.in, '
                   'clicking on "Pay Tax" section, entering your property ID, and making payment through '
                   'credit card, debit card, or net banking.',
            'q_mr': 'मी माझा मालमत्ता कर ऑनलाइन कसा भरू शकतो?',
            'a_mr': 'तुम्ही आमच्या अधिकृत वेबसाइट www.dma.gov.in ला भेट देऊन मालमत्ता कर ऑनलाइन भरू शकता.'
        },
        {
            'q_en': 'What documents are required for birth certificate?',
            'a_en': 'Required documents include: Hospital birth certificate, Parents\' Aadhaar cards, '
                   'Marriage certificate, and Residential proof. Application can be submitted online or '
                   'at the municipal office.',
            'q_mr': 'जन्म दाखला मिळवण्यासाठी कोणती कागदपत्रे आवश्यक आहेत?',
            'a_mr': 'आवश्यक कागदपत्रे: रुग्णालयाचा जन्म दाखला, पालकांचे आधार कार्ड, '
                   'विवाह प्रमाणपत्र आणि निवास पुरावा.'
        },
        {
            'q_en': 'How do I register a complaint about water supply?',
            'a_en': 'You can register water supply complaints through: 1) Online portal at www.dma.gov.in/complaints, '
                   '2) 24x7 helpline: 1800-123-4567, 3) Mobile app: DMA Citizen Services, or 4) Visit the '
                   'water supply department office.',
            'q_mr': 'पाणी पुरवठ्याबद्दल तक्रार कशी नोंदवावी?',
            'a_mr': 'तुम्ही पाणी पुरवठा तक्रार यांच्याद्वारे नोंदवू शकता: १) www.dma.gov.in/complaints वर ऑनलाइन, '
                   '२) २४x७ हेल्पलाइन: १८००-१२३-४५६७.'
        },
    ]
    
    for i, faq in enumerate(faqs, 1):
        # English Q&A
        story.append(Paragraph(f"Q{i}: {faq['q_en']}", styles['Heading3']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"A: {faq['a_en']}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Marathi Q&A
        story.append(Paragraph(f"प्रश्न {i}: {faq['q_mr']}", styles['Heading3']))
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"उत्तर: {faq['a_mr']}", styles['Normal']))
        story.append(Spacer(1, 20))
    
    doc.build(story)
    print(f"✓ Created: {filename}")


def create_form_template():
    """Create a PDF that looks like a form"""
    filename = SAMPLE_DIR / "form_template.pdf"
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("Application Form for Birth Certificate", styles['Heading1']))
    story.append(Spacer(1, 20))
    
    # Form fields
    form_fields = [
        "Name: _____________________________________________________",
        "Date of Birth: ____________________",
        "Place of Birth: ______________________________________________",
        "Father's Name: _________________________________________________",
        "Mother's Name: _________________________________________________",
        "Address: _______________________________________________________",
        "         _______________________________________________________",
        "         _______________________________________________________",
        "Contact Number: ____________________",
        "Email: __________________________________________________________",
        "Signature: ____________________   Date: ____________________"
    ]
    
    for field in form_fields:
        story.append(Paragraph(field, styles['Normal']))
        story.append(Spacer(1, 10))
    
    story.append(Spacer(1, 20))
    story.append(Paragraph("Documents to be attached:", styles['Heading3']))
    story.append(Spacer(1, 10))
    
    doc_list = [
        "□ Hospital Birth Certificate",
        "□ Parents' Aadhaar Cards",
        "□ Marriage Certificate",
        "□ Residential Proof"
    ]
    
    for doc_item in doc_list:
        story.append(Paragraph(doc_item, styles['Normal']))
        story.append(Spacer(1, 8))
    
    doc.build(story)
    print(f"✓ Created: {filename}")


def create_complex_mix():
    """Create a complex PDF with text, tables, and various elements"""
    filename = SAMPLE_DIR / "complex_mix.pdf"
    doc = SimpleDocTemplate(str(filename), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("Municipal Annual Report 2024", styles['Heading1']))
    story.append(Spacer(1, 20))
    
    # Executive Summary (text)
    story.append(Paragraph("Executive Summary", styles['Heading2']))
    story.append(Spacer(1, 10))
    summary_text = """
    The year 2024 has been transformative for our municipality. We have successfully 
    implemented digital governance initiatives, improved citizen services, and achieved 
    significant milestones in infrastructure development. This report provides a 
    comprehensive overview of our achievements, challenges, and future plans.
    """
    story.append(Paragraph(summary_text, styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Budget Table
    story.append(Paragraph("Budget Allocation (in Crores)", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    budget_data = [
        ['Department', 'Allocated', 'Spent', 'Balance'],
        ['Public Works', '₹ 50', '₹ 45', '₹ 5'],
        ['Health', '₹ 30', '₹ 28', '₹ 2'],
        ['Education', '₹ 40', '₹ 38', '₹ 2'],
        ['Water Supply', '₹ 25', '₹ 24', '₹ 1'],
    ]
    
    budget_table = Table(budget_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
    budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(budget_table)
    story.append(Spacer(1, 20))
    
    # FAQ Section
    story.append(Paragraph("Common Questions", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Q: How can citizens access these services?", styles['Heading3']))
    story.append(Paragraph("A: Services are available through our website, mobile app, and help centers.", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Contact Info
    story.append(Paragraph("Contact Information", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    contact_info = """
    Directorate of Municipal Administration<br/>
    Main Office: 123 Government Road, Mumbai - 400001<br/>
    Phone: 022-12345678<br/>
    Email: info@dma.gov.in<br/>
    Website: www.dma.gov.in
    """
    story.append(Paragraph(contact_info, styles['Normal']))
    
    doc.build(story)
    print(f"✓ Created: {filename}")


if __name__ == "__main__":
    print("Creating sample PDF files for Phase 4 testing...")
    print("-" * 60)
    
    try:
        create_text_document()
        create_document_with_tables()
        create_mostly_tables()
        create_faq_document()
        create_form_template()
        create_complex_mix()
        
        print("-" * 60)
        print(f"✓ All sample PDFs created successfully in: {SAMPLE_DIR}")
        print("\nGenerated files:")
        print("  1. text_document.pdf - Pure text document")
        print("  2. document_with_tables.pdf - Mixed text and tables")
        print("  3. mostly_tables.pdf - Primarily tables")
        print("  4. faq_document.pdf - FAQ format (bilingual)")
        print("  5. form_template.pdf - Form template")
        print("  6. complex_mix.pdf - Complex mixed content")
        
    except ImportError as e:
        print(f"\n❌ Error: Missing required library")
        print(f"   {str(e)}")
        print("\n   Please install reportlab:")
        print("   pip install reportlab")
    except Exception as e:
        print(f"\n❌ Error creating PDFs: {str(e)}")
        raise

