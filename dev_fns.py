import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from typing import Optional
import zipfile

import toml


DEFAULT_DEV_CONFIG_TOML = {
    'addon': {
        'src_code_rel_path': '',
        'installation_rel_path': '',
        'distribution_rel_path': '',
        'blender_version': '',
        'blender_rel_path': '',
        'startup_script_rel_path': '',
    }
}
DEV_CONFIG_TOML_PATH = Path(__file__).parent / 'dev_config.toml'


# region Shared Functions

def _create_dev_fns_toml():
    """Create the dev_fns.toml file with default values."""
    if not DEV_CONFIG_TOML_PATH.exists():
        DEV_CONFIG_TOML_PATH.write_text(toml.dumps(DEFAULT_DEV_CONFIG_TOML))
        print('[INFO] dev_fns.toml file created with default values.')


def dev_init():
    """Initialize the dev_fns.toml file with default values."""
    if not DEV_CONFIG_TOML_PATH.exists():
        _create_dev_fns_toml()
    else:
        print('[INFO] dev_fns.toml file already exists. If you want to reset the values, delete the file and run this '
              'command again.')


def _get_dev_fns_toml() -> dict:
    """
    Get the contents of the dev_fns.toml file. If the file does not exist, create it with default values.

    Returns:
        The contents of the dev_fns.toml file as a dictionary
    """
    # If the dev_fns.toml file does not exist, create it with default values
    if not DEV_CONFIG_TOML_PATH.exists():
        _create_dev_fns_toml()
        assert False, (f'dev_config.toml initiated. Please set the proper values in {DEV_CONFIG_TOML_PATH} before '
                       f'proceeding.')
    with open(DEV_CONFIG_TOML_PATH, 'r') as file:
        return toml.load(file)


def _get_path(path_key, is_rel_path: bool = False, must_exist: bool = False) -> Optional[Path]:
    """
    Get the path for the source code or installed code directory from the dev_fns.toml file.

    Args:
        path_key: The key to get the path from the dev_fns.toml file.
        is_rel_path: If True, the path is relative to the dev_fns.py file. If False, the path is absolute.
        must_exist: If True, the path must exist. If False, the path can be empty or not exist.

    Returns:
        The Path object for the source code or installed code directory if the path is valid, otherwise None.
    """
    dev_config_toml = _get_dev_fns_toml()
    target_path = dev_config_toml.get('addon', {}).get(path_key, None)
    if target_path not in [None, '', '.']:
        try:
            if is_rel_path:
                target_path = Path(__file__).parent / target_path
            else:
                target_path = Path(target_path)
        except Exception as e:
            print(f'[ERROR] Invalid path for {path_key} in dev_fns.toml, {e}. Please check the path and try again.')
            return None
        if (not must_exist) or (must_exist and target_path.exists()):
            return target_path
    return None


def _get_package_toml() -> dict:
    """
    Reads the pyproject.toml file and returns the content as a dictionary.

    :return: dict
    """
    # Get the path to the package.toml file which is in the same directory as this script
    pyproject_toml = Path(__file__).parent / 'pyproject.toml'
    if not pyproject_toml.exists():
        raise FileNotFoundError(f"The file {pyproject_toml} does not exist.")
    with open(pyproject_toml, 'r') as file:
        package_info = toml.load(file)
    return package_info


def _is_poetry_installed() -> bool:
    """
    Checks if Poetry is installed on the system.

    Returns:
        bool: True if Poetry is installed, False otherwise.
    """
    try:
        subprocess.run(['poetry', '--version'], capture_output=True, text=True, check=True)
        return True
    except Exception as e:
        print(f'[ERROR] Poetry is not installed: {e}')
        ...
    return False

# endregion Shared Functions


# region Sync Code Function

