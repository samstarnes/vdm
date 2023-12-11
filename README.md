# VDM - Video Download Manager

### VDM is a frontend for youtube-dl. It's coded using python with mongoDB as the backend database.

#### This is still in early development and not all features have been implemented. Expect slow updates as I work, have a life, need entertainment time, etc... 

## Requirements

- cookies.txt file
- docker
- some light editing

## Installation

`do note this is not the final installation method and it will be made easier in the future`

#### 1) First modify the `cookies.txt` file in netscape format with *your* cookies. There are tools, addons and extensions to grab these (only required for sites that require a login, otherwise empty file is fine) 

#### 2) Modify `line 74` in `app.py` to your base directory. 
- For example, I export these files to `/srv/docker/anomaly-ytdlp` so I should expect to find `app.py` like so:
- - `/srv/docker/anomaly-ytdlp/app.py` 
- - \(This will be changed later\)
 
### 3) Modify .env with a new MeiliSearch key

#### 4) `docker-compose up --build` or for a detached container `docker-compose up -d --build`

## Appearance (WIP - will change over time)

![FireShot Webpage Capture 020 - 'VDM_Video Download Manager' - 10 0 0 4](https://github.com/samstarnes/vdm/assets/19420604/b54b9fe4-b0cf-460f-82a6-7a15c12d1842)


## Features not included yet
- admin page
- calender filter for searching between dates
- configurable public item automatic deletion (finished but disabled), cookie file, themes
- configurable option of JSON saving - (metadata is managed by mongoDB and I'm making that a requirement)
- customizable items ordered by duration, size, download date (ID), posted date
- filter function
- multi-user login & registration & login/registration page
- normal vs reverse order
- public vs private view (or both) of videos
- search function
- video player page
- have the output & cutout work for only a single URL

### Known Issues
- Leaving a newline `\n` in the text box with an array of URLs will cause a failure on the empty newline.
- Sometimes the progress bugs out a little and stops updating (looking into this).
- Progress begins with the download but then merges the audio and video so it resets the progress bar to 0%, goes back to 100%.
- SSE seems to unexpectedly close after some time (need to determine if it can be reopened).
- Data stream from yt-dlp when returning the ETA rapidly changes in time, looking into a way of making a more accurate ETA return.
- Currently using the cutout time or renaming of a file is not recommended as I've done no testing nor will it work with multiple URLs. I do not recommend using that.
- Some videos will fail to download if presented with multiple videos on a page. Twitter for example will provide a grid of multiple videos and/or pictures included and the link will fail to complete.

### Possible Issues
- I have absolutely no idea what happens if you attempt to download a URL with multiple videos on the same page. Haven't tested.

#### Personal Note
I've already used this for over 700 videos and it's worked so far. There may be changes in the future with the data structure so it may not work from one version to another. I will attempt to include all changes and commands available to update the data and bump versions.
