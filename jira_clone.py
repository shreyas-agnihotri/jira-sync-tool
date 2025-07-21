#!/usr/bin/env python3

# Import compatibility fix for Python 3.13
import compatibility_fix

# Suppress SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from jira import JIRA
import json
from datetime import datetime
import logging
import argparse
from typing import Dict, List, Optional, Tuple, Any
import os
import sys
import time
import random

# Configure logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration Constants (will be overridden by config manager)
JIRA_URL = 'https://your-jira-instance.atlassian.net'
JIRA_EMAIL = 'your-email@example.com'
JIRA_API_TOKEN = 'your-api-token-here'

# Global configuration
jira_config = None

def set_jira_config(config):
    """Set JIRA configuration from config manager"""
    global jira_config, JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN
    jira_config = config
    JIRA_URL = config.get('url', JIRA_URL)
    JIRA_EMAIL = config.get('email', JIRA_EMAIL)
    JIRA_API_TOKEN = config.get('api_token', JIRA_API_TOKEN)

TARGET_DATE_FIELDS = [
    'PRD Due Date', 'PRD Review Due Date', 'Start date', 'Code Complete Target',
    'Release candidate Target', 'Preview Est. Date', 'GA Estimated Date'
]

FIELD_MAPPINGS = {
    'customfield_10015': 'customfield_13039',  # Start date (date ↔ string)
    'customfield_13039': 'customfield_10015',
    'customfield_11188': 'customfield_12652',  # PRD Due Date (date ↔ string)
    'customfield_12652': 'customfield_11188',
    'customfield_11189': 'customfield_12892',  # PRD Review Due Date (date ↔ string)
    'customfield_12892': 'customfield_11189',
    'customfield_11186': 'customfield_12893',  # Preview Est. Date (date ↔ string)
    'customfield_12893': 'customfield_11186',
    'customfield_10065': 'customfield_12588',  # Release candidate Target (date ↔ string)
    'customfield_12588': 'customfield_10065',
    'customfield_10071': 'customfield_12589',  # GA Estimated Date (date ↔ string)
    'customfield_12589': 'customfield_10071',
    'customfield_10064': 'customfield_12967',  # Code Complete Target (date ↔ string)
    'customfield_12967': 'customfield_10064',
}

# Global output queue for GUI integration
output_queue = None

def set_output_queue(queue):
    """Set the output queue for GUI integration"""
    global output_queue
    output_queue = queue

def gui_print(message):
    """Print to GUI if available, otherwise to console"""
    global output_queue
    if output_queue:
        output_queue.put(message)
    else:
        print(message)

def print_header(title: str, subtitle: str = ""):
    """Print a clean, professional header"""
    gui_print(f"\n{title}")
    if subtitle:
        gui_print(f"{subtitle}")
    gui_print("-" * len(title))

def print_section(title: str):
    """Print a section header"""
    gui_print(f"\n{title}")

def print_success(message: str):
    """Print success message with green color"""
    gui_print(f"\033[32m✓\033[0m {message}")

def print_warning(message: str):
    """Print warning message with yellow color"""
    gui_print(f"\033[33m!\033[0m {message}")

def print_error(message: str):
    """Print error message with red color"""
    gui_print(f"\033[31m✗\033[0m {message}")

def print_info(message: str):
    """Print info message"""
    gui_print(f"  {message}")

def print_verbose(message: str, verbose: bool = False):
    """Print verbose message only when verbose mode is enabled"""
    if verbose:
        gui_print(f"  {message}")