def sync_code():
    """
    This function is used to sync the code installed as Blender's addon to the current source code. The source code
    path and installed code path are read from dev_fns.toml file. The older installed files will always be overwritten
    by the source code files. New source code files will be copied. Deleted source code files will be deleted from the
    installed code directory.
    """

    def get_file_list_to_sync():
        """
        Get the list of files to sync between the source code and installed code directories. Sort the files into three
        categories: 'add', 'copy', and 'delete'.

        :return: A dictionary containing the files to add, copy, and delete.
        """
        excluded_dirs = {'__pycache__', 'libs'}  # Exclude local libraries packed with the addon
        excluded_files = {'deps_installed'}  # Exclude the file that marks the dependencies as installed
        files_to_sync_dict = {'add': [], 'copy': [], 'delete': []}
        source_code_files = [file for file in list(source_code_path.rglob('*')) if file.is_file()]
        installed_code_files = [file for file in list(installed_code_path.rglob('*')) if file.is_file() and
                                set(file.parts) & excluded_dirs == set()]
        # Check for files to add or copy
        for source_code_file in source_code_files:
            installed_code_file = installed_code_path / source_code_file.relative_to(source_code_path)
            if installed_code_file.exists():
                print(source_code_file)
                # Check if the source code file is a text file, if so compare the contents, otherwise copy the file. For
                # binary files, compare the last modified time. If the source code file is newer, copy it.
                if source_code_file.suffix in ['.py', '.txt', '.json', '.toml', '.md', '.html', '.css', '.js', 'qss']:
                    if source_code_file.read_text() != installed_code_file.read_text():
                        files_to_sync_dict['copy'].append((source_code_file, installed_code_file))
                else:
                    if installed_code_file.name != 'deps_installed':
                        if source_code_file.stat().st_mtime > installed_code_file.stat().st_mtime:
                            files_to_sync_dict['copy'].append((source_code_file, installed_code_file))
            else:
                files_to_sync_dict['add'].append((source_code_file, installed_code_file))
        # Check for files to delete
        for installed_code_file in installed_code_files:
            if installed_code_file.name not in excluded_files:
                source_code_file = source_code_path / installed_code_file.relative_to(installed_code_path)
                if not source_code_file.exists():
                    files_to_sync_dict['delete'].append(installed_code_file)
        # Print the files to sync by category
        if len(files_to_sync_dict['add']) + len(files_to_sync_dict['copy']) + len(files_to_sync_dict['delete']) == 0:
            print('No files to sync.')
        else:
            if len(files_to_sync_dict['add']) > 0:
                print(f'{len(files_to_sync_dict["add"])} File(s) to Add:')
                for source_code_file, installed_code_file in files_to_sync_dict['add']:
                    print(f'    {source_code_file} -> {installed_code_file}')
            if len(files_to_sync_dict['copy']) > 0:
                print(f'{len(files_to_sync_dict["copy"])} File(s) to Copy:')
                for source_code_file, installed_code_file in files_to_sync_dict['copy']:
                    print(f'    {source_code_file} -> {installed_code_file}')
            if len(files_to_sync_dict['delete']) > 0:
                print(f'{len(files_to_sync_dict["delete"])} File(s) to Delete:')
                for installed_code_file in files_to_sync_dict['delete']:
                    print(f'    {installed_code_file}')
        return files_to_sync_dict

    def sync_files():
        """
        Sync the files between the source code and installed code directories.
        """
        # Add new files
        for source_code_file, installed_code_file in files_to_sync['add']:
            if not installed_code_file.parent.exists():
                installed_code_file.parent.mkdir(parents=True)
            shutil.copyfile(source_code_file, installed_code_file)
        # Copy existing files
        for source_code_file, installed_code_file in files_to_sync['copy']:
            shutil.copyfile(source_code_file, installed_code_file)
        # Delete files
        for installed_code_file in files_to_sync['delete']:
            installed_code_file.unlink()
        # Report the number of files synced
        print(f'{len(files_to_sync["add"])} File(s) Added. {len(files_to_sync["copy"])} File(s) Copied. '
              f'{len(files_to_sync["delete"])} File(s) Deleted.')

    source_code_path = _get_path('src_code_rel_path', is_rel_path=True, must_exist=True)
    if source_code_path is None:
        print('[ERROR] Source code path is not set in dev_fns.toml. Please set the source code path and try again.')
        exit(1)
    installed_code_path = _get_path('installation_rel_path', is_rel_path=True, must_exist=False)
    if installed_code_path is None:
        print('[ERROR] Installation path is not set in dev_fns.toml. Please set the installation path and try again.')
        exit(1)
    print(f'Source Code Path: {source_code_path}')
    print(f'Installed Code Path: {installed_code_path}')
    files_to_sync = get_file_list_to_sync()
    if len(files_to_sync['add']) + len(files_to_sync['copy']) + len(files_to_sync['delete']) > 0:
        sync_files()

# endregion Sync Code Function


# region Build Extension Functions

