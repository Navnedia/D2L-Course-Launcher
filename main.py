import json
import sys,os
# Load libraries from lib:
parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, 'lib'))
sys.path.append(os.path.join(parent_folder_path, 'plugin'))


from flox import Flox, utils
from pathlib import Path
from shutil import copyfile
from functools import cached_property

HOME_PAGE = '/d2l/home/{}'
CONTENT_PAGE = '/d2l/le/content/{}/home'
DISCUSSIONS_PAGE = '/d2l/le/{}/discussions/List'
SUBMISSIONS_PAGE = '/d2l/lms/dropbox/user/folders_list.d2l?ou={}'
D2L_PAGES = {
    'Course Home': HOME_PAGE,
    'Content Tab': CONTENT_PAGE,
    'Discussions Tab': DISCUSSIONS_PAGE,
    'Submissions Tab': SUBMISSIONS_PAGE
}

ERROR_ICON = 'assets/error.png'
SETTINGS_ICON = 'assets/settings.png'
PAGE_ICONS = {
    'Course Home': 'assets/home.png',
    'Content Tab': 'assets/content.png',
    'Discussions Tab': 'assets/discussions.png',
    'Submissions Tab': 'assets/submissions.png'
}


class CourseLauncher(Flox):
    """A D2L course launcher plugin to open course pages from Flow Launcher."""

    def __init__(self):
        super().__init__()
        self.domain = ''
        self.courses = []
        self.modify_time = 0.0  # Last time the config file was modified.
        self.reload_data()  # Load the configuration from file.

    def query(self, query):
        """Handle plugin queries to get responses."""
        # Check that configuration file exists.
        if not os.path.exists(self.config_file): 
            self.show_error(msg='Please set up the configuration file!')
            self.show_config()
            return
        # If the config has been modified since last time, then reload the data.
        if self.modify_time != os.path.getmtime(self.config_file):
            self.reload_data()
        if not self.domain: # Make sure we have a domain.
            self.show_error(msg='Please add the domain in your configuration file!')
            self.show_config()
            return
        if not self.courses: # Make sure we have courses.
            self.show_error(msg='Please add courses to your configuration file!')
            self.show_config()
            return
        
        # Quick launch config command:
        if query.lower() == 'config':
            self.show_config()
            return
        

        # Loop through add ad all the courses:
        for course in self.courses:
            id = course.get('id', None)
            if not id:  # Ignore entry if there is no id.
                continue

            # Get the users page option, or default to the home page if not set:
            page_title = course.get('default_page', '').strip().title() or 'Course Home'

            # Figure out the correct uri for the selected default page:
            # First, check for the default page title in the custom pages.
            custom_pages = course.get('custom_pages', {})
            uri = custom_pages.get(page_title, {}).get('uri')
            if not uri:  
                # If the default page isn't found in the custom list, then check the known d2l pages.
                d2l_path = D2L_PAGES.get(page_title, HOME_PAGE)
                if d2l_path == HOME_PAGE:  # Not found: update the title when defaulted to the home page.
                    page_title = 'Course Home'
                uri = self.domain + d2l_path.format(id)  # Combine the d2l domain and the page path.

            # Add course entry to results:
            self.add_item(
                title=course.get('name', f'Course {id}') or f'Course {id}',
                subtitle=f'Open {page_title}',
                icon=utils.get_icon(course.get('icon', ''), Path(self.custom_icons_folder)),  # Get the icon path & download if needed.
                method=self.browser_open,
                parameters=[uri],
                context=[id, course.get('name', f'Course {id}'), custom_pages]
            )

    def context_menu(self, data):
        """Generate context menu options for a given course."""
        if not data:
            return

        id, course_name, custom_pages = data
        # Add a sub-item for each D2L page:
        for page_title, page_path in D2L_PAGES.items():
            self.add_item(
                title=page_title,
                subtitle=course_name,
                icon=PAGE_ICONS.get(page_title, ''),
                method=self.browser_open,
                parameters=[self.domain + page_path.format(id)]
            )

        # Add a sub-item for each custom page:
        for page_title, attributes in custom_pages.items():
            uri = attributes.get('uri')
            if not uri:  # Ignore entries with no uri to open.
                continue;

            self.add_item(
                title=page_title,
                subtitle=course_name,
                icon=utils.get_icon(attributes.get('icon', ''), Path(self.custom_icons_folder)),   # Get the icon path & download if needed.
                method=self.browser_open,
                parameters=[uri]
            )
    
    def show_error(self, msg: str='Something went wrong!'):
        """Helper to create an error message item."""
        self.add_item(
            title=msg,
            subtitle='Click here to view instructions on GitHub',
            icon=ERROR_ICON,
            method=self.browser_open,
            parameters=[self.manifest['Website']]
        )

    def show_config(self):
        """Add show config file prompt."""
        self.add_item(
            title='Create/Open Configuration File',
            icon=SETTINGS_ICON,
            method=self.open_config
        )

    def open_config(self):
        """Open the configuration file in default editor."""
        if not os.path.exists(self.config_file):  # Create file from the template if it doesn't exist. 
            copyfile('blank-config.json', self.config_file)
        self.browser_open(self.config_file)  # Open file.

    @cached_property
    def config_file(self):
        """Get the path for the config file."""
        dirname = self.name
        return os.path.join(self.appdata, 'Settings', 'Plugins', dirname, 'Configuration.json')

    def reload_data(self):
        """Load in data for D2L courses from the config file."""
        config = self.config_file
        if not os.path.exists(config):  # Check file exists.
            return
        self.modify_time = os.path.getmtime(config)  # Update the last modified time for tracking.

        # Load in configuration data.
        with open(config, 'r') as fp:
            data = json.load(fp)
            self.domain = data.get('domain', '').strip(' /')  # Strip spaces and backslashes so it's in the correct format.
            self.courses = data.get('courses', [])

    @cached_property
    def custom_icons_folder(self):
        """Get folder path for automatically downloaded custom icons."""
        dirname = self.name
        return os.path.join(self.appdata, 'Settings', 'Plugins', dirname, 'Custom-Icons')


if __name__ == "__main__":
    CourseLauncher()
