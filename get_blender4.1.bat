@echo off
setlocal enabledelayedexpansion
setlocal

:: Define the Blender version and URLs
set BLENDER_VERSION=4.1.1
set BLENDER_ZIP=blender-%BLENDER_VERSION%-windows-x64.zip
set BLENDER_URL=https://download.blender.org/release/Blender4.1/%BLENDER_ZIP%

:: Check if Blender42 directory exists
if exist .blender41 (
    echo Directory ".blender41" already exists.
    set /p DELDIR=Do you want to delete it and proceed? WARNING: You may need to reconfigure your Python environment. [y/n]
    
    if /i "!DELDIR!"=="y" (
        rmdir /s /q .blender41
        echo Directory ".blender41" deleted.
    ) else (
        echo Operation cancelled.
        exit /b
    )
)

:: Download Blender
echo Downloading Blender %BLENDER_VERSION%...
curl -O %BLENDER_URL%

:: Unzip to a folder named ".blender41"
echo Unzipping the downloaded Blender zip file into directory ".blender41"...
mkdir .blender41
tar -xf %BLENDER_ZIP% -C .blender41 --strip-components=1

:: Delete the zip file
del %BLENDER_ZIP%
echo Deleted the downloaded Blender zip file.

:: Create a "portable" directory within .blender41
mkdir .blender41\4.1\config
echo Created a "config" directory under ".blender41" for saving all Blender settings locally.

echo Operation completed.

endlocal