def _configure_paths(package_toml: dict) -> dict:
    """
    Configures the paths for the addon source code, dependencies, and the destination zip file.

    Args:
        package_toml (dict): The package information from the pyproject.toml file.

    Returns:
        dict: A dictionary containing the paths for the addon source code, dependencies, and the destination zip file.
    """
    # Ensure the required keys are present in the package.toml and dev_config.toml files
    try:
        addon_name = package_toml['tool']['poetry']['name']
        addon_version = package_toml['tool']['poetry']['version']
        addon_source_code_dir = _get_path('src_code_rel_path', is_rel_path=True, must_exist=True)
        temp_build_dir = Path(tempfile.mkdtemp()) / (addon_name + '-' + addon_version) / addon_source_code_dir.name
        temp_build_libs_dir = temp_build_dir / 'libs'  # Deps are placed in a 'libs' subdirectory
        temp_build_dir_to_zip = temp_build_dir.parent  # The source code has to be in a subdirectory of the zip file
        dist_dir = _get_path('distribution_rel_path', is_rel_path=True, must_exist=False)
        dist_file_path = dist_dir / f'{addon_name}-{addon_version}.zip'
    except KeyError as e:
        raise KeyError(f'[ERROR] Key {e} not found in pyproject.toml or dev_config.toml file.')
    except Exception as e:
        raise Exception(f'[ERROR] Failed to configure paths for the addon: {e}')
    output = {
        'addon_name': addon_name,
        'addon_version': addon_version,
        'addon_source_code_dir': addon_source_code_dir,
        'temp_build_dir': temp_build_dir,
        'temp_build_libs_dir': temp_build_libs_dir,
        'temp_build_dir_to_zip': temp_build_dir_to_zip,
        'requirements_file': addon_source_code_dir / 'requirements.txt',
        'requirements_pypi_file': addon_source_code_dir / 'requirements_pypi.txt',
        'requirements_git_file': addon_source_code_dir / 'requirements_git.txt',
        'dist_dir': dist_dir,
        'dist_file_path': dist_file_path
    }
    assert all([path is not None for path in output.values()]), 'Failed to configure paths for the addon.'
    return output


def _copy_addon_source_code(paths: dict):
    """
    Copies the source code of the Blender addon to the build directory.

    Args:
        paths: dict: A dictionary containing the paths for the addon source code, dependencies, and the destination zip
                     file.
    """
    print('Copying source code...')
    # Check if the source code directory exists
    if not paths['addon_source_code_dir'].exists():
        raise FileNotFoundError(f"The source code directory {paths['addon_source_code_dir']} does not exist.")
    # Copy the content of the source code directory to the build directory
    temp_build_dir = paths['temp_build_dir']
    for item in paths['addon_source_code_dir'].iterdir():
        if item.is_file():
            shutil.copy(item, temp_build_dir)
        elif item.is_dir():
            shutil.copytree(item, temp_build_dir / item.name)


def _generate_addon_dependencies(paths: dict):
    """
    Collects the dependencies of the addon and copies them to the temporary build directory. The dependencies are
    separated into two files: requirements_pypi.txt and requirements_git.txt. The dependencies in requirements_pypi.txt
    are installed using pip in the target Blender Python environment by the code in configure.py. The dependencies in
    requirements_git.txt are installed in the temporary build directory for packaging.

    Args:
        paths: dict: A dictionary containing the paths for the addon source code, dependencies, and the destination zip
                     file.
    """

    def gen_requirements_files():
        # Use Poetry to generate the requirements.txt file for the addon
        requirements_file = paths['requirements_file']
        subprocess.run(['poetry', 'export', '-f', 'requirements.txt', '-o', str(requirements_file), '--without-hashes'],
                       cwd=Path(__file__).parent, check=True)
        if not requirements_file.exists():
            raise FileNotFoundError(f"Failed to generate the requirements.txt file for the addon.")
        # Separate the requirements into two files: requirements_pypi.txt and requirements_git.txt
        with open(requirements_file, 'r') as file:
            requirements = file.readlines()
        requirements_pypi = []
        requirements_git = []
        for requirement in requirements:
            if 'git+' in requirement:
                requirements_git.append(requirement)
            else:
                requirements_pypi.append(requirement)
        requirements_pypi_file = paths['requirements_pypi_file']
        requirements_git_file = paths['requirements_git_file']
        if len(requirements_pypi) > 0:
            with open(requirements_pypi_file, 'w') as file:
                file.writelines(requirements_pypi)
        if len(requirements_git) > 0:
            with open(requirements_git_file, 'w') as file:
                file.writelines(requirements_git)
        # Remove the requirements.txt file
        requirements_file.unlink()

    # Use Poetry to generate the requirements.txt file for the addon
    print('Generating addon dependencies...')
    # Generate the requirements files
    gen_requirements_files()
    # Use Poetry to run this command "poetry run python -m pip install -r .\requirements_git.txt -t <target_path>
    # --no-deps" to install the git dependencies in the temporary build directory for packaging.
    print('Installing git dependencies...')
    requirements_git_file = paths['requirements_git_file']
    if requirements_git_file.exists():
        libs_dir = paths['temp_build_libs_dir']
        subprocess.run(['poetry', 'run', 'python', '-m', 'pip', 'install', '-r', str(requirements_git_file), '-t',
                        libs_dir, '--no-deps'], cwd=Path(__file__).parent, check=True)


