import time
import json
import re
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from collections import defaultdict
from datetime import datetime
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Define the categories we want to track
DESIRED_CATEGORIES = {
    "Python",
    "C#",
    "Java",
    "JavaScript/TypeScript",
    "Microsoft Copilot Studio",
    "Microsoft 365 Agents SDK",
    "Azure AI Agent Service"
}

def setup_driver():
    """Set up and return a configured Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return webdriver.Chrome(options=chrome_options)

def ensure_output_folder():
    """Create output folder if it doesn't exist"""
    folders = ['output', 'progress']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
    return 'output'

def get_timestamp():
    """Get current timestamp for file naming"""
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def load_progress():
    """Load the latest progress data"""
    ensure_output_folder()  # Make sure folders exist before trying to read
    progress_file = 'progress/scraping_progress.json'
    
    if not os.path.exists(progress_file):
        return {
            'last_page': 1,
            'processed_urls': set(),
            'categories_data': defaultdict(list)
        }
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return {
                'last_page': data.get('last_page', 1),
                'processed_urls': set(data.get('processed_urls', [])),
                'categories_data': defaultdict(list, data.get('categories_data', {}))
            }
    except Exception as e:
        print(f"Error loading progress file: {e}")
        return {
            'last_page': 1,
            'processed_urls': set(),
            'categories_data': defaultdict(list)
        }

