# -*- coding: utf-8 -*-
"""
Created on Sun Dec  7 00:14:37 2025

@author: iammu
"""

from bs4 import BeautifulSoup
import json

def extract_car_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    extracted_data = {}

    # ---------------------------------------------------------
    # 1. Car Name
    # ---------------------------------------------------------
    try:
        # Find div with id 'scroll_car_info', then get the h1 tag inside it
        car_info_div = soup.find('div', id='scroll_car_info')
        if car_info_div and car_info_div.find('h1'):
            extracted_data['car_name'] = car_info_div.find('h1').get_text(strip=True)
        else:
            extracted_data['car_name'] = "N/A"
    except Exception as e:
        extracted_data['car_name'] = "Error extracting name"

    # ---------------------------------------------------------
    # 2. Engine/Table Details (Year, Mileage, Type, Transmission)
    # ---------------------------------------------------------
    # We map the specific classes found in the span to readable labels
    table_data = {}
    class_map = {
        'year': 'Year',
        'millage': 'Mileage', # Note: keeping HTML typo 'millage' to match source
        'type': 'Fuel Type',
        'transmission': 'Transmission'
    }

    try:
        table = soup.find('table', class_='table-engine-detail')
        if table:
            # Iterate over all table cells
            for td in table.find_all('td'):
                # Check which icon class exists in this cell
                span = td.find('span', class_='engine-icon')
                if span:
                    # Check if the span has one of our target classes
                    classes = span.get('class', [])
                    
                    label = "Unknown"
                    for c in classes:
                        if c in class_map:
                            label = class_map[c]
                            break
                    
                    # Get the value from the <p> tag
                    value_p = td.find('p')
                    if value_p:
                        # Clean up text (remove newlines and extra spaces)
                        table_data[label] = value_p.get_text(strip=True)
        
        extracted_data['specs'] = table_data
    except Exception:
        extracted_data['specs'] = {}

    # ---------------------------------------------------------
    # 3. Featured List (Registered In, Color, Assembly, etc.)
    # ---------------------------------------------------------
    # Logic: The list alternates. <li class="ad-data">Key</li> -> <li>Value</li>
    featured_data = {}
    try:
        ul_list = soup.find('ul', class_='ul-featured')
        if ul_list:
            all_items = ul_list.find_all('li')
            
            # We iterate through the list. If we find a key, we look at the next item for the value
            current_key = None
            
            for li in all_items:
                # Check if this li is a label (has class 'ad-data')
                if 'ad-data' in li.get('class', []):
                    current_key = li.get_text(strip=True)
                elif current_key:
                    # This is the value associated with the previous key
                    value = li.get_text(strip=True)
                    featured_data[current_key] = value
                    current_key = None # Reset for next pair
        
        extracted_data['details'] = featured_data
    except Exception:
        extracted_data['details'] = {}

    # ---------------------------------------------------------
    # 4. Car Features (Accordion)
    # ---------------------------------------------------------
    # Scrapes categories (Interior, Safety, etc.) and their specific items
    features_data = {}
    try:
        accordion = soup.find('div', id='featuresAccordion')
        if accordion:
            # Find all groups (Interior, Safety, etc.)
            groups = accordion.find_all('div', class_='accordion-group')
            
            for group in groups:
                # Get the Category Name (e.g., Interior)
                heading = group.find('h3', class_='accordion-toggle')
                category_name = heading.get_text(strip=True) if heading else "Other"
                
                # Get the items in this category
                items = []
                list_ul = group.find('ul', class_='car-feature-list')
                if list_ul:
                    for li in list_ul.find_all('li'):
                        items.append(li.get_text(strip=True))
                
                if items:
                    features_data[category_name] = items

        extracted_data['features'] = features_data
    except Exception:
        extracted_data['features'] = {}

    # ---------------------------------------------------------
    # 5. Seller Comments
    # ---------------------------------------------------------
    # Logic: Find the specific label, go to its parent, extract text, remove label text
    try:
        # Find the label with the specific class
        tip_label = soup.find('label', class_='detail-tip')
        
        if tip_label:
            # The parent div contains the comment text AND the label text
            parent_div = tip_label.parent
            
            # Get the full text of the parent
            full_text = parent_div.get_text(strip=True)
            
            # Get the text of the label
            label_text = tip_label.get_text(strip=True)
            
            # Remove the label text from the full text to get just the comment
            comment = full_text.replace(label_text, '').strip()
            
            extracted_data['seller_comments'] = comment
        else:
            extracted_data['seller_comments'] = ""
            
    except Exception:
        extracted_data['seller_comments'] = ""

    return extracted_data

# ==========================================
# TEST EXECUTION
# ==========================================

# Assuming the HTML string provided in your prompt is stored in 'html_source'
# For this example, I will assume valid HTML input based on your prompt.

# You would load your file or scraped text here:
# html_source = scraper.html.text 
# data = extract_car_data(html_source)

# ------------------------------------------
# Demonstration with the specific HTML provided in prompt
# ------------------------------------------
html_source = """
<div class="col-md-8">
   <div class="well" id="scroll_car_info">
      <h1>Suzuki Cultus VXRi (CNG) 2010</h1>
      <table width="100%" class="table table-bordered text-center table-engine-detail fs16">
         <tbody>
            <tr>
               <td><span class="engine-icon year"></span><p>2010</p></td>
               <td><span class="engine-icon millage"></span><p>144,000 km</p></td>
               <td><span class="engine-icon type"></span><p>Petrol</p></td>
               <td><span class="engine-icon transmission"></span><p>Manual</p></td>
            </tr>
         </tbody>
      </table>
      <ul class="list-unstyled ul-featured clearfix" id="scroll_car_detail">
         <li class="ad-data">Registered In</li>
         <li>Karachi</li>
         <li class="ad-data">Color</li>
         <li>Graphite Grey</li>
         <li class="ad-data">Assembly</li>
         <li>Local</li>
         <li class="ad-data">Engine Capacity</li>
         <li>1000 cc</li>
         <li class="ad-data">Body Type</li>
         <li><a href="#">Hatchback</a></li>
         <li class="ad-data">Last Updated:</li>
         <li>Dec 06, 2025</li>
         <li class="ad-data">Ad Ref #</li>
         <li>10905404</li>
      </ul>
      <div class="faqs">
          <div class="accordion" id="featuresAccordion">
             <div class="accordion-group">
                <h3>Interior</h3>
                <ul class="car-feature-list"><li>Infotainment System</li><li>Front Speakers</li></ul>
             </div>
          </div>
      </div>
      <div>
         Suzuki cultus 2010 in extra vagent condition iner  percent original outside shower for fresh look like a new car with extra ordinary interior and exterior chilled ac transfer is mandatory
         <label class="detail-tip show">Mention PakWheels.com when calling Seller to get a good deal</label>
      </div>
   </div>
</div>
"""

# Run the function
result = extract_car_data(html_source)

# Print Result formatted as JSON
print(json.dumps(result, indent=4))