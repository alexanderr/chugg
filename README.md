**What is chugg?**

A script to fetch HTML and image assets for Chegg ETextbooks for easier readability and portability.

**How do I use chugg?**

First you must obtain the ISBN, Chegg's Book UUID and some specific cookies from your browser.
Thankfully, all three can be obtained with any browser using the Network tab of your browser's web developer console
(Can be easily accessed with right-click->Inspect and going to the network tab.)


Look for a network GET request for `toc.json` as shown below:

![Example](https://i.imgur.com/vpVjEY8.png)

Click on it and on the right side, you should be able to view the following tabs:

![Example](https://i.imgur.com/wN9yoEq.png)

In the cookies tab, look for the following cookies and copy their values into `cookies.json`:
* CloudFront-Key-Pair-Id
* CloudFront-Policy
* CloudFront-Signature

In the response tab, you will be able to see the ISBN and Book ID. The ISBN will be an integer without hyphens. 
The Book ID will be in UUID format similar to this: `18240dc7-9ed8-415d-b338-e7936515e452`

Here are the parameters to the script (you will need Python 3.6+ installed):

`chugg.py <isbn> <book_id>`

A random User Agent will be used unless specified with the `-u` flag. Specify an output directory with the `-d` flag, otherwise the export folder will be used.
