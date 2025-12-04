"""Voicelines-only scraper for Kingdom Archives.

This module provides a focused scraper that downloads only agent voicelines
with organized filenames based on their descriptions.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config import ScraperConfig


@dataclass
class VoicelineInfo:
    """Information about a single voiceline."""
    agent: str
    category: str  # e.g., "Character select", "Match start"
    audio_url: str
    quote: str = ""


def sanitize_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove or replace problematic characters
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    # Remove multiple underscores
    name = re.sub(r"_+", "_", name)
    # Strip leading/trailing underscores
    name = name.strip("_")
    return name


def extract_agent_name_from_url(url: str) -> str:
    """Extract agent name from voicelines URL like /voicelines/yoru."""
    parts = url.rstrip("/").split("/")
    return parts[-1].title()  # 'yoru' -> 'Yoru'


def get_agents_list(session: requests.Session, base_url: str = "https://kingdomarchives.com") -> list[str]:
    """Fetch the list of all agents from the agents page."""
    agents_url = f"{base_url}/agents"
    response = session.get(agents_url, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, "html.parser")
    agents = []
    
    # Find all voicelines links like href="../voicelines/astra"
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/voicelines/" in href and "Voicelines" in link.get_text():
            # Extract agent name from href
            agent_name = href.split("/voicelines/")[-1].split("?")[0].strip("/")
            if agent_name and agent_name not in agents:
                agents.append(agent_name)
    
    return agents


def get_max_page(soup: BeautifulSoup) -> int:
    """Determine the maximum page number from pagination."""
    max_page = 1
    
    # Look for pagination buttons with aria-label like "Go to page X"
    for button in soup.find_all(["button", "span"], attrs={"aria-label": True}):
        label = button.get("aria-label", "")
        match = re.search(r"Go to page (\d+)", label)
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)
    
    return max_page


def parse_voicelines_page(html: str, agent: str, base_url: str) -> list[VoicelineInfo]:
    """Parse a voicelines page and extract all voiceline info."""
    soup = BeautifulSoup(html, "html.parser")
    voicelines = []
    current_category = "Unknown"
    
    # Find all table rows
    for row in soup.find_all("div", class_="custom-table-row"):
        # Check if this is a category row
        category_div = row.find("div", class_="category-row")
        if category_div:
            current_category = category_div.get_text(strip=True)
            continue
        
        # Find the voiceline type (first column with <p> tag)
        type_div = row.find("div", class_=lambda c: c and "col-span-12" in c and "xl:col-span-3" in c)
        if type_div:
            type_p = type_div.find("p")
            if type_p:
                voiceline_type = type_p.get_text(strip=True)
            else:
                voiceline_type = current_category
        else:
            voiceline_type = current_category
        
        # Find the audio element
        audio = row.find("audio", src=True)
        if audio:
            audio_src = audio["src"].replace("\\", "/")
            audio_url = urljoin(base_url, audio_src)
            
            # Try to get the quote text
            quote = ""
            shareable_div = row.find("div", class_="shareable")
            if shareable_div:
                quote_p = shareable_div.find("p")
                if quote_p:
                    quote = quote_p.get_text(strip=True)
            
            voicelines.append(VoicelineInfo(
                agent=agent,
                category=voiceline_type,
                audio_url=audio_url,
                quote=quote,
            ))
    
    return voicelines


def scrape_agent_voicelines(
    session: requests.Session,
    agent: str,
    base_url: str = "https://kingdomarchives.com",
    delay: float = 0.5,
) -> list[VoicelineInfo]:
    """Scrape all voicelines for a single agent across all pages."""
    all_voicelines = []
    
    # Fetch first page to determine max pages
    first_url = f"{base_url}/voicelines/{agent.lower()}"
    print(f"  Fetching {first_url}")
    response = session.get(first_url, timeout=30)
    response.raise_for_status()
    time.sleep(delay)
    
    soup = BeautifulSoup(response.content, "html.parser")
    max_page = get_max_page(soup)
    print(f"  Found {max_page} pages for {agent}")
    
    # Parse first page
    voicelines = parse_voicelines_page(response.text, agent, base_url)
    all_voicelines.extend(voicelines)
    print(f"    Page 1: {len(voicelines)} voicelines")
    
    # Fetch remaining pages
    for page in range(2, max_page + 1):
        page_url = f"{base_url}/voicelines/{agent.lower()}?page={page}"
        print(f"  Fetching page {page}...")
        response = session.get(page_url, timeout=30)
        response.raise_for_status()
        time.sleep(delay)
        
        voicelines = parse_voicelines_page(response.text, agent, base_url)
        all_voicelines.extend(voicelines)
        print(f"    Page {page}: {len(voicelines)} voicelines")
    
    return all_voicelines


def download_voicelines(
    session: requests.Session,
    voicelines: list[VoicelineInfo],
    output_dir: Path,
    delay: float = 0.5,
    dry_run: bool = True,
    skip_existing: bool = False,
) -> None:
    """Download voicelines with organized filenames."""
    # Group voicelines by agent and category to handle numbering
    by_agent_category: dict[str, dict[str, list[VoicelineInfo]]] = defaultdict(lambda: defaultdict(list))
    
    for vl in voicelines:
        by_agent_category[vl.agent][vl.category].append(vl)
    
    downloaded_count = 0
    skipped_count = 0
    
    for agent, categories in by_agent_category.items():
        agent_dir = output_dir / "voicelines" / sanitize_filename(agent)
        
        if not dry_run:
            agent_dir.mkdir(parents=True, exist_ok=True)
        
        for category, vls in categories.items():
            safe_category = sanitize_filename(category)
            
            for idx, vl in enumerate(vls, 1):
                # Create filename: Agent_Category_N.mp3
                if len(vls) > 1:
                    filename = f"{sanitize_filename(agent)}_{safe_category}_{idx}.mp3"
                else:
                    filename = f"{sanitize_filename(agent)}_{safe_category}.mp3"
                
                filepath = agent_dir / filename
                
                if dry_run:
                    print(f"Would download: {filepath}")
                elif skip_existing and filepath.exists():
                    skipped_count += 1
                    print(f"Skipping (exists): {filepath}")
                else:
                    print(f"Downloading: {filepath}")
                    try:
                        response = session.get(vl.audio_url, timeout=30)
                        response.raise_for_status()
                        filepath.write_bytes(response.content)
                        downloaded_count += 1
                        time.sleep(delay)
                    except Exception as e:
                        print(f"  Failed: {e}")
    
    if not dry_run:
        print(f"\nDownloaded: {downloaded_count}, Skipped: {skipped_count}")


class VoicelinesScraper:
    """Scraper focused on downloading agent voicelines."""
    
    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})
        self.base_url = "https://kingdomarchives.com"
    
    def run(self, agents: list[str] | None = None, skip_existing: bool = False) -> None:
        """Run the voicelines scraper.
        
        Args:
            agents: Optional list of agent names to scrape. If None, scrapes all agents.
            skip_existing: If True, skip files that already exist on disk.
        """
        print("Kingdom Archives Voicelines Scraper")
        print("=" * 40)
        
        if skip_existing:
            print("Skip existing files: enabled")
        
        # Get list of agents if not provided
        if agents is None:
            print("\nFetching agents list...")
            agents = get_agents_list(self.session, self.base_url)
            print(f"Found {len(agents)} agents: {', '.join(agents)}")
        
        all_voicelines = []
        
        for agent in agents:
            print(f"\nScraping voicelines for {agent.title()}...")
            try:
                voicelines = scrape_agent_voicelines(
                    self.session,
                    agent,
                    self.base_url,
                    self.config.delay,
                )
                all_voicelines.extend(voicelines)
                print(f"  Total: {len(voicelines)} voicelines for {agent.title()}")
            except Exception as e:
                print(f"  Error scraping {agent}: {e}")
        
        print(f"\n{'=' * 40}")
        print(f"Total voicelines discovered: {len(all_voicelines)}")
        
        # Download voicelines
        output_dir = self.config.output_dir
        dry_run = not self.config.execute_downloads
        
        if dry_run:
            print("\nDry run mode - files will not be downloaded.")
            print("Use --execute-downloads to actually download files.")
        else:
            print(f"\nDownloading to: {output_dir}")
        
        download_voicelines(
            self.session,
            all_voicelines,
            output_dir,
            self.config.delay,
            dry_run,
            skip_existing,
        )
        
        print("\nDone!")
    
    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
