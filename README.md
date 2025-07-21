# JIRA Date Sync Tool

A modern GUI application for synchronizing milestone dates between JIRA issues and JPD (Jira Product Discovery) ideas.

## Features

- **Sync Dates**: Copy milestone dates between two JIRA issues
- **Auto Sync**: Automatically discover and sync from linked engineering tickets to JPD ideas
- **Bulk Sync**: Sync all ideas in a project at once
- **List Fields**: View date fields in any JIRA issue
- **Check Links**: Verify references between issues
- **Modern macOS UI**: Native-looking interface with proper styling

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the GUI:**
   ```bash
   python jira_ui.py
   ```

3. **Configure JIRA Credentials:**
   - The GUI will prompt you to enter your JIRA credentials on first run
   - Credentials are securely stored in macOS Keychain
   - You can change credentials anytime via the "⚙️ Configuration" button

## Usage

### GUI Mode (Recommended)

Launch the GUI application:
```bash
python jira_ui.py
```

The interface provides five main modes:

1. **Sync Dates**: Copy dates from one issue to another
2. **Auto Sync**: Auto-discover linked tickets for JPD ideas
3. **Bulk Sync**: Process all ideas in a project
4. **List Fields**: View fields in an issue
5. **Check Links**: Check references between issues

### Command Line Mode

You can also use the original command-line interface:
```bash
python jira_clone.py --help
```

## Configuration

### JIRA Credentials

The tool now supports secure credential management:

- **First Run**: The GUI will prompt you to enter your JIRA credentials
- **Secure Storage**: Credentials are stored in macOS Keychain for security
- **Easy Management**: Change credentials anytime via the "⚙️ Configuration" button
- **Connection Testing**: Test your credentials before saving

### Required Information

You'll need to provide:
- **JIRA URL**: Your JIRA instance URL (e.g., `https://yourcompany.atlassian.net`)
- **Email**: Your JIRA account email
- **API Token**: Your JIRA API token (not your password)

### Getting Your API Token

1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a name (e.g., "JIRA Date Sync Tool")
4. Copy the generated token

### Configuration Setup

1. Copy the template file:
   ```bash
   cp jira_config.template.json jira_config.json
   ```

2. Edit `jira_config.json` with your actual JIRA credentials:
   ```json
   {
     "url": "https://your-jira-instance.atlassian.net",
     "email": "your-email@example.com", 
     "api_token": "your-api-token-here"
   }
   ```

### Legacy Configuration

If you need to modify the default configuration, edit the constants in `jira_clone.py`:

## Features

### Sync Dates
- Copy milestone dates between any two JIRA issues
- Supports both JIRA and JPD issue types
- Automatic field mapping between different projects
- Dry-run mode for previewing changes

### Auto Sync
- Automatically finds linked engineering tickets for JPD ideas
- Requires formal issue links between JPD and engineering tickets
- Handles JPD-specific date formatting

### Bulk Sync
- Process all ideas in a JPD project
- Progress tracking with visual indicators
- Rate limiting to avoid API overload
- Comprehensive logging

### List Fields
- View all date fields in any JIRA issue
- Option to show all fields (including empty ones)
- Formatted date display

### Check Links
- Verify if one issue references another
- Searches through all fields for text references
- Useful for debugging link relationships

## Supported Date Fields

The tool handles these milestone date fields:
- PRD Due Date
- PRD Review Due Date
- Start date
- Code Complete Target
- Release candidate Target
- Preview Est. Date
- GA Estimated Date

## Error Handling

- Comprehensive error messages
- Rate limiting with exponential backoff
- Retry logic for transient failures
- Detailed logging for debugging

## Output

- Real-time output display in the GUI
- Execution logs saved to `jira_clone_execution.log`
- Status indicators for all operations
- Progress bars for bulk operations

## Requirements

- Python 3.7+ (compatible with Python 3.13)
- macOS (for native UI styling and keychain access)
- JIRA API access
- Valid JIRA credentials

## Troubleshooting

### Python 3.13 Compatibility

The tool includes a compatibility fix for Python 3.13 where the `imghdr` module was removed. This is automatically handled by the `compatibility_fix.py` module.

### Common Issues

1. **Authentication Issues**: Verify your JIRA API token is correct
2. **Permission Errors**: Ensure you have edit permissions on target issues
3. **Rate Limiting**: The tool includes built-in rate limiting, but you may need to wait if you hit API limits
4. **Field Mapping**: Some fields may not be available in all projects
5. **Keychain Access**: If you get keychain permission errors, you may need to allow access in System Preferences
6. **Tkinter Missing**: If you get `ModuleNotFoundError: No module named '_tkinter'`, install tkinter:
   ```bash
   brew install python-tk
   ```

## Development

The GUI is built with tkinter and integrates with the existing `jira_clone.py` functionality. The output is captured and redirected to the GUI display area. 