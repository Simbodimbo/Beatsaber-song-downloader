import requests, os
from zipfile import ZipFile
from pathlib import Path

# Static config:
# Destination directory
downloadDir = r'C:\Users\simon\Downloads\BSLegacyLauncher (1)\BSLegacyLauncher\Installed Versions\Beat Saber 1.29.1\Beat Saber_Data\CustomLevels TEST'

# Headers needed to fake being a real browser session ty bypass Cloudflare check
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'}

# List of preexisting song ids in downloadDir
existingIds = []
for root, dirs, files in os.walk(downloadDir):
    for name in dirs:
        # Assume the first part of the filename is the song id. Extract that (via split), and add to list of existing Ids
        existingIds.append(name.split()[0].strip())
print(f"Identified {len(existingIds)} existing song folders in '{downloadDir}'")


# Function to download / unzip stuff from a beatsaver API URL
# Assumes URL has a {} parameter for page
def download(url, max, dir):
    counter = 0
    page = 0

    # Outer loop control variable
    more = True

    while more:
        print(f'Processing download page #{page}...')
        
        # Set stop flag, to be overridden if and only if we get result indicating there might be more hits
        more = False

        # Call the URL and store the response
        response = requests.get(url.format(page), headers)

        # Parse the response into a dictionary
        data = response.json()

        # Root object is a dictionary containing just 1 element: docs
        docs = data.get('docs')

        # Value of 'docs' is a list of documents (songs)
        # If there was a hit on this page, lets try the next page as well
        if len(docs) > 0:
            print(f'Page #{page} has {len(docs)} entries, processing...')
            more = True
            page = page + 1

        # Grab each hit on the page
        for doc in docs:
            if (max > 0 and counter >= max):
                print(f"Reached download limit of {max}, stopping.")
                return

            counter = counter + 1
        
            # Each doc contains a 'version' attribute, which contains a list of version objects
            versions = doc.get('versions')
            id = doc.get('id')
            name = doc.get('name')

            # Loop over each version of this doc (song) and fetch the download URL
            for version in versions:
                downloadURL = version.get('downloadURL')
                
                if id in existingIds:
                    print(f"[{counter}] Song already exists, skipping download for song id {id}: '{name}'")
                    continue

                # Download file
                response = requests.get(downloadURL, allow_redirects=True, verify=True, timeout=30, headers=headers)
                
                # Success is http 200, quit if we don't get that (given a single retry)
                if response.status_code != 200:
                    print(f"[{counter}] Download failed with http status code {response.status_code}, retrying once...")
                    response = requests.get(downloadURL, allow_redirects=True, headers=headers)

                if response.status_code != 200:
                    print(f"[{counter}] Nope, still didn't work, giving up. Retry from page {page}.")
                    quit()


                # Response will contain a content-disposition header indicating suggested filename like this:
                # attachment; filename="1c680 (Chou, Chou, Kou, Soku, De, Mae, Sai, Soku!!! Speed, Star, Kanade - spectre158).zip"

                # Grab just the (unquoted) filename itself
                filename = response.headers['content-disposition'].split('; ')[1].replace('filename=', '').replace('\"', '')
                
                # Join filename to download dir
                fullFilename = os.path.join(dir, filename)

                # Fix .zip filename, in case they misnamed the file in API
                if not fullFilename.endswith(".zip"):
                    print(f"Someone screwed up, adding .zip to {fullFilename}")
                    fullFilename = fullFilename + ".zip"

                # Write downloaded file to disk
                open(fullFilename, 'wb').write(response.content)

                # Unzip file as zipfile-named subfolder
                with ZipFile(fullFilename, 'r') as zObject:
                    dirname = Path(filename).stem
                    fullDirname = os.path.join(dir, dirname)
                    zObject.extractall(fullDirname)

                # And delete the zipfile itself
                os.remove(fullFilename)
                print(f"[{counter}] Downloaded song id {id}: '{name}'")


# REST API URls to grab songs from
# print("** Downloading ranked songs **")
# download('https://api.beatsaver.com/search/text/{}?ranked=true&sortOrder=Latest', 0, downloadDir)

print("")
print("** Downloading top-500 unranked & verified songs **")
download('https://api.beatsaver.com/search/text/{}?ranked=false&verified=true&sortOrder=Rating', 500, downloadDir)