def _zip_addon(paths: dict):
    """
    Zips the temporary build directory into a zip file and copy it to the dist directory.

    Args:
        paths: dict: A dictionary containing the paths for the addon source code, dependencies, and the destination zip
                     file.
    """
    exclude_files = ['__pycache__', '.git', '.gitignore', '.vscode', '.idea']
    print('Zipping addon...')
    dist_dir = paths['dist_dir']
    dist_file_path = paths['dist_file_path']
    # Check if the dist directory exists, if not, create it
    if not dist_dir.exists():
        dist_dir.mkdir()
    # Check if the target zip file already exists, if so, delete it
    if dist_file_path.exists():
        dist_file_path.unlink()
    # Zip the temporary build directory
    temp_build_dir_to_zip = paths['temp_build_dir_to_zip']
    with zipfile.ZipFile(dist_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_build_dir_to_zip):
            root_path = Path(root)
            for file in files:
                file_path = root_path / file
                if not any(exclude_file in str(root_path) for exclude_file in exclude_files):
                    zipf.write(file_path, file_path.relative_to(temp_build_dir_to_zip))

    # Clean up the temporary build directory
    shutil.rmtree(paths['temp_build_dir'])
    print(f'Addon zip file created: {dist_file_path}')


def build_addon():
    """
    This is a function intended to be called by Poetry as a custom command to build the Blender addon as a zip file for
    distribution. It does the following:
    1. Collect the source code of the Blender addon from the "src" directory.
    2. Collect the dependencies of the addon using Poetry and pip. The dependencies are separated into two files:
       requirements_pypi.txt and requirements_git.txt. The dependencies in requirements_pypi.txt are installed using pip
       in the target Blender Python environment by the code in configure.py. The dependencies in requirements_git.txt
       are installed in the temporary build directory for packaging.
    3. Zip the source code and dependencies into a zip file and copy it to the "dist" directory.
    The generated zip file can be installed in Blender as an addon. The code in the __init__.py file can call functions
    in configure.py to install or link the required libraries in the temporary build directory to the Blender Python.
    The git dependencies are mainly the internal packages and need to be distributed with the addon. The PyPI
    dependencies are will be installed by pip which will resolve the dependencies with the Blender's Python environment
    automatically.
    """
    print('Building Blender addon...')
    # Check if Poetry is installed
    if not _is_poetry_installed():
        raise EnvironmentError('Poetry is not installed. Please install Poetry to build the addon.')
    # Get the package information from the pyproject.toml file
    try:
        package_toml = _get_package_toml()
        addon_name = package_toml['tool']['poetry']['name']
        addon_version = package_toml['tool']['poetry']['version']
    except KeyError as e:
        raise KeyError(f'[ERROR] Key {e} not found in pyproject.toml file.')
    # Create a temporary build directory
    print(f'Building addon: {addon_name} {addon_version}...')
    paths = _configure_paths(package_toml)
    temp_build_dir = paths['temp_build_dir']
    temp_build_dir.mkdir(parents=True, exist_ok=True)
    # Collect the dependencies of the addon and copy them to the temporary build directory
    _generate_addon_dependencies(paths)
    # Copy the source code of the addon to the temporary build directory
    _copy_addon_source_code(paths)
    # Zip the temporary build directory into a zip file and copy it to the dist directory
    _zip_addon(paths)

# endregion Build Extension Functions


