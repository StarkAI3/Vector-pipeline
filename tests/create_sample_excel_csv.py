"""
Create Sample Excel and CSV Files for Phase 2 Testing
Generates various file structures to test all extraction and processing scenarios
"""
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Output directory
OUTPUT_DIR = Path(__file__).parent / "sample_data"
OUTPUT_DIR.mkdir(exist_ok=True)

print("Creating sample Excel and CSV files...")
print(f"Output directory: {OUTPUT_DIR}")

# ============================================================================
# 1. Standard Data Table (Excel & CSV)
# ============================================================================
print("\n1. Creating standard_table_officials.xlsx/.csv...")

standard_data = {
    'Name': ['रामेश कुमार', 'प्रिया शर्मा', 'अमित पाटील', 'सुनीता देशमुख', 'विकास जोशी'],
    'Position': ['Commissioner', 'Deputy Commissioner', 'Assistant Commissioner', 'Section Officer', 'Clerk'],
    'Department': ['Administration', 'Finance', 'Revenue', 'Public Works', 'IT Department'],
    'Email': ['ramesh.kumar@dma.gov.in', 'priya.sharma@dma.gov.in', 'amit.patil@dma.gov.in', 
              'sunita.deshmukh@dma.gov.in', 'vikas.joshi@dma.gov.in'],
    'Phone': ['+91-22-2266-1001', '+91-22-2266-1002', '+91-22-2266-1003', 
              '+91-22-2266-1004', '+91-22-2266-1005'],
    'Office': ['Mumbai HQ', 'Mumbai HQ', 'Pune Branch', 'Nagpur Branch', 'Mumbai HQ']
}

df_standard = pd.DataFrame(standard_data)
df_standard.to_excel(OUTPUT_DIR / 'standard_table_officials.xlsx', index=False)
df_standard.to_csv(OUTPUT_DIR / 'standard_table_officials.csv', index=False, encoding='utf-8')

print("   ✓ Created standard_table_officials.xlsx (5 rows)")
print("   ✓ Created standard_table_officials.csv (5 rows)")

# ============================================================================
# 2. FAQ Table - 2 Column (Excel & CSV)
# ============================================================================
print("\n2. Creating faq_table_2col_english.xlsx/.csv...")

faq_2col = {
    'Question': [
        'How do I apply for a birth certificate?',
        'What documents are needed for a property tax payment?',
        'How long does it take to get a trade license?',
        'What are the office hours for municipal services?',
        'How can I file a complaint about garbage collection?'
    ],
    'Answer': [
        'Visit the nearest municipal office with your hospital discharge papers and parents\' ID proof. Fill out Form BC-01 and submit with required documents. Certificate will be issued within 7 working days.',
        'You need: 1) Property ownership documents, 2) Previous tax receipts, 3) ID proof of owner, 4) Property survey number. Visit the revenue office or pay online through the official portal.',
        'Trade license processing typically takes 15-20 working days after submission of complete application with all required documents including shop registration, health certificate, and fire safety approval.',
        'Municipal offices are open Monday to Friday from 10:00 AM to 5:00 PM. Saturday hours are 10:00 AM to 2:00 PM. Offices are closed on Sundays and public holidays.',
        'File complaints through: 1) Online portal at complaints.dma.gov.in, 2) Call helpline 1800-XXX-XXXX, 3) Visit ward office in person, 4) Use mobile app "DMA Connect". Complaint will be registered and tracking ID provided.'
    ]
}

df_faq_2col = pd.DataFrame(faq_2col)
df_faq_2col.to_excel(OUTPUT_DIR / 'faq_table_2col_english.xlsx', index=False)
df_faq_2col.to_csv(OUTPUT_DIR / 'faq_table_2col_english.csv', index=False, encoding='utf-8')

print("   ✓ Created faq_table_2col_english.xlsx (5 FAQs)")
print("   ✓ Created faq_table_2col_english.csv (5 FAQs)")

# ============================================================================
# 3. FAQ Table - 4 Column Bilingual (Excel & CSV)
# ============================================================================
print("\n3. Creating faq_table_4col_bilingual.xlsx/.csv...")

