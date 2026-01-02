
# MyQSL

Ham radio logging and QSL card software. Pronounced "My Queasel". 

This software handles logging to QRZ.com as well as generated and sends QSL cards via email. This is definitely a personal project, and really just made for me. I haven't hard coded any values specific to me, however, so if you would like to use this software, it should be as easy as generating your own config file, and swapping out my images for yours. 

One challenge, should you decide to adpat this code for your own use, however, would be mail. I handle my domains' email service through Office 365, so I used their API for mail sending. I haven't integrated SMTP at all. I'm sure it wouldn't be that difficult to do, but I don't need to, so I haven't. 



## Requirements
I've only tested this on Linux. No idea if it runs on Windows or MacOS

**System Packages:**
 - Python 3.12 or higher
 - ImageMagick
   
**Python Libraries:**
 - Flask - [https://pypi.org/project/Flask/](https://pypi.org/project/Flask/)
 - Wand - [https://pypi.org/project/Wand/](https://pypi.org/project/Wand/)
 - O365 - [https://pypi.org/project/o365/](https://pypi.org/project/o365/)
 - xmltodict - [https://pypi.org/project/xmltodict/](https://pypi.org/project/xmltodict/)
 - requests - [https://pypi.org/project/requests/](https://pypi.org/project/requests/)

    
