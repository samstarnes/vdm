# VDM - Video Download Manager

## VDM is a frontend downloader for youtube-dlp. Coded using python & flask with mongodb as the database. Json files saving as a support backup.

#### This is still in early development and not all features have been implemented. Expect slow updates as I work, have a life, need entertainment time, etc... 

#### Main is typically up to date and the latest as found on my instance of [VDM](https://vdm.0x0.la) (unless some *big* changes are coming).
> Ideally, don't use mine as I don't have *that* much HD space and I'll end up deleting your [unwanted] data.

## Requirements

- docker
- - cookies.txt file (optional, may become a requirement in the future)

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

> [!WARNING]
> The security and safety of your server cannot be guaranteed. I am unable to secure all aspects independently.<br>
> Running this application locally is generally safe (no open ports, no reverse proxy, and not exposed to the internet), provided you trust users on your local area network (LAN).<br><br>
> As of October 31, 2024, a significant security breach was attempted; however, due to the nature of the attack, the intruder was unable to escape the container.<br><br>
> The attacker exploited a vulnerability in an outdated ffmpeg binary, enabling remote code execution (RCE) through base64-encoded commands embedded in an .mkv video file. Importantly, no modifications were made to my production server—only four additional files (including one .mkv video) were added.<br><br>
> The ffmpeg and ffprobe binaries have been updated to 6.1. Overall, the system remains secure. (24.11.02)

![Full Page](https://0x0.la/x/vdm.png)
![Embeds for videos](https://0x0.la/i/2023/12/17-12.36-btrz.png)


## Features not included yet
- Admin page (*coming soon!*)
- Calender filter for searching between dates
- Configurable:
  - Cookie file (*coming soon!*)
  - Items ordered by duration, size, download date (ID), posted date  
  - Option of JSON saving (metadata is managed by mongoDB and I'm making that a requirement, for now) (*coming soon!*)
  - Public item automatic deletion (finished but disabled, needs light work)
  - Normal vs reverse order
  - Other database options (like postgreSQL and RethinkDB, perhaps others)
  - Public vs private view (and mixed of both) for videos (*coming soon-ish!*)
  - Themes (*coming soon!*)
- Download comments | requested by /u/ECrispy
- Download playlists | requested by /u/barry_flash-
- Filter function
- Have the output & cutout work for only a single URL 
  - [*I might just remove this altogether and provide an alternative method*]
- Move installation location (files, directories, requires updates to mongodb) (*coming soon!*) 
  - [***this comes next as additional volumes available for storage is necessary now***]
- Multi-user login & registration & login/registration page (*coming soon-ish!*)
- Repair mongoDB with JSON files as backup (*coming soon-ish!*)
  - (*just had to do this, don't updateMany with no sleep*)
- Search is IN but I've got some ideas to tweak it and make it better (*tags*)
- Video player page (it looks terrible right now and honestly requires chunked videos with HLS to function properly) (*coming soon!*)
  - [***FINISHED*** however this is doubling the amount of data being saved hence the requirement for additional volumes and automatic deletion of original video copies. A command to convert and download will be made available.]
  - [*This is also why I have not updated in quite some time.*]
- Volume management system to add additional hard drives for extra storage
  - [*This will include round-robin and high-watermarking as methods of saving.*]

### Known Issues
- High Priority
  - Some videos will fail to download if presented with multiple videos on a page. Twitter for example will provide a grid of multiple videos and/or pictures included and the link will fail to complete.
    - [*This works now, I think? But you will have to manually select each video of the grid to download them all or else the first one is downloaded.*]
- Low Priority:
  - Currently using the cutout time or renaming of a file is not recommended as I've done zero testing using it nor will it work with multiple URLs. I **do not** recommend using it at all.
  - Leaving a newline `\n` in the text box with an array of URLs will cause a failure on the empty newline.
- Cosmetic Issues:
  - Data stream from yt-dlp when returning the ETA rapidly changes in time, looking into a way of making a more accurate ETA return.
  - Progress begins with the download but then merges the audio and video so it resets the progress bar to 0%, goes back to 100%.
  - Sometimes the progress bugs out a little and stops updating (looking into this).
  - SSE seems to unexpectedly close after some time (need to determine if it can be reopened).

### Possible Issues
- N/A

### Personal Note
I've already used this for over 3500+ videos and it's worked so far. There may be changes in the future with the data structure so it may not work from one version to another (*highly unlikely*). I will attempt to include all changes and commands available to update the data if breaking changes are necessary.
