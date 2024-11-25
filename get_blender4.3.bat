@echo off
setlocal enabledelayedexpansion
setlocal

:: Define the Blender version and URLs
set BLENDER_VERSION=4.3.0
set BLENDER_ZIP=blender-%BLENDER_VERSION%-windows-x64.zip
set BLENDER_URL=https://download.blender.org/release/Blender4.3/%BLENDER_ZIP%

:: Check if Blender42 directory exists
if exist .blender43 (
    echo Directory ".blender43" already exists.
    set /p DELDIR=Do you want to delete it and proceed? WARNING: You may need to reconfigure your Python environment. [y/n]
    
    if /i "!DELDIR!"=="y" (
        rmdir /s /q .blender43
        echo Directory ".blender43" deleted.
    ) else (
        echo Operation cancelled.
        exit /b
    )
)

:: Download Blender
echo Downloading Blender %BLENDER_VERSION%...
curl -O %BLENDER_URL%

:: Unzip to a folder named ".blender43"
echo Unzipping the downloaded Blender zip file into directory ".blender43"...
mkdir .blender43
tar -xf %BLENDER_ZIP% -C .blender43 --strip-components=1

:: Delete the zip file
del %BLENDER_ZIP%
echo Deleted the downloaded Blender zip file.

:: Create a "portable" directory within .blender43
mkdir .blender43\portable
echo Created a "portable" directory under ".blender43" for saving all Blender settings locally.

echo Operation completed.

endlocal
