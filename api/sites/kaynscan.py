import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
from api.services import get_selenium_driver 
import threading

# Simple in-memory cache for chapter pages
_chapter_cache = {}
_cache_timeout = 3600  # 1 hour cache timeout

# Cache for search results (home page)
_search_cache = {}
_search_cache_timeout = 1800  # 30 minutes for search

# Cache for browse results
_browse_cache = {}
_browse_cache_timeout = 3600  # 1 hour for browse results

def browse_all_manga(page=1):
    """Browse all manga from AsuraScans browse pages"""
    base_url = "https://asurascans.com"
    all_manga = []
    
    try:
        # Scrape the specific browse page
        browse_url = f"{base_url}/browse"
        if page > 1:
            browse_url += f"?page={page}"
            
        print(f"Scraping browse page {page}: {browse_url}")
        
        response = requests.get(browse_url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: Print page title and some structure
            page_title = soup.find('title')
            print(f"Page title: {page_title.get_text() if page_title else 'No title found'}")
            
            # Try to find manga items specific to browse pages
            manga_list = []
            
            # Try browse-specific selectors first
            browse_selectors = [
                'div.bsx a',  # Common for browse pages
                'div.manga-poster a',
                'div.manga-cover a', 
                'div.manga-item a',
                'article.post-item a',
                'div.bixbox a',
                'div.listupd a',
                'div.utao a'
            ]
            
            print("Trying browse-specific selectors...")
            for selector in browse_selectors:
                items = soup.select(selector)
                if items:
                    print(f"Found {len(items)} items with selector: {selector}")
                    for item in items:
                        manga_data = extract_manga_data_from_item(item, base_url)
                        if manga_data:
                            manga_list.append(manga_data)
                    break  # Stop at first successful selector
            
            # If no browse-specific selectors worked, try the general function
            if not manga_list:
                print("Trying general extract_manga_from_soup...")
                manga_list = extract_manga_from_soup(soup, base_url)
            
            print(f"Found {len(manga_list)} manga on browse page {page}")
            
            # Debug: Print first few manga
            if manga_list:
                print(f"Sample manga from page {page}:")
                for i, manga in enumerate(manga_list[:3]):
                    print(f"  {i+1}. {manga.get('title', 'No title')} - {manga.get('id', 'No ID')}")
            else:
                # Debug: Show some HTML structure
                print("DEBUG - No manga found. Showing page structure...")
                all_links = soup.find_all('a', href=True)
                print(f"Total links found: {len(all_links)}")
                for i, link in enumerate(all_links[:10]):
                    print(f"  {i+1}. {link.get_text(strip=True)[:50]} -> {link.get('href')}")
            
            return {
                'manga': manga_list,
                'page': page,
                'total_on_page': len(manga_list)
            }
        else:
            print(f"Failed to fetch browse page {page}: Status {response.status_code}")
            return {'manga': [], 'page': page, 'total_on_page': 0}
            
    except Exception as e:
        print(f"Error scraping browse page {page}: {str(e)}")
        return {'manga': [], 'page': page, 'total_on_page': 0}

def extract_manga_data_from_item(item, base_url):
    """Extract manga data from a single item element"""
    try:
        title = item.get_text(strip=True)
        link = item.get('href')
        img_elem = item.select_one('img')
        
        # Clean up title
        title = title.replace('\n', ' ').replace('\t', ' ').strip()
        
        if title and len(title) > 2 and link:
            # Convert relative URL to absolute
            if link and not link.startswith('http'):
                if link.startswith('/'):
                    link = base_url + link
                else:
                    link = base_url + '/' + link
            
            cover_url = img_elem.get('src') if img_elem else None
            if cover_url and not cover_url.startswith('http'):
                if cover_url.startswith('/'):
                    cover_url = base_url + cover_url
                else:
                    cover_url = base_url + '/' + cover_url
            
            # Extract ID from URL
            manga_id = link.split('/')[-1] if link else ''
            
            return {
                'id': manga_id,
                'title': title,
                'url': link,
                'cover_url': cover_url,
                'cover': cover_url
            }
    except Exception as e:
        print(f"Error extracting manga data: {str(e)}")
    
    return None

def get_all_browse_manga():
    """Get all manga from all browse pages (1-17) - OPTIMIZED"""
    # Check cache first
    cache_key = "all_browse_manga"
    current_time = time.time()
    
    if cache_key in _browse_cache:
        cached_data, cached_time = _browse_cache[cache_key]
        if current_time - cached_time < _browse_cache_timeout:
            print("Browse cache hit - returning cached data")
            return cached_data
    
    print("Cache miss - scraping all browse pages...")
    all_manga = []
    base_url = "https://asurascans.com"
    
    try:
        # Use concurrent requests to speed up scraping
        import concurrent.futures
        
        def scrape_page(page_num):
            """Scrape a single page"""
            try:
                browse_url = f"{base_url}/browse"
                if page_num > 1:
                    browse_url += f"?page={page_num}"
                
                response = requests.get(browse_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                })
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    manga_list = extract_manga_from_soup(soup, base_url)
                    return page_num, manga_list
                else:
                    print(f"Failed to fetch page {page_num}: {response.status_code}")
                    return page_num, []
            except Exception as e:
                print(f"Error scraping page {page_num}: {str(e)}")
                return page_num, []
        
        # Scrape pages concurrently (max 5 at a time to be respectful)
        max_pages = 17
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_page = {executor.submit(scrape_page, page): page for page in range(1, max_pages + 1)}
            
            for future in concurrent.futures.as_completed(future_to_page):
                page_num, manga_list = future.result()
                if manga_list:
                    all_manga.extend(manga_list)
                    print(f"Page {page_num}: Found {len(manga_list)} manga")
                else:
                    print(f"Page {page_num}: No manga found")
        
        print(f"Total manga scraped: {len(all_manga)}")
        
        # Remove duplicates based on ID or title
        unique_manga = []
        seen_ids = set()
        seen_titles = set()
        
        for manga in all_manga:
            manga_id = manga.get('id', '')
            title = manga.get('title', '').lower().strip()
            
            # Use both ID and title for deduplication
            identifier = manga_id if manga_id else title
            
            if identifier and identifier not in seen_ids and title not in seen_titles:
                seen_ids.add(identifier)
                seen_titles.add(title)
                unique_manga.append(manga)
        
        print(f"After deduplication: {len(unique_manga)} unique manga")
        
        result = {
            'manga': unique_manga,
            'total_pages': max_pages,
            'total_manga': len(unique_manga)
        }
        
        # Cache the result
        _browse_cache[cache_key] = (result, current_time)
        
        return result
        
    except Exception as e:
        print(f"Error in get_all_browse_manga: {str(e)}")
        return {'manga': [], 'total_pages': 0, 'total_manga': 0}