def print_progress(current: int, total: int, item: str = ""):
    """Print progress indicator"""
    percentage = (current / total) * 100 if total > 0 else 0
    bar_length = 20
    filled_length = int(bar_length * current // total) if total > 0 else 0
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    gui_print(f"\r  [{bar}] {percentage:5.1f}% ({current}/{total}) {item}", end='', flush=True)
    if current == total:
        gui_print()  # New line when complete

class ExecutionLogger:
    """Handles execution logging to file"""
    
    def __init__(self):
        self.log_file = "jira_clone_execution.log"
        self.execution_data = {
            'timestamp': datetime.now().isoformat(),
            'operation': None,
            'parameters': {},
            'results': {},
            'summary': []
        }
    
    def log_operation(self, operation: str, **kwargs):
        """Log the operation and parameters"""
        self.execution_data['operation'] = operation
        self.execution_data['parameters'].update(kwargs)
    
    def log_results(self, results: dict):
        """Log execution results"""
        self.execution_data['results'] = results
    
    def add_summary_line(self, line: str):
        """Add a line to the summary"""
        self.execution_data['summary'].append(line)
    
    def save_to_file(self):
        """Save execution summary to file"""
        try:
            with open(self.log_file, 'w') as f:
                f.write("=" * 80 + "\n")
                f.write(f"JIRA Clone Tool Execution Summary\n")
                f.write(f"Generated: {self.execution_data['timestamp']}\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Operation: {self.execution_data['operation']}\n")
                
                if self.execution_data['parameters']:
                    f.write("\nParameters:\n")
                    for key, value in self.execution_data['parameters'].items():
                        f.write(f"  {key}: {value}\n")
                
                if self.execution_data['results']:
                    f.write("\nResults:\n")
                    for key, value in self.execution_data['results'].items():
                        f.write(f"  {key}: {value}\n")
                
                if self.execution_data['summary']:
                    f.write("\nDetailed Summary:\n")
                    f.write("-" * 40 + "\n")
                    for line in self.execution_data['summary']:
                        f.write(f"{line}\n")
                
                f.write("\n" + "=" * 80 + "\n")
            
            print_info(f"Execution summary saved to: {self.log_file}")
        except Exception as e:
            print_warning(f"Could not save execution log: {str(e)}")

def create_table(headers: List[str], rows: List[List[str]], title: str = None) -> str:
    """Create a simple text table"""
    if not rows:
        return "No data to display"
    
    # Calculate column widths
    col_widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Create separator line
    separator = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
    
    # Build table
    table_lines = []
    if title:
        table_lines.append(f"\n{title}")
        table_lines.append("=" * len(title))
    
    table_lines.append(separator)
    
    # Header row
    header_row = "|"
    for i, header in enumerate(headers):
        header_row += f" {header.ljust(col_widths[i])} |"
    table_lines.append(header_row)
    table_lines.append(separator)
    
    # Data rows
    for row in rows:
        data_row = "|"
        for i, cell in enumerate(row):
            if i < len(col_widths):
                data_row += f" {str(cell).ljust(col_widths[i])} |"
        table_lines.append(data_row)
    
    table_lines.append(separator)
    return "\n".join(table_lines)

def format_date_for_display(date_value: Any) -> str:
    """Format date for user-friendly display"""
    if not date_value:
        return "Not set"
    
    date_str = str(date_value)
    if 'T' in date_str:
        date_str = date_str.split('T')[0]
    elif ' ' in date_str:
        date_str = date_str.split(' ')[0]
    
    try:
        # Try to format as a more readable date
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    except:
        return date_str

class JiraClient:
    """Handles Jira API connections and requests with rate limiting"""
    
    def __init__(self):
        self.jira = self._create_jira_client()
        self.last_api_call = 0
        self.min_delay = 0.2  # Minimum delay between API calls
    
    def _rate_limit_delay(self):
        """Ensure minimum delay between API calls"""
        elapsed = time.time() - self.last_api_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_api_call = time.time()
    
    def _api_call_with_retry(self, func, *args, **kwargs):
        """Execute API call with exponential backoff retry"""
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                self._rate_limit_delay()
                return func(*args, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                
                # Check for rate limiting errors
                if 'rate limit' in error_str or 'too many requests' in error_str or '429' in error_str:
                    if attempt < max_retries - 1:
                        # Exponential backoff with jitter
                        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print_warning(f"Rate limited, waiting {delay:.1f}s before retry {attempt + 1}/{max_retries}")
                        time.sleep(delay)
                        continue
                
                # Re-raise if not rate limiting or max retries reached
                raise e
        
        raise Exception(f"Max retries ({max_retries}) exceeded")

    def _create_jira_client(self):
        """Create a JIRA client with rate limiting, API v3, and SSL verification disabled for self-signed certs"""
        return JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN), 
                   options={'rest_api_version': '3', 'verify': False})

    def get_issue(self, issue_key: str):
        """Get issue with rate limiting"""
        return self._api_call_with_retry(self.jira.issue, issue_key)

    def update_issue_field(self, issue_key: str, field_id: str, value: Any) -> bool:
        """Update issue field with rate limiting"""
        try:
            issue = self.get_issue(issue_key)
            self._api_call_with_retry(issue.update, fields={field_id: value})
            return True
        except Exception as e:
            print_error(f"Failed to update {field_id} on {issue_key}: {str(e)}")
            return False

    def search_issues(self, *args, **kwargs):
        """Search issues with rate limiting"""
        return self._api_call_with_retry(self.jira.search_issues, *args, **kwargs)

class FieldMapper:
    """Handles field mapping and resolution"""
    
    def __init__(self, jira_client: JiraClient):
        self.jira = jira_client.jira
        self._field_cache = None
    
    @property
    def all_fields(self) -> List[Dict]:
        """Cached field definitions"""
        if self._field_cache is None:
            self._field_cache = self.jira.fields()
        return self._field_cache
    
    def get_field_mapping(self) -> Dict[str, Dict]:
        """Get enhanced field mapping for target date fields"""
        field_map = {}
        field_alternatives = {}
        
        # Group fields by name
        for field in self.all_fields:
            if field['custom'] and field['name'] in TARGET_DATE_FIELDS:
                name = field['name']
                if name not in field_alternatives:
                    field_alternatives[name] = []
                
                schema_type = field.get('schema', {}).get('type', 'unknown')
                field_alternatives[name].append({
                    'id': field['id'], 'type': schema_type
                })
        
        # Choose primary and alternatives
        for name, alternatives in field_alternatives.items():
            date_fields = [f for f in alternatives if f['type'] in ['date', 'datetime']]
            primary = date_fields[0] if date_fields else alternatives[0]
            
            field_map[name] = {
                'id': primary['id'],
                'type': primary['type'],
                'alternatives': [f['id'] for f in alternatives if f['id'] != primary['id']]
            }
        
        return field_map
    
    def resolve_field_for_issue(self, field_id: str, issue) -> Optional[str]:
        """Resolve field ID that works for the given issue"""
        # Try original field
        try:
            getattr(issue.fields, field_id, None)
            return field_id
        except AttributeError:
            pass
        
        # Try mapped field
        mapped_id = FIELD_MAPPINGS.get(field_id)
        if mapped_id:
            try:
                getattr(issue.fields, mapped_id, None)
                return mapped_id
            except AttributeError:
                pass
        
        return None

class DateFieldProcessor:
    """Handles date field processing and formatting"""
    
    @staticmethod
    def is_jpd_issue(issue) -> bool:
        """Check if issue is JPD"""
        try:
            return issue.fields.issuetype.name == 'Idea'
        except:
            return False
    
    @staticmethod
    def format_date_string(date_value: Any) -> str:
        """Convert date to string format"""
        date_str = str(date_value)
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        elif ' ' in date_str:
            date_str = date_str.split(' ')[0]
        return date_str
    
    @staticmethod
    def format_for_jpd(date_value: Any) -> str:
        """Format date for JPD JSON string format"""
        date_str = DateFieldProcessor.format_date_string(date_value)
        return json.dumps({"start": date_str, "end": date_str})
    
    def extract_populated_fields(self, issue, field_mapping: Dict) -> Dict:
        """Extract populated date fields from issue"""
        populated = {}
        for field_name, field_info in field_mapping.items():
            field_value = getattr(issue.fields, field_info['id'], None)
            if field_value:
                populated[field_name] = {
                    'value': field_value,
                    'source_id': field_info['id'],
                    'type': field_info['type']
                }
        return populated

