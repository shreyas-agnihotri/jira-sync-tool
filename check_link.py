#!/usr/bin/env python3

import os
from jira import JIRA

# Load configuration
JIRA_URL = os.getenv('JIRA_URL', 'https://your-jira-instance.atlassian.net')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')

def check_for_reference(issue_key, search_term):
    """Check if an issue has any reference to a search term"""
    jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN), 
           options={'rest_api_version': '3', 'verify': False})
    
    try:
        issue = jira.issue(issue_key, expand='names')
        print(f"\nChecking {issue_key} for references to '{search_term}'...")
        print(f"Issue: {issue.key} - {issue.fields.summary}")
        print("=" * 60)
        
        # Get all field names
        field_names = {f['id']: f['name'] for f in jira.fields()}
        
        references_found = []
        
        # Check all fields
        for field_id in dir(issue.fields):
            if field_id.startswith('_'):
                continue
                
            try:
                value = getattr(issue.fields, field_id, None)
                if value and str(value) and search_term.upper() in str(value).upper():
                    field_name = field_names.get(field_id, field_id)
                    references_found.append((field_name, str(value)))
            except:
                continue
        
        if references_found:
            print(f"\n✅ Found {len(references_found)} reference(s) to '{search_term}':")
            for field_name, value in references_found:
                print(f"  • {field_name}: {value}")
        else:
            print(f"\n❌ No references to '{search_term}' found in {issue_key}")
            
        return len(references_found) > 0
        
    except Exception as e:
        print(f"❌ Error checking {issue_key}: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        # Check if IDEA-689 has any reference to AV-99599
        has_reference = check_for_reference("IDEA-689", "AV-99599")
        
        if has_reference:
            print(f"\n🔗 IDEA-689 has a link back to AV-99599!")
        else:
            print(f"\n🚫 No link found from IDEA-689 back to AV-99599")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Force exit to avoid PowerShell issues
        import sys
        sys.exit(0) 