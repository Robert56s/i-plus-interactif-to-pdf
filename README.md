# i-plus-interactif-to-pdf

## Project Overview

This project is dedicated to resolving the problems of affordability and accessibility associated with online school books by eliminating restrictive DRM (Digital Rights Management) constraints.

## The Challenge

I+ Interactive, an ebook solution, is cumbersome and DRM-restricted. Users are compelled to maintain an active internet connection merely to access their purchased books, which is far from ideal. This project addresses this issue by providing a tool to convert your personal I+ Interactif books into PDF format.

## Disclaimer

We want to make it abundantly clear that the "i-plus-interactif-to-pdf" tool is intended for legitimate and legal purposes only. We are not responsible for any misuse of this software for illegal activities, including but not limited to piracy of I+ Interactive books.

Users are strongly advised to comply with all applicable laws and regulations regarding the use of copyrighted materials and to respect the terms and conditions set by the content providers. Any use of this software that violates copyright or other legal rights is entirely the responsibility of the user.

We do not endorse or condone any illegal activities, and any such use of this tool is expressly discouraged.

## Requirements

- Google Chrome or Firefox
- Python 3 with pip installed

## Usage

Install the required Python dependencies:

```
pip install -r requirements.txt
```

Create a `.env` file and add your i+ interactif login credentials (email and password), along with the browser you want to use (chrome or firefox). Check the `.env.example` if you are lost.

If your computer is slow or the script fails due to timing issues, try increasing the delay values in `time.sleep()` to give the browser more time to load pages.