class FieldLister:
    """Handles field listing functionality"""
    
    def __init__(self, jira_client: JiraClient):
        self.jira_client = jira_client
        self.field_mapper = FieldMapper(jira_client)
    
    def list_fields(self, issue_key: str, show_empty: bool = False) -> bool:
        """List fields in an issue"""
        issue = self.jira_client.get_issue(issue_key)
        if not issue:
            return False
        
        is_jpd = DateFieldProcessor.is_jpd_issue(issue)
        self._print_issue_summary(issue, is_jpd, show_empty)
        
        populated, empty = self._categorize_fields(issue, show_empty)
        self._display_field_summary(populated, empty, show_empty, is_jpd)
        
        return True
    
    def _print_issue_summary(self, issue, is_jpd: bool, show_empty: bool):
        """Print clean issue summary"""
        issue_type = "JPD Idea" if is_jpd else f"{issue.fields.issuetype.name}"
        scope = "All fields" if show_empty else "Populated fields"
        
        print_header(f"📋 {issue.key} ({issue_type})")
        print_info(f"{issue.fields.summary}")
        print_info(f"Showing: {scope}")
    
    def _categorize_fields(self, issue, show_empty: bool) -> Tuple[Dict, Dict]:
        """Categorize fields into populated and empty"""
        field_lookup = {f['id']: f for f in self.field_mapper.all_fields}
        populated = {}
        empty = {}
        
        if show_empty:
            # Check all fields
            for field in self.field_mapper.all_fields:
                field_id = field['id']
                try:
                    value = getattr(issue.fields, field_id, None)
                    target = populated if (value and value != [] and value != "") else empty
                    target[field_id] = self._create_field_entry(field, value or None)
                except:
                    empty[field_id] = self._create_field_entry(field, None)
        else:
            # Only populated fields
            for attr_name in dir(issue.fields):
                if not attr_name.startswith('_'):
                    try:
                        value = getattr(issue.fields, attr_name, None)
                        if value and value != [] and value != "":
                            field_info = field_lookup.get(attr_name, {})
                            populated[attr_name] = self._create_field_entry(field_info, value)
                    except:
                        continue
        
        return populated, empty
    
    def _create_field_entry(self, field_info: Dict, value: Any) -> Dict:
        """Create standardized field entry"""
        schema_type = field_info.get('schema', {}).get('type', 'unknown')
        value_str = str(value or 'Not set')
        
        return {
            'name': field_info.get('name', field_info.get('id', 'Unknown')),
            'type': schema_type,
            'value': value_str[:50] + "..." if value and len(value_str) > 50 else value_str,
            'is_custom': field_info.get('custom', False),
            'is_date': schema_type in ['date', 'datetime']
        }
    
    def _display_field_summary(self, populated: Dict, empty: Dict, show_empty: bool, is_jpd: bool):
        """Display clean field summary"""
        # Focus on date fields for product managers
        date_fields = {k: v for k, v in populated.items() if v['is_date']}
        target_date_fields = {k: v for k, v in date_fields.items() if v['name'] in TARGET_DATE_FIELDS}
        
        if target_date_fields:
            print_section("🎯 Milestone Dates")
            for field_id, field in target_date_fields.items():
                formatted_date = format_date_for_display(field['value']) if field['value'] != 'Not set' else 'Not set'
                print(f"  {field['name']}: {formatted_date}")
        
        if date_fields and len(date_fields) > len(target_date_fields):
            print_section("🗓️ Other Dates")
            for field_id, field in date_fields.items():
                if field['name'] not in TARGET_DATE_FIELDS:
                    formatted_date = format_date_for_display(field['value']) if field['value'] != 'Not set' else 'Not set'
                    print(f"  {field['name']}: {formatted_date}")
        
        # Summary
        print_section("📊 Summary")
        print_info(f"Total: {len(populated)} fields, {len(date_fields)} dates, {len(target_date_fields)} milestones")
        
        if is_jpd:
            print_info("JPD formatting applies for updates")

