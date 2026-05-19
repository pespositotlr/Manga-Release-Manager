# Manga Release Manager

I made this to work in tandem with my other tools https://github.com/pespositotlr/Mangataro-Scheduled-Uploader and https://github.com/pespositotlr/Mangadex-Scheduled-Uploader along with https://github.com/wotakumoe/kaguya and some CLI tools.
This orchestrates other tools to upload the same version of a manga release to each of them, store the reader links, and update a Wordpress site with the new links.
It should work with uploading new chapters/volumes as well as checking each source if another version already exists in which case it clears the original pages and updates with new ones.
This is meant to save time doing the repetetive task of uploading to each one via a web UI and copying links over.


You need to create a series_config.json to store credentials to login to wordpress and locations of the other tools.
This is built for uploading to Catbox.moe, Mega.nz, Mangadex, Mangataro, and Cubari (Using ImageChest as a host, uploading via wotakumoe's Kaguya tool).
I modified my local version of the Kaguya tool to skip all prompts and use default values. Normally it prompts you for y/n inputs.