faq_4col = {
    'Question_EN': [
        'How do I register a new business?',
        'What is the process for building permit?',
        'How to pay water bills online?'
    ],
    'Answer_EN': [
        'Visit the Trade Department with: 1) Business plan, 2) Shop ownership proof, 3) PAN card, 4) Aadhar card. Fill application form TR-05. Pay registration fee of ₹500. License issued in 10 days.',
        'Submit building plans to Town Planning Department. Required: architect-approved drawings, land ownership documents, NOC from fire department. Approval takes 30-45 days depending on complexity.',
        'Visit portal.dma.gov.in/water-bills. Login with consumer number. Select pending bills. Pay using credit card, debit card, net banking, or UPI. Receipt generated immediately.'
    ],
    'Question_MR': [
        'नवीन व्यवसाय नोंदणी कशी करावी?',
        'इमारत परवान्यासाठी प्रक्रिया काय आहे?',
        'पाणी बिले ऑनलाइन कसे भरावे?'
    ],
    'Answer_MR': [
        'व्यापार विभागात भेट द्या: 1) व्यवसाय योजना, 2) दुकान मालकी पुरावा, 3) पॅन कार्ड, 4) आधार कार्ड. अर्ज TR-05 भरा. ₹500 नोंदणी शुल्क भरा. 10 दिवसात परवाना मिळेल.',
        'शहर नियोजन विभागाकडे इमारत योजना सबमिट करा. आवश्यक: वास्तुविशारद-मंजूर रेखाचित्रे, जमीन मालकी कागदपत्रे, अग्निशमन विभागाकडून NOC. मंजूरीला 30-45 दिवस लागतात.',
        'portal.dma.gov.in/water-bills ला भेट द्या. ग्राहक क्रमांकाने लॉगिन करा. प्रलंबित बिले निवडा. क्रेडिट कार्ड, डेबिट कार्ड, नेट बँकिंग किंवा UPI वापरून पैसे भरा. पावती लगेच मिळेल.'
    ]
}

df_faq_4col = pd.DataFrame(faq_4col)
df_faq_4col.to_excel(OUTPUT_DIR / 'faq_table_4col_bilingual.xlsx', index=False)
df_faq_4col.to_csv(OUTPUT_DIR / 'faq_table_4col_bilingual.csv', index=False, encoding='utf-8')

print("   ✓ Created faq_table_4col_bilingual.xlsx (3 bilingual FAQs)")
print("   ✓ Created faq_table_4col_bilingual.csv (3 bilingual FAQs)")

# ============================================================================
# 4. Directory/Contact List (Excel & CSV)
# ============================================================================
print("\n4. Creating directory_contact_list.xlsx/.csv...")

directory_data = {
    'Officer_Name': ['Dr. संजय मेहता', 'श्रीमती अनुराधा कुलकर्णी', 'श्री राजेश गायकवाड', 'श्रीमती पूजा नाईक'],
    'Designation': ['Chief Municipal Officer', 'Health Officer', 'Town Planner', 'Education Officer'],
    'Department': ['Administration', 'Public Health', 'Urban Planning', 'Education & Culture'],
    'Office_Address': [
        'Main Municipal Building, Ground Floor, Room 101, Mumbai - 400001',
        'Health Department, 2nd Floor, Annexe Building, Mumbai - 400001',
        'Town Planning Office, 3rd Floor, Main Building, Mumbai - 400001',
        'Education Wing, 1st Floor, Civic Center, Mumbai - 400002'
    ],
    'Phone_Office': ['+91-22-2266-2001', '+91-22-2266-2050', '+91-22-2266-2075', '+91-22-2266-2100'],
    'Phone_Mobile': ['+91-9876543210', '+91-9876543211', '+91-9876543212', '+91-9876543213'],
    'Email': ['sanjay.mehta@dma.gov.in', 'anuradha.kulkarni@dma.gov.in', 
              'rajesh.gaikwad@dma.gov.in', 'pooja.naik@dma.gov.in'],
    'Office_Hours': ['Mon-Fri: 10 AM - 5 PM', 'Mon-Sat: 9 AM - 4 PM', 
                     'Mon-Fri: 10 AM - 5 PM', 'Mon-Sat: 9 AM - 4 PM']
}

df_directory = pd.DataFrame(directory_data)
df_directory.to_excel(OUTPUT_DIR / 'directory_contact_list.xlsx', index=False)
df_directory.to_csv(OUTPUT_DIR / 'directory_contact_list.csv', index=False, encoding='utf-8')

print("   ✓ Created directory_contact_list.xlsx (4 officers)")
print("   ✓ Created directory_contact_list.csv (4 officers)")

# ============================================================================
# 5. Service Catalog (Excel & CSV)
# ============================================================================
print("\n5. Creating service_catalog.xlsx/.csv...")

