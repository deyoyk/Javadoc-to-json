
import argparse
import json
import re
import sys
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


@dataclass
class Parameter:
    name: str
    type: str
    description: Optional[str] = None


@dataclass
class Method:
    name: str
    return_type: str
    parameters: List[Parameter]
    description: str
    modifiers: List[str]
    exceptions: List[str]
    class_name: str
    package_name: str
    url: str


@dataclass
class APIClass:
    name: str
    package_name: str
    description: str
    methods: List[Method]
    url: str
    type: str  


class JavadocParser:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_page(self, url: str) -> BeautifulSoup:
        """Fetch and parse a web page"""
        response = self.session.get(url)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')

    def extract_package_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract package links from the main Javadoc page"""
        package_links = []
        
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.endswith('package-summary.html'):
                
                base_url_with_slash = self.base_url if self.base_url.endswith('/') else self.base_url + '/'
                full_url = urljoin(base_url_with_slash, href)
                package_links.append(full_url)
        
        
        summary_table = soup.find('div', class_='summary-table')
        if summary_table:
            for link in summary_table.find_all('a', href=True):
                href = link['href']
                if href.endswith('package-summary.html'):
                    base_url_with_slash = self.base_url if self.base_url.endswith('/') else self.base_url + '/'
                    full_url = urljoin(base_url_with_slash, href)
                    package_links.append(full_url)
        
        
        for table in soup.find_all('table'):
            for link in table.find_all('a', href=True):
                href = link['href']
                if '/package-summary.html' in href or href.endswith('package-summary.html'):
                    base_url_with_slash = self.base_url if self.base_url.endswith('/') else self.base_url + '/'
                    full_url = urljoin(base_url_with_slash, href)
                    package_links.append(full_url)
        
        return list(set(package_links))

    def extract_class_links_from_package(self, package_url: str) -> List[str]:
        """Extract class links from a package summary page"""
        soup = self.get_page(package_url)
        class_links = []
        
        
        
        for table in soup.find_all('table'):
            for link in table.find_all('a', href=True):
                href = link['href']
                if href.endswith('.html') and not href.endswith('package-summary.html'):
                    class_links.append(urljoin(package_url, href))
        
        
        for ul in soup.find_all('ul'):
            for link in ul.find_all('a', href=True):
                href = link['href']
                if href.endswith('.html') and not href.endswith('package-summary.html'):
                    class_links.append(urljoin(package_url, href))
        
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if (href.endswith('.html') and 
                not href.endswith('package-summary.html') and
                not href.startswith('http') and
                '/' not in href.replace('.html', '')):  
                class_links.append(urljoin(package_url, href))
        
        return list(set(class_links))  

    def parse_method_signature(self, signature_text: str) -> Dict:
        """Parse method signature to extract return type, name, and parameters"""
        signature_text = signature_text.strip()
        
        
        if '(' not in signature_text or ')' not in signature_text:
            return None
        
        
        
        if signature_text.count(' ') == 1 and '(' in signature_text:
            
            pass
        
        elif signature_text.strip() and not any(modifier in signature_text for modifier in ['public', 'private', 'protected', 'static']):
            
            if signature_text.split('(')[0].strip().split()[-1].title() == signature_text.split('(')[0].strip().split()[-1]:
                return None
        
        
        modifiers = []
        modifier_pattern = r'\b(public|private|protected|static|final|abstract|synchronized|native|default)\b'
        modifiers = re.findall(modifier_pattern, signature_text)
        
        
        signature_clean = re.sub(modifier_pattern, '', signature_text).strip()
        
        
        paren_index = signature_clean.find('(')
        if paren_index == -1:
            return None
        
        
        before_params = signature_clean[:paren_index].strip()
        params_str = signature_clean[paren_index+1:signature_clean.rfind(')')].strip()
        
        
        parts = before_params.split()
        if len(parts) < 2:
            return None
        
        method_name = parts[-1]
        return_type = ' '.join(parts[:-1])
        
        
        parameters = []
        if params_str.strip():
            
            param_parts = self._split_parameters(params_str)
            for param in param_parts:
                param = param.strip()
                if param:
                    
                    param_words = param.split()
                    if len(param_words) >= 2:
                        param_name = param_words[-1]
                        param_type = ' '.join(param_words[:-1])
                        parameters.append(Parameter(
                            name=param_name.strip(),
                            type=param_type.strip()
                        ))
        
        return {
            'return_type': return_type.strip(),
            'name': method_name,
            'parameters': parameters,
            'modifiers': modifiers
        }
    
    def _split_parameters(self, params_str: str) -> List[str]:
        """Split parameter string handling generics and nested types"""
        parameters = []
        current_param = ""
        bracket_depth = 0
        
        for char in params_str:
            if char == '<':
                bracket_depth += 1
            elif char == '>':
                bracket_depth -= 1
            elif char == ',' and bracket_depth == 0:
                if current_param.strip():
                    parameters.append(current_param.strip())
                current_param = ""
                continue
            
            current_param += char
        
        if current_param.strip():
            parameters.append(current_param.strip())
        
        return parameters

    def extract_methods_from_class(self, class_url: str) -> List[Method]:
        """Extract all methods from a class documentation page"""
        soup = self.get_page(class_url)
        methods = []
        
        
        package_name = ""
        class_name = ""
        
        
        title_elem = soup.find('title')
        if title_elem:
            title = title_elem.get_text()
            parts = title.split('(')
            if parts:
                class_name = parts[0].strip().split()[-1]
        
        
        header_h2 = soup.find('h2', class_='title')
        if header_h2 and not class_name:
            header_text = header_h2.get_text(strip=True)
            
            words = header_text.split()
            if len(words) >= 2:
                class_name = words[-1]
        
        
        url_path = urlparse(class_url).path
        path_parts = url_path.split('/')
        package_parts = []
        for i, part in enumerate(path_parts):
            if part.endswith('.html'):
                
                package_parts = [p for p in path_parts[:i] if p and p != '..']
                break
        if package_parts:
            package_name = '.'.join(package_parts[-4:])  
        
        
        header = soup.find('div', class_='header') or soup.find('div', class_='topNav')
        if header:
            package_link = header.find('a', href=lambda x: x and 'package-summary' in x)
            if package_link:
                package_name = package_link.get_text(strip=True)
        
        
        if not package_name:
            subtitle = soup.find('div', class_='sub-title')
            if subtitle:
                
                package_link = subtitle.find('a')
                if package_link:
                    package_name = package_link.get_text(strip=True)
                else:
                    package_name = subtitle.get_text(strip=True).replace('Package', '').strip()
        
        
        
        
        summary_table = soup.find('div', class_='summary-table')
        if summary_table:
            
            method_rows = summary_table.find_all('div', class_='col-second')
            for method_cell in method_rows:
                code_elem = method_cell.find('code')
                if code_elem:
                    
                    method_link = code_elem.find('a', class_='member-name-link')
                    if method_link:
                        method_text = code_elem.get_text(strip=True)
                        
                        
                        return_type = ""
                        col_first = method_cell.find_previous_sibling('div', class_='col-first')
                        if col_first:
                            return_type = col_first.get_text(strip=True)
                        
                        
                        if return_type and '(' in method_text:
                            
                            method_text_clean = re.sub(r'\s+', ' ', method_text).strip()
                            full_signature = f"{return_type} {method_text_clean}"
                            parsed = self.parse_method_signature(full_signature)
                            
                            if parsed:
                                
                                description = ""
                                col_last = method_cell.find_next_sibling('div', class_='col-last')
                                if col_last:
                                    desc_div = col_last.find('div', class_='block')
                                    if desc_div:
                                        description = desc_div.get_text(strip=True)
                                
                                method = Method(
                                    name=parsed['name'],
                                    return_type=parsed['return_type'],
                                    parameters=parsed['parameters'],
                                    description=description,
                                    modifiers=parsed['modifiers'],
                                    exceptions=[],
                                    class_name=class_name,
                                    package_name=package_name,
                                    url=class_url
                                )
                                methods.append(method)
        
        
        for table in soup.find_all('table'):
            
            header_cells = table.find_all('th')
            if any('method' in th.get_text().lower() for th in header_cells):
                for row in table.find_all('tr')[1:]:  
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        methods.extend(self._extract_method_from_row(cells, class_name, package_name, class_url))
        
        
        method_details = soup.find_all(['div', 'section'], class_=lambda x: x and 'detail' in x.lower())
        for detail in method_details:
            if 'method' in detail.get('class', [''])[0].lower():
                methods.extend(self._extract_method_from_detail(detail, class_name, package_name, class_url))
        
        
        for member_sig in soup.find_all('div', class_='member-signature'):
            
            return_type_elem = member_sig.find('span', class_='return-type')
            element_name_elem = member_sig.find('span', class_='element-name')
            parameters_elem = member_sig.find('span', class_='parameters')
            
            if element_name_elem:
                method_name = element_name_elem.get_text(strip=True)
                return_type = return_type_elem.get_text(strip=True) if return_type_elem else 'void'
                params_str = parameters_elem.get_text(strip=True) if parameters_elem else '()'
                
                
                full_signature = f"{return_type} {method_name}{params_str}"
                parsed = self.parse_method_signature(full_signature)
                
                if parsed:
                    
                    description = ""
                    section = member_sig.find_parent('section', class_='detail')
                    if section:
                        block_div = section.find('div', class_='block')
                        if block_div:
                            description = block_div.get_text(strip=True)
                    
                    method = Method(
                        name=parsed['name'],
                        return_type=parsed['return_type'],
                        parameters=parsed['parameters'],
                        description=description,
                        modifiers=parsed['modifiers'],
                        exceptions=[],
                        class_name=class_name,
                        package_name=package_name,
                        url=class_url
                    )
                    methods.append(method)
        
        
        for pre in soup.find_all('pre'):
            text = pre.get_text(strip=True)
            if '(' in text and ')' in text and len(text) > 10:
                
                cleaned_text = re.sub(r'<[^>]+>', '', str(pre))
                temp_soup = BeautifulSoup(cleaned_text, 'html.parser')
                cleaned_text = temp_soup.get_text(strip=True)
                
                parsed = self.parse_method_signature(cleaned_text)
                if parsed:
                    
                    description = ""
                    next_elem = pre.find_next_sibling('div', class_='block')
                    if next_elem:
                        description = next_elem.get_text(strip=True)
                    
                    method = Method(
                        name=parsed['name'],
                        return_type=parsed['return_type'],
                        parameters=parsed['parameters'],
                        description=description,
                        modifiers=parsed['modifiers'],
                        exceptions=[],
                        class_name=class_name,
                        package_name=package_name,
                        url=class_url
                    )
                    methods.append(method)
        
        
        for dl in soup.find_all('dl'):
            dt_elements = dl.find_all('dt')
            for dt in dt_elements:
                member_link = dt.find('span', class_='memberNameLink')
                if member_link:
                    link = member_link.find('a')
                    if link:
                        method_text = link.get_text(strip=True)
                        if '(' in method_text and ')' in method_text:
                            
                            
                            
                            parsed = self.parse_method_signature(f"void {method_text}")  
                            
                            if parsed:
                                
                                description = ""
                                next_dd = dt.find_next_sibling('dd')
                                if next_dd:
                                    description = next_dd.get_text(strip=True)
                                
                                method = Method(
                                    name=parsed['name'],
                                    return_type=parsed['return_type'],
                                    parameters=parsed['parameters'],
                                    description=description,
                                    modifiers=parsed['modifiers'],
                                    exceptions=[],
                                    class_name=class_name,
                                    package_name=package_name,
                                    url=class_url
                                )
                                methods.append(method)
        
        
        for code in soup.find_all('code'):
            text = code.get_text(strip=True)
            if '(' in text and ')' in text and len(text) > 10:
                parsed = self.parse_method_signature(text)
                if parsed:
                    
                    description = ""
                    parent = code.parent
                    if parent:
                        desc = parent.get_text(strip=True)
                        description = desc.replace(text, '').strip()[:200]  
                    
                    method = Method(
                        name=parsed['name'],
                        return_type=parsed['return_type'],
                        parameters=parsed['parameters'],
                        description=description,
                        modifiers=parsed['modifiers'],
                        exceptions=[],
                        class_name=class_name,
                        package_name=package_name,
                        url=class_url
                    )
                    methods.append(method)
        
        return list({m.name: m for m in methods}.values())  
    
    def _extract_method_from_row(self, cells, class_name, package_name, class_url):
        """Helper to extract method from table row"""
        methods = []
        for cell in cells:
            code_elem = cell.find('code')
            if code_elem:
                signature = code_elem.get_text(strip=True)
                parsed = self.parse_method_signature(signature)
                if parsed:
                    description = cell.get_text(strip=True).replace(signature, '').strip()
                    method = Method(
                        name=parsed['name'],
                        return_type=parsed['return_type'],
                        parameters=parsed['parameters'],
                        description=description[:200],
                        modifiers=parsed['modifiers'],
                        exceptions=[],
                        class_name=class_name,
                        package_name=package_name,
                        url=class_url
                    )
                    methods.append(method)
        return methods
    
    def _extract_method_from_detail(self, detail, class_name, package_name, class_url):
        """Helper to extract method from detail section"""
        methods = []
        for code in detail.find_all('code'):
            text = code.get_text(strip=True)
            parsed = self.parse_method_signature(text)
            if parsed:
                description = detail.get_text(strip=True).replace(text, '').strip()[:200]
                method = Method(
                    name=parsed['name'],
                    return_type=parsed['return_type'],
                    parameters=parsed['parameters'],
                    description=description,
                    modifiers=parsed['modifiers'],
                    exceptions=[],
                    class_name=class_name,
                    package_name=package_name,
                    url=class_url
                )
                methods.append(method)
        return methods

    def extract_all_apis(self) -> List[APIClass]:
        """Extract all APIs from the Javadoc website"""
        print(f"Fetching main page: {self.base_url}")
        main_soup = self.get_page(self.base_url)
        
        
        package_links = self.extract_package_links(main_soup)
        
        if not package_links:
            
            print("No packages found, looking for direct class links...")
            class_links = []
            for link in main_soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.html') and not href.endswith('index.html'):
                    class_links.append(urljoin(self.base_url, href))
        else:
            print(f"Found {len(package_links)} packages")
            class_links = []
            for package_url in package_links[:20]:  
                print(f"Processing package: {package_url}")
                try:
                    new_links = self.extract_class_links_from_package(package_url)
                    class_links.extend(new_links)
                    print(f"  Found {len(new_links)} classes in this package")
                except Exception as e:
                    print(f"Error processing package {package_url}: {e}")
        
        api_classes = []
        print(f"Found {len(class_links)} classes to process")
        
        for class_url in class_links[:50]:  
            print(f"Processing class: {class_url}")
            try:
                methods = self.extract_methods_from_class(class_url)
                if methods:
                    
                    first_method = methods[0]
                    api_class = APIClass(
                        name=first_method.class_name,
                        package_name=first_method.package_name,
                        description=f"Class from {first_method.package_name}",
                        methods=methods,
                        url=class_url,
                        type="class"
                    )
                    api_classes.append(api_class)
            except Exception as e:
                print(f"Error processing class {class_url}: {e}")
        
        return api_classes


def main():
    parser = argparse.ArgumentParser(
        description="Extract methods and APIs from Javadoc websites and convert to JSON"
    )
    parser.add_argument("url", help="URL of the Javadoc website")
    parser.add_argument("-o", "--output", help="Output JSON file (default: stdout)")
    parser.add_argument("--pretty", action="store_true", help="Pretty print JSON output")
    
    args = parser.parse_args()
    
    try:
        javadoc_parser = JavadocParser(args.url)
        api_classes = javadoc_parser.extract_all_apis()
        
        
        result = {
            "source_url": args.url,
            "total_classes": len(api_classes),
            "total_methods": sum(len(cls.methods) for cls in api_classes),
            "classes": [asdict(cls) for cls in api_classes]
        }
        
        
        if args.pretty:
            json_output = json.dumps(result, indent=2, default=str)
        else:
            json_output = json.dumps(result, default=str)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(json_output)
            print(f"Output written to {args.output}")
        else:
            print(json_output)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