def save_progress(last_page, processed_urls, categories_data):
    """Save current progress"""
    ensure_output_folder()  # Make sure folders exist before trying to write
    progress_data = {
        'last_page': last_page,
        'processed_urls': list(processed_urls),
        'categories_data': dict(categories_data),
        'timestamp': get_timestamp()
    }
    
    try:
        with open('progress/scraping_progress.json', 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving progress: {e}")

def extract_issue_number(url):
    """Extract issue number from GitHub issue URL"""
    match = re.search(r'/issues/(\d+)', url)
    return int(match.group(1)) if match else None

def remove_duplicates(categories):
    """Remove duplicates from each category while preserving the most recent issues"""
    for category, urls in categories.items():
        # Create a dictionary with issue numbers as keys and full URLs as values
        issue_dict = {}
        for url in urls:
            issue_num = extract_issue_number(url)
            if issue_num:
                issue_dict[issue_num] = url
        
        # Sort by issue number (higher numbers are more recent) and get unique URLs
        sorted_unique_urls = [issue_dict[num] for num in sorted(issue_dict.keys(), reverse=True)]
        categories[category] = sorted_unique_urls
    
    return categories

def extract_projects_from_page(html_content):
    """Extract all projects from the page HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    projects = []
    
    # Find all issue rows
    issue_rows = soup.find_all('div', class_='IssueRow-module__row--XmR1f')
    
    for row in issue_rows:
        try:
            # Get the title and URL
            title_element = row.find('a', class_='IssuePullRequestTitle-module__ListItemTitle_1--_xOfg')
            if title_element:
                url = f"https://github.com{title_element['href']}"
                projects.append({"url": url})
        except Exception as e:
            print(f"Error processing a project: {str(e)}")
            continue
    
    return projects

def get_project_categories(driver, url):
    """Extract categories from an issue page"""
    try:
        print(f"\nExtracting categories from: {url}")
        driver.get(url)
        
        # Get the page source
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        categories = []
        
        # Find the language section
        for h3 in soup.find_all('h3'):
            if 'Language & Framework' in h3.text:
                # Find all task list items
                task_items = soup.find_all('div', class_='TaskListItem-module__task-list-item--hncv0')
                for item in task_items:
                    checkbox = item.find('input', type='checkbox')
                    text_div = item.find('div', class_='TaskListItem-module__task-list-html--PQxW3')
                    
                    if checkbox and text_div:
                        lang_name = text_div.text.strip()
                        is_checked = checkbox.has_attr('checked')
                        
                        # Only add if it's one of our desired categories and is checked
                        if is_checked and lang_name in DESIRED_CATEGORIES:
                            categories.append(lang_name)
                break
        
        return categories
        
    except Exception as e:
        print(f"Error getting categories for {url}: {e}")
        return []

def process_projects(projects, categories_data, processed_urls, current_page):
    """Process projects and categorize them"""
    driver = setup_driver()
    try:
        total_projects = len(projects)
        processed_count = 0
        
        for project in projects:
            url = project['url']
            
            # Skip if already processed
            if url in processed_urls:
                print(f"\nSkipping already processed URL: {url}")
                continue
            
            print(f"\nProcessing project {processed_count + 1}/{total_projects}")
            
            # Get categories for this project
            categories = get_project_categories(driver, url)
            
            # Add URL to each category
            for category in categories:
                categories_data[category].append(url)
            
            # Mark as processed
            processed_urls.add(url)
            processed_count += 1
            
            # Save progress every 5 projects
            if processed_count % 5 == 0:
                save_progress_and_stats(categories_data, processed_urls, current_page)
            
            time.sleep(1)  # Small delay between requests
            
    except Exception as e:
        print(f"Error during processing: {e}")
    finally:
        driver.quit()
    
    return processed_count

def save_progress_and_stats(categories_data, processed_urls, current_page):
    """Save both progress and statistics"""
    # Save progress
    save_progress(current_page, processed_urls, categories_data)
    
    # Calculate and save statistics
    timestamp = get_timestamp()
    output_folder = ensure_output_folder()
    
    # Remove duplicates
    categories_data = remove_duplicates(categories_data)
    
    # Calculate statistics
    category_counts = {category: len(urls) for category, urls in categories_data.items()}
    total_issues = sum(category_counts.values())
    
    # Print statistics
    print("\nCurrent statistics:")
    print(f"Total processed URLs: {len(processed_urls)}")
    for category, count in sorted(category_counts.items()):
        print(f"{category}: {count} issues")
    
    # Save categorized issues
    categorized_issues = {
        "categories": dict(categories_data),
        "metadata": {
            "timestamp": timestamp,
            "last_page": current_page,
            "total_processed": len(processed_urls),
            "category_counts": category_counts,
            "total_unique_issues": total_issues
        }
    }
    
    try:
        with open(os.path.join(output_folder, f'categorized_issues_{timestamp}.json'), 'w', encoding='utf-8') as f:
            json.dump(categorized_issues, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving statistics: {e}")

def main():
    # Make sure output folders exist
    ensure_output_folder()
    
    # Load previous progress
    progress = load_progress()
    current_page = progress['last_page']
    processed_urls = progress['processed_urls']
    categories_data = progress['categories_data']
    
    print(f"Resuming from page {current_page}")
    print(f"Already processed {len(processed_urls)} URLs")
    
    driver = setup_driver()
    try:
        # Scrape pages 1-50
        for page in range(current_page, 51):
            current_page = page
            print(f"\nProcessing page {page}/50...")
            url = f"https://github.com/microsoft/AI_Agents_Hackathon/issues?page={page}"
            
            try:
                # Load the page
                driver.get(url)
                
                # Wait for content to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "IssueRow-module__row--XmR1f"))
                )
                
                # Extract projects from the page
                page_projects = extract_projects_from_page(driver.page_source)
                
                if not page_projects:
                    print(f"No more projects found on page {page}. Stopping pagination.")
                    break
                    
                print(f"Found {len(page_projects)} projects on page {page}")
                
                # Process the projects from this page
                processed_count = process_projects(page_projects, categories_data, processed_urls, current_page)
                print(f"Processed {processed_count} new projects from page {page}")
                
                # Save progress after each page
                save_progress_and_stats(categories_data, processed_urls, current_page)
                
                # Add a small delay between pages
                time.sleep(2)
                
            except TimeoutException:
                print(f"Timeout on page {page}. Moving to next page.")
                continue
            except Exception as e:
                print(f"Error processing page {page}: {e}")
                # Save progress before moving to next page
                save_progress_and_stats(categories_data, processed_urls, current_page)
                continue
            
    finally:
        driver.quit()
    
    # Final save
    save_progress_and_stats(categories_data, processed_urls, current_page)
    print("\nScraping completed!")
    print(f"Total processed URLs: {len(processed_urls)}")

if __name__ == "__main__":
    main() 