services_data = {
    'Service_Name': [
        'Birth Certificate',
        'Property Tax Payment',
        'Trade License',
        'Water Connection',
        'Building Permit'
    ],
    'Service_Name_MR': [
        'जन्म दाखला',
        'मालमत्ता कर भरणा',
        'व्यापार परवाना',
        'पाणी कनेक्शन',
        'इमारत परवाना'
    ],
    'Description': [
        'Official birth registration certificate issued by municipal corporation',
        'Annual property tax payment service for residential and commercial properties',
        'License required for operating commercial business establishments',
        'New water supply connection for residential or commercial properties',
        'Approval for construction of new buildings or major renovations'
    ],
    'Department': [
        'Registration Department',
        'Revenue Department',
        'Trade Department',
        'Water Supply Department',
        'Town Planning Department'
    ],
    'Processing_Time': [
        '7 working days',
        'Immediate (online)',
        '15-20 working days',
        '30 working days',
        '30-45 working days'
    ],
    'Fee': [
        '₹50',
        'Based on property size',
        '₹500',
        '₹2,000 + deposit',
        '₹1,000 - ₹10,000'
    ],
    'Online_Available': [
        'Yes',
        'Yes',
        'Partial',
        'No',
        'Application only'
    ],
    'Portal_Link': [
        'https://services.dma.gov.in/birth-certificate',
        'https://tax.dma.gov.in/property',
        'https://services.dma.gov.in/trade-license',
        '-',
        'https://planning.dma.gov.in/building-permit'
    ]
}

df_services = pd.DataFrame(services_data)
df_services.to_excel(OUTPUT_DIR / 'service_catalog.xlsx', index=False)
df_services.to_csv(OUTPUT_DIR / 'service_catalog.csv', index=False, encoding='utf-8')

print("   ✓ Created service_catalog.xlsx (5 services)")
print("   ✓ Created service_catalog.csv (5 services)")

# ============================================================================
# 6. Multiple Sheets Workbook (Excel only)
# ============================================================================
print("\n6. Creating multi_sheet_workbook.xlsx...")

with pd.ExcelWriter(OUTPUT_DIR / 'multi_sheet_workbook.xlsx', engine='openpyxl') as writer:
    # Sheet 1: Officials
    df_standard.to_excel(writer, sheet_name='Officials', index=False)
    
    # Sheet 2: Services
    df_services[['Service_Name', 'Description', 'Department', 'Fee']].to_excel(
        writer, sheet_name='Services', index=False
    )
    
    # Sheet 3: FAQ
    df_faq_2col.to_excel(writer, sheet_name='FAQ', index=False)

print("   ✓ Created multi_sheet_workbook.xlsx (3 sheets)")

# ============================================================================
# 7. Complex CSV with Special Characters
# ============================================================================
print("\n7. Creating complex_data_with_special_chars.csv...")

complex_data = {
    'ID': ['MH001', 'MH002', 'MH003'],
    'Document_Title': [
        'Guidelines for "Smart City" Initiative',
        'Policy: Waste Management, 2024-2025',
        'Circular No. 45/2024 - COVID-19 Protocols'
    ],
    'Description': [
        'Comprehensive guidelines for implementing smart city projects in Maharashtra. Includes: 1) IoT sensors, 2) Traffic management, 3) E-governance.',
        'Updated waste management policy covering: segregation at source, collection schedules, recycling centers, penalties for non-compliance.',
        'COVID-19 safety protocols for municipal offices: mandatory masks, social distancing (2m), sanitization every 2 hours.'
    ],
    'Issued_By': ['Urban Development', 'Sanitation Department', 'Health Department'],
    'Date': ['2024-01-15', '2024-03-01', '2024-02-10'],
    'Reference_URL': [
        'https://dma.gov.in/circular/smart-city-2024',
        'https://dma.gov.in/policies/waste-mgmt',
        'https://dma.gov.in/covid/circular-45'
    ]
}

df_complex = pd.DataFrame(complex_data)
df_complex.to_csv(OUTPUT_DIR / 'complex_data_with_special_chars.csv', index=False, encoding='utf-8')

print("   ✓ Created complex_data_with_special_chars.csv (3 entries)")

print("\n" + "="*70)
print("✅ All sample Excel and CSV files created successfully!")
print("="*70)
print(f"\nFiles are located in: {OUTPUT_DIR}")
print("\nSummary:")
print("  • 2 Standard table files (Excel + CSV)")
print("  • 2 FAQ 2-column files (Excel + CSV)")
print("  • 2 FAQ 4-column bilingual files (Excel + CSV)")
print("  • 2 Directory files (Excel + CSV)")
print("  • 2 Service catalog files (Excel + CSV)")
print("  • 1 Multi-sheet workbook (Excel)")
print("  • 1 Complex CSV with special characters")
print("\nTotal: 12 test files")
print("\nThese files cover all Excel/CSV extraction and processing scenarios for Phase 2.")