def search(query, page=1):
    """Search for manga on AsuraScans"""
    # Check cache first for common home page queries
    cache_key = f"{query}_{page}"
    current_time = time.time()
    
    if query in ['a', 'the', ''] and cache_key in _search_cache:
        cached_data, cached_time = _search_cache[cache_key]
        if current_time - cached_time < _search_cache_timeout:
            print(f"Search cache hit for query: '{query}'")
            return cached_data
    
    base_url = "https://asurascans.com"
    
    # For specific searches like "Solo Leveling", try multiple strategies
    manga_list = []
    
    if query and query not in ['a', 'the', '']:
        # Strategy 1: Scrape the COMPLETE manga library from /comics/
        try:
            print("Scraping complete manga library...")
            response = requests.get(f"{base_url}/comics/", timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                # Get ALL manga from the library page
                all_manga = extract_all_manga_from_library(soup, base_url)
                print(f"{len(all_manga)} total in library")
                
                # Filter for query match (case-insensitive)
                filtered_manga = []
                query_lower = query.lower()
                
                for manga in all_manga:
                    if query_lower in manga['title'].lower():
                        filtered_manga.append(manga)
                
                manga_list.extend(filtered_manga)
                print(f"Found {len(filtered_manga)} manga matching '{query}'")
                
                # If we found results, return them immediately
                if len(filtered_manga) > 0:
                    result = {'manga': filtered_manga}
                    print(f"Search for '{query}' returned {len(filtered_manga)} results from library")
                    return result
                    
        except Exception as e:
            print(f"Library scraping failed: {e}")
        
        # Strategy 2: Try WordPress search (fallback)
        search_urls = [
            f"{base_url}/?s={query}",
            f"{base_url}/page/{page}/?s={query}",
            f"{base_url}/comics/?s={query}",
        ]
        
        for search_url in search_urls:
            try:
                print(f"Trying search URL: {search_url}")
                response = requests.get(search_url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    found_manga = extract_manga_from_soup(soup, base_url, query)
                    manga_list.extend(found_manga)
                    print(f"Found {len(found_manga)} manga from {search_url}")
                    
                    if len(found_manga) > 0:
                        break  # Stop if we found results
                        
            except Exception as e:
                print(f"Search failed for {search_url}: {e}")
                
    else:
        # For home page queries, scrape the library but with special handling
        try:
            print("Home page query - scraping library...")
            response = requests.get(f"{base_url}/comics/", timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                library_manga = extract_all_manga_from_library(soup, base_url)
                manga_list.extend(library_manga)
                print(f"Home page library scrape found {len(library_manga)} manga")
                
                # Debug: Print first few manga for home page
                if library_manga:
                    print("DEBUG - Home page manga samples:")
                    for i, manga in enumerate(library_manga[:3]):
                        print(f"  {i+1}. Title: '{manga['title']}' | Cover: {manga['cover_url']}")
                        
        except Exception as e:
            print(f"Home page library scrape failed: {e}")
            
            # Fallback: try homepage if library fails
            try:
                print("Falling back to homepage scrape...")
                response = requests.get(base_url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    homepage_manga = extract_manga_from_soup(soup, base_url, None)
                    manga_list.extend(homepage_manga)
                    print(f"Fallback homepage scrape found {len(homepage_manga)} manga")
                    
                    # Debug: Print first few manga from homepage
                    if homepage_manga:
                        print("DEBUG - Homepage manga samples:")
                        for i, manga in enumerate(homepage_manga[:3]):
                            print(f"  {i+1}. Title: '{manga['title']}' | Cover: {manga['cover_url']}")
                            
            except Exception as e:
                print(f"Fallback homepage scrape also failed: {e}")
    
    # Remove duplicates based on title
    seen_titles = set()
    unique_manga = []
    for manga in manga_list:
        clean_title = manga['title'].lower().strip()
        if clean_title not in seen_titles:
            seen_titles.add(clean_title)
            unique_manga.append(manga)
    
    result = {'manga': unique_manga}
    
    # Cache common home page queries
    if query in ['a', 'the', '']:
        _search_cache[cache_key] = (result, current_time)
        print(f"Cached home page results for '{query}': {len(unique_manga)} manga")
    
    print(f"Search for '{query}' returned {len(unique_manga)} results")
    return result

def extract_all_manga_from_library(soup, base_url):
    """Extract ALL manga from the library page - more comprehensive"""
    manga_list = []
    
    # Debug: Print the page title and structure
    print("DEBUG - Library page analysis:")
    title_elem = soup.select_one('title')
    if title_elem:
        print(f"  Page title: {title_elem.get_text()}")
    
    # Debug: Print page content structure
    print("DEBUG - Page structure:")
    all_links = soup.find_all('a')
    print(f"  Total links found: {len(all_links)}")
    
    comics_links = [a for a in all_links if '/comics/' in a.get('href', '')]
    print(f"  Links with /comics/: {len(comics_links)}")
    
    # Debug: Print all comics links found
    print("DEBUG - All /comics/ links found:")
    for i, link in enumerate(comics_links[:10]):  # First 10
        href = link.get('href', '')
        text = link.get_text(strip=True).replace('\n', ' ').replace('\t', ' ').strip()
        print(f"  {i+1}. Href: {href} | Text: '{text}'")
    
    # Try multiple selectors for manga items in library
    selectors = [
        'a[href*="/comics/"]',
        'div.manga-item a',
        'div.post-item a', 
        'article.manga a',
        'div.wp-manga a',
        'div.manga-wrap a',
        'div.manga-list a',
        'div.item a',
        'div.manga-archive a',
        'div.series-list a',
        'h1 a',
        'h2 a',
        'h3 a',
        '.manga-title a',
        '.series-title a'
    ]
    
    manga_items = []
    for selector in selectors:
        items = soup.select(selector)
        if items:
            manga_items.extend(items)
            print(f"Found {len(items)} items with selector: {selector}")
    
    # Debug: Print first 5 items found
    print("DEBUG - First 5 manga items found:")
    for i, item in enumerate(manga_items[:5]):
        title = item.get_text(strip=True).replace('\n', ' ').replace('\t', ' ').strip()
        link = item.get('href')
        print(f"  {i+1}. Title: '{title}' | Link: {link}")
    
    # Remove duplicates but prefer longer titles over ratings
    seen_links = {}
    for item in manga_items:
        link = item.get('href')
        title = item.get_text(strip=True).replace('\n', ' ').replace('\t', ' ').strip()
        
        if link:
            # If we haven't seen this link, store it
            if link not in seen_links:
                seen_links[link] = {'title_item': item, 'rating_item': None}
            
            # Check if this is a title (longer) or rating (shorter)
            if len(title) > 10:  # Likely a real title
                seen_links[link]['title_item'] = item
            elif re.match(r'^\d+\.\d+$', title):  # Rating
                seen_links[link]['rating_item'] = item
    
    # Combine items: use title from title_item, image from rating_item if needed
    unique_items = []
    for link, items in seen_links.items():
        title_item = items['title_item']
        rating_item = items['rating_item']
        
        # Create a combined item with title from title_item and image from rating_item
        if title_item or rating_item:
            # Use title_item as base, or rating_item if no title_item
            base_item = title_item if title_item else rating_item
            
            # If title_item exists but has no image, try to get image from rating_item
            if title_item and not title_item.select_one('img') and rating_item and rating_item.select_one('img'):
                # Copy the img from rating_item to title_item
                img = rating_item.select_one('img')
                # We'll handle this in the extraction logic below
                base_item._rating_img = img
            elif rating_item and not title_item:
                base_item._rating_img = rating_item.select_one('img')
            
            unique_items.append(base_item)
    
    print(f"After removing duplicates (preferring longer titles): {len(unique_items)} unique manga items")
    
    for item in unique_items:
        title = item.get_text(strip=True)
        link = item.get('href')
        img_elem = item.select_one('img')
        
        # If no image found, try the stored rating image
        if not img_elem and hasattr(item, '_rating_img'):
            img_elem = item._rating_img
        
        # Clean up title
        title = title.replace('\n', ' ').replace('\t', ' ').strip()
        
        # Debug: Print what we're processing
        print(f"Processing: Title='{title}' | Link='{link}' | HasImage={bool(img_elem)}")
        
        # Skip if title is too short or empty
        if not title or len(title) < 3:
            print(f"  Skipping: Title too short or empty")
            continue
            
        # Skip rating-only titles (numbers like "9.1", "8.4", etc.)
        if re.match(r'^\d+\.\d+$', title):
            print(f"  Skipping: Rating-only title")
            continue
            
        # Skip if link doesn't contain manga/comics
        if not link or ('comics/' not in link and 'manga' not in link.lower()):
            print(f"  Skipping: Link doesn't contain comics/manga")
            continue
        
        print(f"  ✓ Adding manga: {title}")
        
        cover_url = img_elem.get('src')
        
        # Convert relative URL to absolute
        if link and not link.startswith('http'):
            if link.startswith('/'):
                link = base_url + link
            else:
                link = base_url + '/' + link
        
        # Convert relative image URL to absolute
        if cover_url and not cover_url.startswith('http'):
            if cover_url.startswith('//'):
                cover_url = 'https:' + cover_url
            elif cover_url.startswith('/'):
                cover_url = base_url + cover_url
        
        # If no cover image, provide a placeholder
        if not cover_url:
            cover_url = "https://via.placeholder.com/300x450/374151/9CA3AF?text=No+Cover"
            print(f"  No cover found for {title}, using placeholder")
        
        manga_list.append({
            'title': title,
            'id': link,
            'cover_url': cover_url
        })
    
    print(f"Extracted {len(manga_list)} manga from library")
    
    # Debug: Print first 5 extracted manga
    if manga_list:
        print("DEBUG - First 5 extracted manga:")
        for i, manga in enumerate(manga_list[:5]):
            print(f"  {i+1}. {manga['title']}")
    
    # If still no manga, try a different approach - look for any text content
    if not manga_list:
        print("DEBUG - No manga found, trying alternative approach...")
        # Look for any divs that might contain manga info
        all_divs = soup.find_all('div')
        print(f"  Total divs: {len(all_divs)}")
        
        for i, div in enumerate(all_divs[:20]):  # First 20 divs
            div_text = div.get_text(strip=True).replace('\n', ' ').replace('\t', ' ').strip()
            if len(div_text) > 10 and len(div_text) < 100:  # Reasonable length for title
                print(f"  Div {i+1}: '{div_text}'")
    
    return manga_list

def extract_manga_from_soup(soup, base_url, query_filter=None):
    """Extract manga from BeautifulSoup with optional query filtering"""
    manga_list = []
    
    # Try multiple selectors for manga items - look for containers that might hold both title and image
    container_selectors = [
        'div.bs',      # Common browse container
        'div.bixbox',  # Another common container
        'div.listupd', # List update container
        'div.utao',    # Another container type
        'div.manga-poster',
        'div.manga-cover',
        'div.manga-item',
        'article.post-item'
    ]
    
    manga_containers = []
    for selector in container_selectors:
        containers = soup.select(selector)
        if containers:
            manga_containers.extend(containers)
            print(f"Found {len(containers)} containers with selector: {selector}")
    
    # If no containers found, try the old method with individual links
    if not manga_containers:
        link_selectors = [
            'a[href*="/comics/"]',
            'div.manga-item a',
            'div.post-item a',
            'article.manga a',
            'div.wp-manga a',
            'div.manga-wrap a',
            'div.manga-list a',
            'div.item a'
        ]
        
        for selector in link_selectors:
            items = soup.select(selector)
            if items:
                manga_containers.extend(items)
                print(f"Found {len(items)} items with selector: {selector}")
    
    print(f"Total containers/items to process: {len(manga_containers)}")
    
    # Debug: Print first 10 items found
    print("DEBUG - First 10 items found:")
    for i, item in enumerate(manga_containers[:10]):
        title = item.get_text(strip=True).replace('\n', ' ').replace('\t', ' ').strip()
        img = item.select_one('img')
        link = item.get('href') if hasattr(item, 'get') else None
        print(f"  {i+1}. Title: '{title}' | Has Image: {bool(img)} | Link: {link}")
    
    seen_links = {}
    
    for container in manga_containers:
        # Try to find link, title, and image within this container
        link_elem = container if container.name == 'a' else container.find('a', href=True)
        img_elem = container.select_one('img')
        
        # Get the link
        link = link_elem.get('href') if link_elem else None
        
        # Get the title - try multiple sources
        title = ""
        if container.name == 'a':
            # If container is a link, use its text
            title = container.get_text(strip=True)
        else:
            # If container is a div, look for title in various places
            title_elem = container.find('a') or container.find('h2') or container.find('h3') or container.find('.title')
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                # Fallback to container text
                title = container.get_text(strip=True)
        
        # Clean up title
        title = title.replace('\n', ' ').replace('\t', ' ').strip()
        
        # Skip if no title or title is too short
        if not title or len(title) < 3:
            continue
            
        # Skip if no link or invalid link
        if not link or ('comics/' not in link and 'manga' not in link.lower()):
            continue
        
        # For images, be more lenient - look in parent containers if not found directly
        if not img_elem:
            # Look for image in parent or sibling elements
            parent = container.parent
            if parent:
                img_elem = parent.select_one('img') or container.find_previous('img')
        
        # Skip if still no image found (but be less strict about this)
        if not img_elem:
            print(f"Warning: No image found for '{title}', but including anyway")
            # We'll add a placeholder later
        
        # Apply query filter if provided
        if query_filter and query_filter not in ['a', 'the', '']:
            if query_filter.lower() not in title.lower():
                continue
        
        # Deduplicate by link
        if link in seen_links:
            # Keep the one with longer title
            existing_title = seen_links[link]['title']
            if len(title) > len(existing_title):
                seen_links[link] = {'title': title, 'img_elem': img_elem}
        else:
            seen_links[link] = {'title': title, 'img_elem': img_elem}
    
    print(f"After deduplication: {len(seen_links)} unique manga")
    
    for link, data in seen_links.items():
        title = data['title']
        img_elem = data['img_elem']
        
        cover_url = img_elem.get('src') if img_elem else None
        
        # Convert relative URL to absolute
        if link and not link.startswith('http'):
            if link.startswith('/'):
                link = base_url + link
            else:
                link = base_url + '/' + link
        
        # Convert relative image URL to absolute
        if cover_url and not cover_url.startswith('http'):
            if cover_url.startswith('//'):
                cover_url = 'https:' + cover_url
            elif cover_url.startswith('/'):
                cover_url = base_url + cover_url
        
        # If no cover image, provide a placeholder
        if not cover_url:
            cover_url = "https://via.placeholder.com/300x450/374151/9CA3AF?text=No+Cover"
            print(f"  No cover found for {title}, using placeholder")
        
        print(f"  ✓ Adding manga: {title}")
        
        manga_list.append({
            'title': title,
            'id': link,
            'cover_url': cover_url
        })
    
    print(f"Extracted {len(manga_list)} manga from soup")
    
    # Debug: Print first 5 extracted manga
    if manga_list:
        print("DEBUG - First 5 extracted manga:")
        for i, manga in enumerate(manga_list[:5]):
            print(f"  {i+1}. {manga['title']} (Image: {bool(manga['cover_url'])})")
    
    return manga_list

def manga_info(manga_id):
    """Get chapter list for a specific manga"""
    if not manga_id:
        return []
    
    try:
        response = requests.get(manga_id, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            chapters = []
            seen_urls = set() # To prevent the duplicate Chapter 1 / Chapter 33
            
            # Target the specific list container if possible, 
            # otherwise filter the items globally
            chapter_items = soup.select('a[href*="/chapter/"]')
            
            for item in chapter_items:
                chapter_url = item.get('href')
                chapter_title = ''.join(item.find_all(text=True, recursive=False)).strip()
                
                if not chapter_title:
                    chapter_title = item.get_text(" ", strip=True).split('\n')[0]
                
                if not chapter_url:
                    continue

                # Normalize the URL
                if not chapter_url.startswith('http'):
                    chapter_url = 'https://asurascans.com' + ('' if chapter_url.startswith('/') else '/') + chapter_url

                # --- THE FIXES ---
                
                # 1. Skip if we've already added this URL (Stops duplicate Ch 1 and Ch 33)
                if chapter_url in seen_urls:
                    continue
                
                # 2. Skip the 'First Chapter' and 'Latest Chapter' buttons
                # These are usually just navigation helpers, not the list items
                if any(x in chapter_title.lower() for x in ['first chapter', 'latest chapter', 'next chapter', 'prev chapter']):
                    continue

                chapter_num = extract_chapter_number(chapter_title, chapter_url)
                
                seen_urls.add(chapter_url)
                chapters.append({
                    'id': chapter_url,
                    'title': chapter_title,
                    'number': chapter_num
                })
            
            # 3. Final Sort: Numeric descending ensures Ch 33 is at the top
            chapters.sort(key=lambda x: x['number'], reverse=True)
            return chapters

        return []
            
    except Exception as e:
        print(f"Manga info failed: {e}")
        return []


# --- NEW: GLOBAL LOCK ---
# This prevents multiple requests from spawning multiple Chrome instances
# and crashing your Railway server (OOM 503 error).
selenium_lock = threading.Lock()

def chapter_pages(chapter_id):
    if not chapter_id:
        return []

    # 1. Cache Check (Outside the lock for speed)
    current_time = time.time()
    if chapter_id in _chapter_cache:
        cached_data, cached_time = _chapter_cache[chapter_id]
        if current_time - cached_time < _cache_timeout:
            return cached_data

    # 2. Sequential Execution with Lock
    print(f"DEBUG: Request queued for: {chapter_id}")
    
    with selenium_lock:
        print(f"DEBUG: Starting Stealth Selenium for: {chapter_id}")
        driver = get_selenium_driver() 

        try:
            driver.get(chapter_id)
            
            # Brief pause for Cloudflare/Initial Load
            time.sleep(4) 
            
            # 3. FAST OPTIMIZED SCROLLING
            # Instead of a fixed 15 scrolls, we scroll only until new content stops appearing
            print("DEBUG: Executing smart scroll...")
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            for i in range(8):  # Max 8 attempts to find new height
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)  # Wait for lazy-load images
                
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    # Try one tiny "nudge" scroll to be sure
                    driver.execute_script("window.scrollBy(0, -200);")
                    time.sleep(0.5)
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    
                    # If still no change, we are done
                    if driver.execute_script("return document.body.scrollHeight") == last_height:
                        break
                
                last_height = new_height
                print(f"DEBUG: Scroll {i+1} successful, height: {last_height}")

            # 4. Extraction
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pages = extract_pages_from_soup(soup)
            
            if not pages:
                pages = extract_pages_fallback(soup)
            
            print(f"DEBUG: Successfully found {len(pages)} images")
            _chapter_cache[chapter_id] = (pages, current_time)
            return pages

        except Exception as e:
            print(f"Scraping Error: {e}")
            return []
            
        finally:
            # Crucial: Always quit the driver to free up RAM
            driver.quit()
            print(f"DEBUG: Driver closed for: {chapter_id}")
def extract_pages_from_soup(soup):
    """Extract pages from BeautifulSoup object - shared logic for both requests and Selenium"""
    print(f"DEBUG: Starting page extraction from HTML with {len(soup.select('img'))} total images")
    
    # Strip comment/social/sidebar sections before any selection
    for unwanted in soup.select(
        'div.comments, div#comments, div.comment-area, div.comment-section, '
        'div.widget, div.sidebar, aside, section.comments, '
        'div[id*="comment"], div[class*="comment"], '
        'div[id*="respond"], div[class*="respond"], '
        'div[class*="discussion"], div[id*="disqus"]'
    ):
        unwanted.decompose()

    pages = []

    # Try multiple container selectors in order of preference
    reader_containers = [
        'div.reading-content', 'div.entry-content', 'div#readerarea', 
        'div.chapter-content', 'main', 'article', 'div.post-content',
        'div.content', 'div.manga-content', 'div.chapter-body',
        'section.content', 'div.reader-area', 'div.chapter-area',
        'div.manga-reading-area', 'div.chapter-images', 'div.wp-block-group',
        'div.chapter-wrapper', 'div.manga-reader', 'div.reader-container'
    ]
    
    reader_container = None
    for container_sel in reader_containers:
        reader_container = soup.select_one(container_sel)
        if reader_container:
            print(f"DEBUG: Found container: {container_sel} with {len(reader_container.select('img'))} images")
            break

    # If no specific container found, use body but be more careful
    if not reader_container:
        reader_container = soup.find('body') or soup
        print(f"DEBUG: Using body as container with {len(reader_container.select('img'))} images")

    # Very minimal filtering - only skip obvious non-manga images
    obvious_non_manga = ['logo', 'icon', 'avatar', 'gravatar', 'emoji', 'profile', 'button', 'social', 'favicon', 'cover', 'banner', 'ad']
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}

    # Look for ALL images in the container with minimal filtering
    for img in reader_container.select('img'):
        img_url = (
            img.get('src') or
            img.get('data-src') or
            img.get('data-lazy-src') or
            img.get('data-original') or
            img.get('data-url') or
            img.get('data-lazy-original') or
            img.get('data-srcset') or
            img.get('srcset')
        )

        if not img_url or img_url.startswith('data:'):
            continue

        # Handle srcset (may contain multiple URLs)
        if 'srcset' in str(img_url).lower() and ',' in str(img_url):
            img_url = str(img_url).split(',')[0].split()[0]

        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif img_url.startswith('/'):
            img_url = 'https://asurascans.com' + img_url

        # Only skip very obvious non-manga images
        if any(kw in img_url.lower() for kw in obvious_non_manga):
            continue

        # Check extension on the path only (ignore query params)
        path = img_url.lower().split('?')[0]
        if not any(path.endswith(ext) for ext in valid_extensions):
            continue

        # Only skip very small images (under 50px)
        try:
            width = img.get('width') or img.get('data-width') or ''
            height = img.get('height') or img.get('data-height') or ''
            w = int(str(width).replace('px', '').strip() or 0)
            h = int(str(height).replace('px', '').strip() or 0)
            if (w and w < 50) or (h and h < 50):
                continue
        except (ValueError, TypeError):
            pass  # No size info, don't skip

        # Avoid duplicates
        if img_url not in pages:
            pages.append(img_url)
            print(f"DEBUG: Found page: {img_url}")

    print(f"DEBUG: Initial extraction found {len(pages)} pages")

    # If still not enough pages, try very aggressive search
    if len(pages) < 10:  # Lower threshold
        print("DEBUG: Trying aggressive search for more pages...")
        # Look for ALL images in entire document
        for img in soup.select('img'):
            img_url = img.get('src') or img.get('data-src') or img.get('data-original')
            if img_url and not img_url.startswith('data:'):
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = 'https://asurascans.com' + img_url
                
                path = img_url.lower().split('?')[0]
                if any(path.endswith(ext) for ext in valid_extensions):
                    # Only skip very obvious non-manga
                    if not any(kw in img_url.lower() for kw in ['logo', 'icon', 'avatar', 'gravatar', 'favicon']):
                        if img_url not in pages:
                            pages.append(img_url)
                            print(f"DEBUG: Aggressive search found: {img_url}")

    print(f"DEBUG: Final extraction found {len(pages)} pages")
    return pages

def extract_chapter_number(title, url):
    """Forcefully extract only the chapter number from the URL slug, ignoring trailing version numbers"""
    import re
    
    # 1. THE MOST RELIABLE WAY: Extract from the URL slug
    # Standardize the URL (remove trailing slashes)
    url_parts = url.rstrip('/').split('/')
    last_part = url_parts[-1] # e.g., '82-1' or 'chapter-82'
    
    # Step A: If the slug contains hyphens (like 82-1), 
    # we usually only want the FIRST number.
    if '-' in last_part:
        # Split by hyphen and take the first part that contains a digit
        parts = last_part.split('-')
        for p in parts:
            num_match = re.search(r'(\d+(?:\.\d+)?)', p)
            if num_match:
                return float(num_match.group(1))

    # Step B: Standard regex for slugs without hyphens
    url_number_match = re.search(r'(\d+(?:\.\d+)?)', last_part)
    if url_number_match:
        return float(url_number_match.group(1))

    # 2. FALLBACK: If URL fails, use the Title but be VERY strict
    # Use word boundaries (\b) to prevent "Chapter 82" from seeing "1 day ago"
    title_match = re.search(r'Chapter\s*\b(\d+(?:\.\d+)?)\b', title, re.IGNORECASE)
    if title_match:
        return float(title_match.group(1))

    return 0.0

def extract_pages_fallback(soup):
    """Fallback extraction with broader search for manga pages"""
    pages = []
    skip_keywords = ['logo', 'icon', 'avatar', 'banner', 'ad', 'gravatar', 'emoji', 'profile', 'thumb', 'user']
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'}
    
    # Try multiple container selectors
    containers = [
        'div.reading-content', 'div.entry-content', 'div#readerarea', 
        'div.chapter-content', 'main', 'article', 'div.post-content',
        'div.content', 'div.manga-content', 'div.chapter-body',
        'section.content', 'div.reader-area'
    ]
    
    for container_sel in containers:
        container = soup.select_one(container_sel)
        if container:
            # Look for all images in this container
            for img in container.select('img'):
                img_url = (
                    img.get('src') or img.get('data-src') or 
                    img.get('data-lazy-src') or img.get('data-original') or
                    img.get('data-url') or img.get('data-lazy-original')
                )
                
                if not img_url or img_url.startswith('data:'):
                    continue
                
                # Convert relative URLs
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = 'https://asurascans.com' + img_url
                
                # Skip obvious non-manga images
                if any(kw in img_url.lower() for kw in skip_keywords):
                    continue
                
                # Check for valid image extensions
                path = img_url.lower().split('?')[0]
                if not any(path.endswith(ext) for ext in valid_extensions):
                    continue
                
                # Skip very small images
                try:
                    width = img.get('width') or img.get('data-width') or ''
                    height = img.get('height') or img.get('data-height') or ''
                    w = int(str(width).replace('px', '').strip() or 0)
                    h = int(str(height).replace('px', '').strip() or 0)
                    if (w and w < 150) or (h and h < 150):
                        continue
                except (ValueError, TypeError):
                    pass
                
                if img_url not in pages:  # Avoid duplicates
                    pages.append(img_url)
            
            if pages:  # If we found pages in this container, break
                break
    
    # If still no pages, try searching entire document (last resort)
    if not pages:
        for img in soup.select('img[src*="/chapter/"], img[src*="page"], img[src*="manga"], img[data-src*="/chapter/"]'):
            img_url = img.get('src') or img.get('data-src')
            if img_url and not img_url.startswith('data:'):
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    img_url = 'https://asurascans.com' + img_url
                
                path = img_url.lower().split('?')[0]
                if any(path.endswith(ext) for ext in valid_extensions):
                    if img_url not in pages:
                        pages.append(img_url)
    
    return pages