# region Add Auto Launch Script

def add_auto_launch_script():
    """
    Add a script to the Blender startup directory to launch the Honeycomb prototype automatically after Blender starts.
    The correct operator must be invoked through bpy.ops.wm to run the Honeycomb prototype. It must be invoked through
    Blender's timer system (0.1s after it starts after Blender starts) to ensure that the Blender context is ready.
    """

    dev_config = _get_dev_fns_toml()
    script = f'import bpy\n\n' \
             f'def execute_after_startup():\n' \
             f'    print(\'Running {dev_config.get("addon", {}).get("addon_print_name", "Unknown")}\')\n' \
             f'    {dev_config.get("addon", {}).get("addon_operator_id", "unknown")}()\n\n' \
             f'bpy.app.timers.register(execute_after_startup, first_interval=0.1)\n'

    startup_script_path = _get_path('startup_script_rel_path', is_rel_path=True, must_exist=False)
    if not startup_script_path.exists():
        startup_script_path.mkdir(parents=True)
    auto_launch_script_path = startup_script_path / (f'launch_'
                                                     f'{dev_config.get("addon", {}).get("addon_name", "unknown")}.py')
    with open(auto_launch_script_path, 'w') as file:
        file.write(script)

# endregion


# region Run Blender

def run_blender(install_blender: bool = False):
    """
    Run Blender that is installed within this package's directory using the path specified in the dev_fns.toml file. If
    Blender is not installed, download it from the Blender website and set it up (unzip the file, remove the zip file,
    and add a portable directory).

    Args:
        install_blender (bool): If True, download Blender from the Blender website and set it up. If False, run the
                                Blender executable in the package's directory
    """

    def download_blender():
        """Run curl to install Blender 4.2, unzip the file, and remove the zip file. Add portable dir."""
        # Detect current OS and download the corresponding Blender version
        os = platform.system()
        if os == 'Darwin':
            subprocess.run(['curl', '-O', f'https://download.blender.org/release/{blender_minor_version}'
                                          f'/blender-f{blender_version}-mac-x64.dmg'])
            blender_zip_path = Path(__file__).parent / f'blender-f{blender_version}-mac-x64.dmg'
        elif os == 'Linux':
            subprocess.run(['curl', '-O', f'https://download.blender.org/release/{blender_minor_version}'
                                          f'/blender-f{blender_version}-linux-x64.tar.xz'])
            blender_zip_path = Path(__file__).parent / f'blender-f{blender_version}-linux-x64.tar.xz'
        elif os == 'Windows':
            subprocess.run(['curl', '-O', f'https://download.blender.org/release/{blender_minor_version}'
                                          f'/blender-f{blender_version}-windfows-x64.zip'])
            blender_zip_path = Path(__file__).parent / f'blender-f{blender_version}-windows-x64.zip'
        else:
            raise Exception(f'Unsupported OS: {os}')
        # Unzip the file into Blender42 dir
        with zipfile.ZipFile(blender_zip_path, 'r') as zip_ref:
            zip_ref.extractall(Path(__file__).parent / blender_dir_name)
        # Remove the zip file
        blender_zip_path.unlink()
        # Add portable dir
        portal_dir = Path(__file__).parent / blender_dir_name / 'portable'
        portal_dir.mkdir()

    dev_config = _get_dev_fns_toml()

    try:
        blender_version = dev_config.get('addon', {}).get('blender_version')
        blender_minor_version = blender_version.split('.')[0] + '.' + blender_version.split('.')[1]
        blender_dir_name = dev_config.get('addon', {}).get('blender_rel_path')
    except KeyError as e:
        raise KeyError(f'[ERROR] Key {e} not found in dev_fns.toml file.')

    # Download Blender if it doesn't exist
    blender_dir_path = Path(__file__).parent / blender_dir_name
    if install_blender and not blender_dir_path.exists():
        download_blender()
    # Find Blender executable and run it
    os = platform.system()
    if os == 'Darwin':
        blender_exe_path = blender_dir_path / 'blender.app' / 'Contents' / 'MacOS' / 'blender'
    elif os == 'Linux':
        blender_exe_path = blender_dir_path / 'blender'
    elif os == 'Windows':
        blender_exe_path = blender_dir_path / 'blender.exe'
    else:
        raise Exception(f'Unsupported OS: {os}')

    subprocess.run([str(blender_exe_path)])

# endregion
