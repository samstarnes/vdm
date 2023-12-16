# VDM - Video Download Manager

## VDM is a frontend downloader for youtube-dlp. Coded using python & flask with mongodb as the database. Json files saving as a support backup.

#### This is still in early development and not all features have been implemented. Expect slow updates as I work, have a life, need entertainment time, etc... 

#### Main is currently up to date and the latest as found on my instance of [VDM](https://vdm.0x0.la).
> Ideally, don't use mine as I don't have *that* much HD space and I'll end up deleting your [unwanted] data.

## Requirements

- docker
- - cookies.txt file (optional)

## Installation

#### 1) CD to your target install directory and clone: `git clone https://github.com/samstarnes/vdm.git` 
> Or install to current directory after CDing to target install directory `git clone https://github.com/samstarnes/vdm.git .`

#### 2) (optional) Modify the `cookies.txt` file in netscape format with *your* cookies. 
> Recommended method: `yt-dlp --cookies-from-browser chrome --cookies cookies.txt`

> Alternative method: There are tools, addons and [extensions](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) to grab these.
> > This is only required for sites that require a login otherwise do not change the file.
> > > Sites such as Twitter (when it once required a login to download content) or videos locked behind age verifications or subscriptions will require this (but yt-dlp might fail, ymmv). 
> > > > Note that the cookies file must be in Mozilla/Netscape format and the first line of the cookies file must be either:

> > > > `# HTTP Cookie File` or `# Netscape HTTP Cookie File`. 

> > > > Make sure you have correct newline format in the cookies file and convert newlines if necessary to correspond with your OS, namely `CRLF` (`\r\n`) for Windows and `LF` (`\n`) for Unix and Unix-like systems (Linux, macOS, etc.). `HTTP Error 400: Bad Request` when using `--cookies` is a good sign of invalid newline format.

#### 3) Edit your .env file for your keys
> If you'd like you can change your container names and external ports.
> > To generate keys (random 64 character):

> > > For Linux you can run: 
```
openssl rand -hex 32
```

> > > For Windows in PowerShell, see below:
```
$randomKeyBytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($randomKeyBytes)
$randomKeyHex = -join ($randomKeyBytes | ForEach-Object { $_.ToString("X2") })
Write-Host $randomKeyHex
```

#### 4) Build and run docker container: `docker-compose up --build` 
- Or for a detached container `docker-compose up -d --build`

## Appearance (WIP - will change over time)

![FireShot Webpage Capture 020 - 'VDM_Video Download Manager' - 10 0 0 4](https://github.com/samstarnes/vdm/assets/19420604/b54b9fe4-b0cf-460f-82a6-7a15c12d1842)


## Features not included yet
- Admin page
- Calender filter for searching between dates
- Configurable:
  - Cookie file
  - Items ordered by duration, size, download date (ID), posted date  
  - Option of JSON saving (metadata is managed by mongoDB and I'm making that a requirement, for now)
  - Public item automatic deletion (finished but disabledm, needs light work)
  - Normal vs reverse order
  - Other database options (like postgreSQL and RethinkDB, perhaps others)
  - Public vs private view (and mixed of both) for videos
  - Themes
- Download comments | requested by /u/ECrispy
- Download playlists | requested by /u/barry_flash-
- Filter function
- Have the output & cutout work for only a single URL
- Multi-user login & registration & login/registration page
- Repair mongoDB with JSON files as backup (just had to do this, don't updateMany with no sleep)
- Search is IN but I've got some ideas to tweak it and make it better
- Video player page (it looks terrible right now and honestly requires chunked videos with HLS to function properly)

### Known Issues
- High Priority
  - Currently using the cutout time or renaming of a file is not recommended as I've done zero testing using it nor will it work with multiple URLs. I **do not** recommend using it at all.  
  - Some videos will fail to download if presented with multiple videos on a page. Twitter for example will provide a grid of multiple videos and/or pictures included and the link will fail to complete.
- Low Priority:
  - Leaving a newline `\n` in the text box with an array of URLs will cause a failure on the empty newline.
- Cosmetic Issues:
  - Data stream from yt-dlp when returning the ETA rapidly changes in time, looking into a way of making a more accurate ETA return.
  - Progress begins with the download but then merges the audio and video so it resets the progress bar to 0%, goes back to 100%.
  - Sometimes the progress bugs out a little and stops updating (looking into this).
  - SSE seems to unexpectedly close after some time (need to determine if it can be reopened).

### Possible Issues
- N/A

#### Personal Note
I've already used this for over 1000+ videos and it's worked so far. There may be changes in the future with the data structure so it may not work from one version to another. I will attempt to include all changes and commands available to update the data if breaking changes are necessary.