class DateFieldCloner:
    """Main class for cloning date fields between issues"""
    
    def __init__(self, quiet: bool = False, verbose: bool = False):
        self.jira_client = JiraClient()
        self.field_mapper = FieldMapper(self.jira_client)
        self.processor = DateFieldProcessor()
        self.field_lister = FieldLister(self.jira_client)
        self.logger = self._create_logger()
        self.quiet = quiet
        self.verbose = verbose
    
    def _create_logger(self):
        """Create execution logger"""
        return {
            'log_file': "jira_clone_execution.log",
            'data': {
                'timestamp': datetime.now().isoformat(),
                'operation': None,
                'parameters': {},
                'results': {},
                'summary': []
            }
        }
    
    def _log_operation(self, operation: str, **kwargs):
        """Log the operation and parameters"""
        self.logger['data']['operation'] = operation
        self.logger['data']['parameters'].update(kwargs)
    
    def _save_execution_log(self):
        """Save execution summary to file"""
        try:
            with open(self.logger['log_file'], 'w') as f:
                f.write("=" * 80 + "\n")
                f.write(f"JIRA Clone Tool Execution Summary\n")
                f.write(f"Generated: {self.logger['data']['timestamp']}\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"Operation: {self.logger['data']['operation']}\n")
                
                if self.logger['data']['parameters']:
                    f.write("\nParameters:\n")
                    for key, value in self.logger['data']['parameters'].items():
                        f.write(f"  {key}: {value}\n")
                
                if self.logger['data']['results']:
                    f.write("\nResults:\n")
                    for key, value in self.logger['data']['results'].items():
                        f.write(f"  {key}: {value}\n")
                
                if self.logger['data']['summary']:
                    f.write("\nDetailed Summary:\n")
                    f.write("-" * 40 + "\n")
                    for line in self.logger['data']['summary']:
                        f.write(f"{line}\n")
                
                f.write("\n" + "=" * 80 + "\n")
            
            print_info(f"Execution summary saved to: {self.logger['log_file']}")
        except Exception as e:
            print_warning(f"Could not save execution log: {str(e)}")
    
    def _create_table(self, headers: List[str], rows: List[List[str]], title: str = None) -> str:
        """Create a clean, well-formatted text table"""
        if not rows:
            return "No data to display"
        
        # Calculate column widths, accounting for emoji display width
        def display_width(text):
            """Calculate display width accounting for emojis"""
            emoji_count = 0
            for char in str(text):
                # Count common emojis that take more visual space
                if char in '✅❌⚠️⏭️📋🚀🔍📊📤📥🗺️':
                    emoji_count += 1
            # Emojis typically display as 2 characters wide but count as 1
            return len(str(text)) + emoji_count
        
        col_widths = [display_width(header) for header in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], display_width(cell))
        
        # Add minimum padding and ensure reasonable column widths
        col_widths = [max(width + 2, 12) for width in col_widths]
        
        # Create clean separator line
        separator = "+" + "+".join("─" * (width + 2) for width in col_widths) + "+"
        
        # Build table
        table_lines = []
        if title:
            table_lines.append(f"\n{title}")
            table_lines.append("=" * len(title))
        
        table_lines.append(separator)
        
        # Header row
        header_row = "│"
        for i, header in enumerate(headers):
            padding = col_widths[i] - display_width(header)
            header_row += f" {header}{' ' * padding} │"
        table_lines.append(header_row)
        table_lines.append(separator.replace("─", "═"))
        
        # Data rows
        for row in rows:
            data_row = "│"
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    padding = col_widths[i] - display_width(cell)
                    data_row += f" {str(cell)}{' ' * padding} │"
            table_lines.append(data_row)
        
        table_lines.append(separator)
        return "\n".join(table_lines)
    
    def find_linked_engineering_ticket(self, jpd_key: str) -> Optional[str]:
        """Find the linked engineering ticket for a JPD idea"""
        issue = self.jira_client.get_issue(jpd_key)
        if not issue:
            return None
        
        # Check if it's actually a JPD issue
        if not self.processor.is_jpd_issue(issue):
            print_warning(f"{jpd_key} is not a JPD idea")
            return None
        
        # Look for linked engineering tickets
        try:
            if hasattr(issue.fields, 'issuelinks') and issue.fields.issuelinks:
                for link in issue.fields.issuelinks:
                    linked_issue_key = None
                    
                    # Check both directions of the link
                    if hasattr(link, 'outwardIssue') and link.outwardIssue:
                        linked_issue_key = link.outwardIssue.key
                    elif hasattr(link, 'inwardIssue') and link.inwardIssue:
                        linked_issue_key = link.inwardIssue.key
                    
                    # If we found a non-JPD issue, it's likely the engineering ticket
                    if linked_issue_key and not linked_issue_key.startswith('IDEA-'):
                        return linked_issue_key
        except Exception as e:
            print_info(f"Could not check issue links: {str(e)}")
        
        return None
    
    def get_jpd_ideas_in_project(self, project_key: str) -> List[str]:
        """Get all JPD ideas in a project using pagination with rate limiting"""
        try:
            # Query for all ideas in the project with pagination
            jql = f'project = "{project_key}" AND issuetype = "Idea"'
            all_issues = []
            start_at = 0
            max_results = 50  # Reduced batch size to be gentler on API
            
            while True:
                print_info(f"Fetching ideas {start_at + 1}-{start_at + max_results}...")
                
                # Use rate-limited search
                issues = self.jira_client.search_issues(
                    jql, 
                    startAt=start_at, 
                    maxResults=max_results, 
                    fields='key,summary'
                )
                
                print_info(f"Got {len(issues)} issues in this batch")
                
                if not issues:
                    print_info("No more issues found, stopping pagination")
                    break
                
                all_issues.extend(issues)
                
                # If we got fewer results than requested, we've reached the end
                if len(issues) < max_results:
                    print_info(f"Got {len(issues)} < {max_results}, reached end of results")
                    break
                
                start_at += max_results
                
                # Add delay between pagination requests to avoid overwhelming API
                time.sleep(0.3)
            
            idea_keys = [issue.key for issue in all_issues]
            print_info(f"Found {len(idea_keys)} total ideas in project {project_key}")
            
            return idea_keys
        except Exception as e:
            print_error(f"Failed to get ideas from project {project_key}: {str(e)}")
            return []
    
    def bulk_sync_project(self, project_key: str, dry_run: bool = False, force: bool = False) -> bool:
        """Auto-sync dates for all ideas in a JPD project"""
        self._log_operation(f"Bulk Sync Project", project=project_key, dry_run=dry_run)
        
        mode_text = " (dry run)" if dry_run else ""
        if not self.quiet:
            print_header(f"Bulk sync: {project_key}{mode_text}")
        
        # Get all ideas in the project
        if not self.quiet:
            print_info("Discovering JPD ideas...")
        idea_keys = self.get_jpd_ideas_in_project(project_key)
        
        if not idea_keys:
            print_error(f"No ideas found in project {project_key}")
            return False
        
        if not self.quiet:
            action_text = "Would process" if dry_run else "Processing"
            print_info(f"{action_text} {len(idea_keys)} ideas")
        
        # Track results
        results = {
            'processed': 0,
            'successful': 0,
            'no_links': 0,
            'skipped': 0,
            'failed': 0,
            'details': []
        }
        
        # Process each idea
        for i, idea_key in enumerate(idea_keys, 1):
            if not self.quiet and not self.verbose:
                print_progress(i, len(idea_keys), idea_key)
            elif self.verbose:
                print_section(f"Processing {i}/{len(idea_keys)}: {idea_key}")
            
            # Find linked engineering ticket
            eng_ticket = self.find_linked_engineering_ticket(idea_key)
            
            if not eng_ticket:
                print_verbose(f"No linked engineering ticket found for {idea_key}", self.verbose)
                results['no_links'] += 1
                results['details'].append((idea_key, 'no_link', None))
                continue
            
            print_verbose(f"Found linked ticket: {eng_ticket}", self.verbose)
            
            # Try to sync
            try:
                success, status = self._clone_fields_with_status(eng_ticket, idea_key, dry_run=dry_run, force=force)
                if success:
                    results['successful'] += 1
                    results['details'].append((idea_key, 'success', eng_ticket))
                    if self.verbose:
                        action_text = "Would sync" if dry_run else "Synced"
                        print_success(f"{action_text} {idea_key} ← {eng_ticket}")
                elif status == 'skipped':
                    results['skipped'] += 1
                    results['details'].append((idea_key, 'skipped', eng_ticket))
                    if self.verbose:
                        action_text = "Would skip" if dry_run else "Skipped"
                        print_warning(f"{action_text} {idea_key} ← {eng_ticket}")
                else:  # status == 'failed'
                    if not dry_run:  # Don't count as failed in dry run
                        results['failed'] += 1
                        results['details'].append((idea_key, 'failed', eng_ticket))
                        if self.verbose:
                            print_error(f"Failed {idea_key} ← {eng_ticket}")
            except Exception as e:
                if not dry_run:  # Don't count as error in dry run
                    results['failed'] += 1
                    results['details'].append((idea_key, 'error', eng_ticket))
                    if self.verbose:
                        print_error(f"Error syncing {idea_key}: {str(e)}")
            
            results['processed'] += 1
            
            # Add progressive delay to avoid overwhelming the API (longer for larger projects)
            delay = 0.1 if dry_run else min(1.0, 0.3 + (i / 100))  # Progressive delay: 0.3s to 1.0s
            time.sleep(delay)
        
        # Final summary
        if not self.quiet:
            self._print_bulk_summary(project_key, results, dry_run)
        else:
            # Minimal output for quiet mode
            if results['successful'] > 0:
                action = "Would sync" if dry_run else "Synced"
                print(f"{action}: {results['successful']}")
            if results['failed'] > 0 and not dry_run:
                print(f"Failed: {results['failed']}")
        
        # Save execution log
        self._save_execution_log()
        
        return results['successful'] > 0
    
    def _print_bulk_summary(self, project_key: str, results: dict, dry_run: bool = False):
        """Print bulk sync summary following Google CLI best practices"""
        mode_text = " (dry run)" if dry_run else ""
        print_header(f"Summary: {project_key}{mode_text}")
        
        # Clean summary with status indicators
        total = results['processed'] + results['no_links']
        
        if results['successful'] > 0:
            action_text = "Would sync" if dry_run else "Synced"
            print_success(f"{action_text} {results['successful']} ideas")
        
        if results['skipped'] > 0:
            skip_text = "Would skip" if dry_run else "Skipped"
            print_warning(f"{skip_text} {results['skipped']} ideas (no milestone dates)")
        
        if results['no_links'] > 0:
            print_warning(f"No linked tickets: {results['no_links']} ideas")
        
        if results['failed'] > 0 and not dry_run:
            print_error(f"Failed to sync: {results['failed']} ideas")
        
        if not self.quiet:
            print_info(f"Total processed: {total} ideas")
        
        if dry_run and results['successful'] > 0:
            print_info("Run without --dry-run to apply changes")
        
        # Show detailed table only when verbose or when there are issues
        show_detailed = (
            self.verbose or 
            (results['failed'] > 0 and not dry_run) or
            (dry_run and total > 0)
        )
        
        if show_detailed:
            self._print_detailed_results(results, dry_run)
        
        # Log results
        self.logger['data']['results'] = {
            'project': project_key,
            'dry_run': dry_run,
            'successful': results['successful'],
            'skipped': results['skipped'],
            'no_links': results['no_links'], 
            'failed': results['failed'],
            'total_processed': results['processed']
        }
    
    def _print_detailed_results(self, results: dict, dry_run: bool):
        """Print detailed results table"""
        headers = ["Idea", "Status", "Engineering Ticket", "Result"]
        rows = []
        
        for idea_key, status, eng_ticket in results['details']:
            if status == 'success':
                status_symbol = "✓"
                result = "Would sync" if dry_run else "Synced"
                eng_display = eng_ticket or "-"
            elif status == 'skipped':
                status_symbol = "!"
                result = "Would skip" if dry_run else "Skipped"
                eng_display = eng_ticket or "-"
            elif status == 'no_link':
                status_symbol = "!"
                result = "No linked ticket"
                eng_display = "-"
            else:
                status_symbol = "✗" if not dry_run else "!"
                result = "Failed" if not dry_run else "Would fail"
                eng_display = eng_ticket or "Unknown"
            
            rows.append([idea_key, status_symbol, eng_display, result])
        
        table = self._create_table(headers, rows)
        print(table)
        
        # Log table to summary
        self.logger['data']['summary'].append("Detailed Results:")
        self.logger['data']['summary'].append(table)

    def auto_sync_from_jpd(self, jpd_key: str, force: bool = False) -> bool:
        """Auto-discover and sync dates from linked engineering ticket to JPD idea"""
        self._log_operation(f"Auto Sync from JPD", jpd_idea=jpd_key)
        
        print_header(f"🔍 Auto-discovering links for {jpd_key}")
        
        # Find the linked engineering ticket
        eng_ticket = self.find_linked_engineering_ticket(jpd_key)
        
        if not eng_ticket:
            print_error(f"No linked engineering ticket found for {jpd_key}")
            print_info("JPD idea must have a formal issue link to an engineering ticket")
            self.logger['data']['results'] = {'status': 'no_linked_ticket', 'jpd_idea': jpd_key}
            self._save_execution_log()
            return False
        
        print_success(f"Found linked engineering ticket: {eng_ticket}")
        print_info(f"Will copy dates from {eng_ticket} to {jpd_key}")
        
        # Log the discovery
        self.logger['data']['summary'].extend([
            f"Auto-discovery for JPD idea: {jpd_key}",
            f"Found linked engineering ticket: {eng_ticket}",
            "Proceeding with date sync..."
        ])
        
        # Proceed with normal sync
        success = self.clone_fields(eng_ticket, jpd_key, dry_run=False, force=force)
        return success

    def check_links(self, issue1_key: str, issue2_key: str) -> bool:
        """Check if issue1 has any reference to issue2"""
        print_header(f"🔍 Checking links: {issue1_key} → {issue2_key}")
        
        issue1 = self.jira_client.get_issue(issue1_key)
        if not issue1:
            print_error(f"Cannot access {issue1_key}")
            return False
        
        print_info(f"Searching {issue1_key} for references to '{issue2_key}'...")
        
        # Get all field names for display
        field_names = {f['id']: f['name'] for f in self.field_mapper.all_fields}
        references_found = []
        
        # Check issue links first
        try:
            if hasattr(issue1.fields, 'issuelinks') and issue1.fields.issuelinks:
                for link in issue1.fields.issuelinks:
                    linked_issue = None
                    link_type = ""
                    
                    if hasattr(link, 'outwardIssue') and link.outwardIssue:
                        linked_issue = link.outwardIssue.key
                        link_type = f"outward: {link.type.outward}"
                    elif hasattr(link, 'inwardIssue') and link.inwardIssue:
                        linked_issue = link.inwardIssue.key  
                        link_type = f"inward: {link.type.inward}"
                    
                    if linked_issue and linked_issue.upper() == issue2_key.upper():
                        references_found.append(("Issue Links", f"{link_type} → {linked_issue}"))
        except Exception as e:
            print_info(f"Could not check issue links: {str(e)}")
        
        # Check all other fields for text references
        for field_id in dir(issue1.fields):
            if field_id.startswith('_'):
                continue
                
            try:
                value = getattr(issue1.fields, field_id, None)
                if value and str(value) and issue2_key.upper() in str(value).upper():
                    field_name = field_names.get(field_id, field_id)
                    # Truncate long values for display
                    display_value = str(value)
                    if len(display_value) > 100:
                        display_value = display_value[:100] + "..."
                    references_found.append((field_name, display_value))
            except:
                continue
        
        # Display results
        print_section("📊 Results")
        if references_found:
            print_success(f"Found {len(references_found)} reference(s) to '{issue2_key}':")
            for field_name, value in references_found:
                print(f"  • {field_name}: {value}")
            return True
        else:
            print_warning(f"No references to '{issue2_key}' found in {issue1_key}")
            return False
    
    def show_mapping(self):
        """Display field mapping information following Google CLI best practices"""
        print_header("Milestone Date Fields")
        
        print("Available fields:")
        for field_name in TARGET_DATE_FIELDS:
            print(f"  {field_name}")
        
        print("\nUsage:")
        print("  jira_clone.py SOURCE TARGET          # Sync dates between issues")
        print("  jira_clone.py --auto-sync IDEA       # Auto-discover linked ticket")
        print("  jira_clone.py --bulk-sync PROJECT    # Bulk sync project ideas")
        print("  jira_clone.py --list-fields ISSUE    # Show issue dates")
        
        print("\nOptions:")
        print("  --dry-run    Preview changes without applying")
        print("  --force      Skip confirmation prompts")
        print("  --quiet      Minimal output")
        print("  --verbose    Detailed output")
        
        print("\nNotes:")
        print("  - Automatically detects field formats (Jira vs JPD)")
        print("  - Maps fields by name between projects")
        print("  - Requires valid JIRA authentication")
    
    def clone_fields(self, source_key: str, target_key: str, dry_run: bool = False, force: bool = False) -> bool:
        """Clone date fields between issues with clean output
        
        Returns:
            success: bool
        """
        success, _ = self._clone_fields_with_status(source_key, target_key, dry_run, force)
        return success
    
    def _clone_fields_with_status(self, source_key: str, target_key: str, dry_run: bool = False, force: bool = False) -> tuple[bool, str]:
        """Clone date fields between issues with detailed status
        
        Returns:
            (success: bool, status: str) where status is 'success', 'skipped', or 'failed'
        """
        self._log_operation(f"Clone Fields", source=source_key, target=target_key, dry_run=dry_run)
        
        # Get issues
        source_issue = self.jira_client.get_issue(source_key)
        target_issue = self.jira_client.get_issue(target_key)
        
        if not source_issue or not target_issue:
            print_warning("Cannot access issues. Check issue keys.")
            self._save_execution_log()
            return False, 'skipped'
        
        # Analyze source
        field_mapping = self.field_mapper.get_field_mapping()
        populated_fields = self.processor.extract_populated_fields(source_issue, field_mapping)
        
        if not populated_fields:
            print_warning(f"No milestone dates in {source_key} - skipping")
            self._save_execution_log()
            return False, 'skipped'
        
        # Show what will be copied
        is_target_jpd = self.processor.is_jpd_issue(target_issue)
        target_type = "JPD" if is_target_jpd else "Jira"
        
        mode_text = "DRY RUN" if dry_run else "SYNC"
        print_header(f"📤 {source_key} → 📥 {target_key} ({target_type}) [{mode_text}]")
        
        action_text = "Would copy" if dry_run else "Copying"
        print_info(f"{action_text} {len(populated_fields)} dates:")
        
        dates_list = []
        for field_name, field_data in populated_fields.items():
            formatted_date = format_date_for_display(field_data['value'])
            print(f"  • {field_name}: {formatted_date}")
            dates_list.append(f"{field_name}: {formatted_date}")
        
        # Log the dates being copied
        self.logger['data']['summary'].extend([
            f"Operation: {mode_text}",
            f"Source: {source_key} ({source_issue.fields.issuetype.name})",
            f"Target: {target_key} ({target_type})",
            f"Dates to copy: {len(populated_fields)}",
            ""
        ] + dates_list)
        
        if dry_run:
            print_section("🔍 Dry Run Results")
            print_info("No changes would be made - this is a preview only")
            
            # Create comprehensive table for dry run showing all target date fields
            headers = ["Field Name", "Source Value", "Status"]
            rows = []
            
            # Check all target date fields, not just populated ones
            for target_field in TARGET_DATE_FIELDS:
                if target_field in populated_fields:
                    # Field has a value in source
                    field_data = populated_fields[target_field]
                    date_value = format_date_for_display(field_data['value'])
                    status = "Would update"
                else:
                    # Field is not set in source
                    date_value = "Not set"
                    status = "No data to copy"
                
                rows.append([target_field, date_value, status])
            
            table = self._create_table(headers, rows, f"Dry Run: {source_key} → {target_key}")
            print(table)
            
            # Log results
            self.logger['data']['results'] = {
                'source': source_key,
                'target': target_key,
                'dry_run': True,
                'fields_to_copy': len(populated_fields),
                'total_target_fields': len(TARGET_DATE_FIELDS),
                'status': 'preview_only'
            }
            
            self._save_execution_log()
            return True, 'success'
        
        # Confirm operation
        if force:
            print_info("Skipping confirmation with --force flag")
        else:
            response = input(f"\nProceed? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                print_info("Cancelled")
                self.logger['data']['results'] = {'status': 'cancelled_by_user'}
                self._save_execution_log()
                return False, 'skipped'
        
        # Execute cloning
        success = self._execute_sync(target_issue, populated_fields, field_mapping, is_target_jpd)
        
        # Log final results
        status = 'success' if success else 'failed'
        self.logger['data']['results'] = {
            'source': source_key,
            'target': target_key,
            'dry_run': False,
            'fields_copied': len(populated_fields),
            'status': status
        }
        
        self._save_execution_log()
        return success, status
    
    def _execute_sync(self, target_issue, populated_fields: Dict, field_mapping: Dict, is_jpd: bool) -> bool:
        """Execute the field sync with clean progress reporting"""
        print_section("🚀 Updating dates")
        
        # Resolve target fields
        compatible_fields = self._resolve_target_fields(populated_fields, field_mapping, target_issue, is_jpd)
        
        if not compatible_fields:
            print_error("No compatible fields found")
            print_info("Target issue may not have these date fields configured")
            return False
        
        # Prepare and execute updates
        update_data = self._prepare_updates(compatible_fields, is_jpd)
        success_count = 0
        
        for field_name, (field_id, value) in update_data.items():
            if self.jira_client.update_issue_field(target_issue.key, field_id, value):
                print(f"  • {field_name} ✅")
                success_count += 1
            else:
                print(f"  • {field_name} ❌")
        
        # Final summary
        print_section("📊 Results")
        if success_count > 0:
            # Add clickable link to target issue
            if is_jpd:
                issue_url = f"{JIRA_URL}/jira/discovery/browse/{target_issue.key}"
                print_success(f"Updated {success_count}/{len(update_data)}")
                print_info(f"View idea: \033]8;;{issue_url}\033\\{issue_url}\033]8;;\033\\")
            else:
                issue_url = f"{JIRA_URL}/browse/{target_issue.key}"
                print_success(f"Updated {success_count}/{len(update_data)}")
                print_info(f"View issue: \033]8;;{issue_url}\033\\{issue_url}\033]8;;\033\\")
            
            if success_count < len(update_data):
                print_warning("Some updates failed - check field permissions")
            return True
        else:
            print_error("All updates failed - check permissions")
            return False
    
    def _resolve_target_fields(self, populated_fields: Dict, field_mapping: Dict, target_issue, is_jpd: bool) -> Dict:
        """Resolve target field IDs for populated fields"""
        compatible = {}
        
        for field_name, field_data in populated_fields.items():
            if field_name not in field_mapping:
                continue
            
            target_info = field_mapping[field_name]
            resolved_id = None
            
            # For JPD, try alternatives first (usually string fields)
            if is_jpd and target_info.get('alternatives'):
                for alt_id in target_info['alternatives']:
                    resolved_id = self.field_mapper.resolve_field_for_issue(alt_id, target_issue)
                    if resolved_id:
                        break
            
            # Try primary field if no alternative worked
            if not resolved_id:
                resolved_id = self.field_mapper.resolve_field_for_issue(target_info['id'], target_issue)
            
            if resolved_id:
                compatible[field_name] = {**field_data, 'target_id': resolved_id}
        
        return compatible
    
    def _prepare_updates(self, compatible_fields: Dict, is_jpd: bool) -> Dict:
        """Prepare update data with proper formatting"""
        updates = {}
        
        for field_name, field_data in compatible_fields.items():
            target_id = field_data['target_id']
            value = field_data['value']
            
            # For JPD, use JSON format for date fields
            if is_jpd:
                formatted_value = self.processor.format_for_jpd(value)
                updates[field_name] = (target_id, formatted_value)
            else:
                updates[field_name] = (target_id, value)
        
        return updates

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Sync milestone dates between Jira issues and JPD ideas',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s AV-12345 IDEA-67890             # Sync dates from AV-12345 to IDEA-67890
  %(prog)s --auto-sync IDEA-67890          # Auto-discover and sync from linked ticket
  %(prog)s --bulk-sync "JPD Project"       # Bulk sync all ideas in project
  %(prog)s --bulk-sync "JPD Project" --force  # Bulk sync without confirmation
  %(prog)s --bulk-sync "JPD Project" --dry-run  # Preview what would be synced
  %(prog)s --list-fields IDEA-67890        # Show dates in IDEA-67890
  %(prog)s --list-all-fields AV-12345      # Show all fields in AV-12345
  %(prog)s --show-mapping                  # Show available milestone date fields
        '''
    )
    
    parser.add_argument('source', nargs='?', help='Source issue key (e.g., AV-12345)')
    parser.add_argument('target', nargs='?', help='Target issue key (e.g., IDEA-67890)')
    parser.add_argument('-s', '--source', dest='source_explicit', help='Source issue key')
    parser.add_argument('-t', '--target', dest='target_explicit', help='Target issue key')
    parser.add_argument('-l', '--list-fields', dest='list_fields_issue', help='Show milestone dates in the specified issue')
    parser.add_argument('-a', '--list-all-fields', dest='list_all_fields_issue', help='Show all fields in the specified issue')
    parser.add_argument('-m', '--show-mapping', action='store_true', help='Show available milestone date fields')
    parser.add_argument('-c', '--check-links', nargs=2, metavar=('ISSUE1', 'ISSUE2'), help='Check if ISSUE1 has any reference to ISSUE2')
    parser.add_argument('--auto-sync', dest='auto_sync_jpd', help='Auto-discover and sync dates from linked engineering ticket to JPD idea')
    parser.add_argument('--bulk-sync', dest='bulk_sync_project', help='Bulk sync all ideas in a JPD project')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be synced without making changes')
    parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation prompts and proceed automatically')
    parser.add_argument('--quiet', '-q', action='store_true', help='Suppress non-essential output')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed output')
    
    return parser.parse_args()

def get_user_inputs(args) -> Tuple[Optional[str], Optional[str]]:
    """Get user inputs from command line or interactive prompt"""
    source_key = args.source_explicit or args.source
    target_key = args.target_explicit or args.target
    
    if source_key and target_key:
        return source_key.strip(), target_key.strip()
    
    # Interactive mode
    print_header("🔄 MILESTONE DATE SYNC TOOL")
    print_info("📅 This tool copies milestone dates between Jira issues and JPD ideas")
    
    if not source_key:
        source_key = input("\n📤 Source issue (where dates will be copied FROM): ").strip()
    if not target_key:
        target_key = input("📥 Target issue (where dates will be copied TO): ").strip()
    
    if not source_key or not target_key:
        print_error("Both source and target issue keys are required")
        return None, None
    
    return source_key, target_key

def main():
    """Main execution flow"""
    args = parse_arguments()
    
    try:
        cloner = DateFieldCloner(quiet=args.quiet, verbose=args.verbose)
        
        # Handle different modes
        if args.list_fields_issue or args.list_all_fields_issue:
            issue_key = args.list_all_fields_issue or args.list_fields_issue
            show_empty = bool(args.list_all_fields_issue)
            success = cloner.field_lister.list_fields(issue_key, show_empty)
            if not success:
                print_error("Unable to access the specified issue")
                sys.exit(1)
            
        elif args.show_mapping:
            cloner.show_mapping()
            
        elif args.check_links:
            issue1_key, issue2_key = args.check_links
            success = cloner.check_links(issue1_key, issue2_key)
            if not success and not args.quiet:
                print_info("No links found")
            
        elif args.auto_sync_jpd:
            success = cloner.auto_sync_from_jpd(args.auto_sync_jpd, force=args.force)
            if not success:
                print_error("Auto-sync failed")
                sys.exit(1)
            elif not args.quiet:
                print_success("Auto-sync completed")
        
        elif args.bulk_sync_project:
            if args.dry_run:
                if not args.quiet:
                    print_info("Dry run mode: showing what would be changed")
                success = cloner.bulk_sync_project(args.bulk_sync_project, dry_run=True, force=args.force)
            else:
                if not args.quiet:
                    print_warning("This will process all ideas in the project")
                
                # Auto-confirm if --force flag is used
                if args.force:
                    if not args.quiet:
                        print_info("Proceeding with --force flag")
                    proceed = True
                else:
                    if args.quiet:
                        print_error("Bulk sync requires --force in quiet mode")
                        sys.exit(1)
                    response = input("Continue? (y/N): ").strip().lower()
                    proceed = response in ['y', 'yes']
                
                if proceed:
                    success = cloner.bulk_sync_project(args.bulk_sync_project, dry_run=False, force=args.force)
                    if not success and not args.quiet:
                        print_warning("Bulk sync completed with issues")
                else:
                    if not args.quiet:
                        print_info("Cancelled")
                    sys.exit(0)
            
        else:
            # Sync mode
            source_key, target_key = get_user_inputs(args)
            if source_key and target_key:
                success = cloner.clone_fields(source_key, target_key, dry_run=args.dry_run, force=args.force)
                
                if not success and not args.dry_run:
                    print_error("Sync failed")
                    sys.exit(1)
                elif success and not args.quiet:
                    if args.dry_run:
                        print_success("Dry run completed")
                    else:
                        print_success("Sync completed")
            
    except KeyboardInterrupt:
        if not args.quiet:
            print_info("\nOperation cancelled")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print_error(f"An unexpected error occurred: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

