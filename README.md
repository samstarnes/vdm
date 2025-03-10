# VDM - Video Download Manager

### VDM is a frontend for youtube-dl. It's coded using python with mongoDB as the backend database.

# You are looking at the beta version. This will either be broken in some way or have undeveloped or untested features. This is not the recommended version to use. Main is currently more up to date 23.12.15

#### This is still in early development and not all features have been implemented. Expect slow updates as I work, have a life, need entertainment time, etc... 

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

## Appearance (WIP - will change over time)

![Full Page](https://camo.githubusercontent.com/f792ec1a1426c7ae6b9ec1c916b638435a982b08dba96973d768af7906b600e6/68747470733a2f2f3078302e6c612f782f76646d2e706e67)
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

I've already used this for over 2000+ videos and it's worked so far. There may be changes in the future with the data structure so it may not work from one version to another (*highly unlikely*). I will attempt to include all changes and commands available to update the data if breaking changes are necessary.
