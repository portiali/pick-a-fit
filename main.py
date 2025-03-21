# client-side pyhton app for outfit app, which is calling
# a set of lambda functions in AWS through API Gateway
# the overall purpose of the app is to recommend users an outfit
# based no images of clothes in their outfit and weather
#
# Authors: 
# Portia Li & Mariana Ma
#
# Northwestern University
# CS 310
#

import requests
import jsons

import random
import uuid
import pathlib
import logging
import sys
import os
import base64
import time

from configparser import ConfigParser


# functions: 
# outfit()
#   returns outfit in a folder? -- resized and everything


# upload()
#   allows user to continously upload outfits to S3
#   should call sagemaker-- server side probs
#   also return a description of what sagemaker analyzed
#   loop continously until user says no more clothes left to upload

# weather()
#   abstraction from user-- but should get the weather data from weather API
#   makes clothing decisions accordingly


# main:
#   initial welcome prompt, ask for username, assign user id accordingly

############################################################
#
# classes
#
class Data:

  def __init__(self, row):
    self.dataid = row[0]
    self.clothingid = row[1]
    self.gender = row[2]
    self.category = row[3]
    self.articleType = row[4]
    self.color = row[5]
    self.season = row[6]
    self.usage = row[7]

class User:
   def __init__(self, row):
      self.userid = row[0]
      self.username = row[1]

###################################################################
#
# web_service_get
#
# When calling servers on a network, calls can randomly fail. 
# The better approach is to repeat at least N times (typically 
# N=3), and then give up after N tries.
#
def web_service_get(url):
  """
  Submits a GET request to a web service at most 3 times, since 
  web services can fail to respond e.g. to heavy user or internet 
  traffic. If the web service responds with status code 200, 400 
  or 500, we consider this a valid response and return the response.
  Otherwise we try again, at most 3 times. After 3 attempts the 
  function returns with the last response.
  
  Parameters
  ----------
  url: url for calling the web service
  
  Returns
  -------
  response received from web service
  """

  try:
    retries = 0
    
    while True:
      response = requests.get(url)
        
      if response.status_code in [200, 400, 480, 481, 482, 500]:
        #
        # we consider this a successful call and response
        #
        break
      #
      # failed, try again?
      #
      retries = retries + 1
      if retries < 3:
        # try at most 3 times
        time.sleep(retries)
        continue
          
      #
      # if get here, we tried 3 times, we give up:
      #
      break

    return response

  except Exception as e:
    print("**ERROR**")
    logging.error("web_service_get() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return None
############################################################
#
# get_or_create_user
#

def get_or_create_user(baseurl):
    try: 
        
        # /usernames is called in main and passed in here as a list
        username = input("Enter your username: ")
        api = "/users"
        url = baseurl + api

        # prepare the data to send as JSON in POST body
        data = {
           "username": username
        }


        #POST req to add new user if they don't exist 
        # and to retrieve data of user if they do
        res = requests.post(url, json=data)
        
        if res.status_code == 200:
           body = res.json()
           message = body['message']
           print(message)
           return body['userid']
        elif res.status_code == 500:
           body = res.json()
           message = body['message']
           print(message)
           return
        else:
           body = res.json()
           print(body)
           return
           
    except Exception as e:
        print("**ERROR")
        print("**ERROR: invalid input")
        print("**ERROR")
        return -1
    
############################################################
#
# prompt
# 

def prompt():
  try:
    print()
    print(">> Enter a command:")
    print("   0 => end")
    print("   1 => upload closet")
    print("   2 => get a fit!")

    cmd = input()

    if cmd == "":
      cmd = -1
    elif not cmd.isnumeric():
      cmd = -1
    else:
      cmd = int(cmd)

    return cmd

  except Exception as e:
    print("**ERROR")
    print("**ERROR: invalid input")
    print("**ERROR")
    return -1


############################################################
#
# upload
#
def upload(baseurl, userid):
  """
  Prompts the user for a local filename and user id, 
  and uploads that asset (jpeg of a clothing item) to S3 for 
  analysis and recognition. Returns the attributes of the
  clothing item upon competion of the job.

  Parameters
  ----------
  baseurl: baseurl for web service

  Returns
  -------
  nothing
  """

  try:
    print("Enter jpeg filename>")
    local_filename = input()

    if not pathlib.Path(local_filename).is_file():
      print("JPEG file '", local_filename, "' does not exist...")
      return

    print("Enter user id>")
    userid = input()

    #
    # build the data packet:
    #
    infile = open(local_filename, "rb")
    bytes = infile.read()
    infile.close()

    #
    # now encode the image as base64. Note b64encode returns
    # a bytes object, not a string. So then we have to convert
    # (decode) the bytes -> string, and then we can serialize
    # the string as JSON for upload to server:
    #
    data = base64.b64encode(bytes)
    datastr = data.decode()

    print(">> What kind of clothing item is this?")
    print("   Type 1 for top")
    print("   Type 2 for bottoms")
    print("   Type 3 for dress")
    print("   Type 4 for shoes")
    print("   Type 5 for accessory")

    input = input().strip()

    category = None
    articleType = None

    if input == "1":
        category = "Top"
        print("What kind of top?")
        print("   Type 1 for T-shirt")
        print("   Type 2 for sweater")
        print("   Type 3 for jacket")

        top_types = {
            "1": "T-shirt",
            "2": "Sweater",
            "3": "Jacket",
        }

        articleType = top_types.get(input().strip(), "Unknown top, please enter one of the given options")

    elif input == "2":
        category = "Bottoms"
        print("What kind of bottoms?")
        print("   Type 1 for long pants")
        print("   Type 2 for shorts")
        print("   Type 3 for skirt")

        bottom_types = {
            "1": "Long pants",
            "2": "Shorts",
            "3": "Skirt"
        }

        articleType = bottom_types.get(input().strip(), "Unknown bottom, please enter one of the given options")

    elif input == "3":
        category = "Shoes"
        print("What kind of shoes?")
        print("   Type 1 for Boots")
        print("   Type 2 for Sneakers")
        print("   Type 3 for Sandals")

        shoe_types = {
            "1": "Boots",
            "2": "Sneakers",
            "3": "Sandals",
        }

        articleType = shoe_types.get(input().strip(), "Unknown shoes, please enter one of the given options")

    else:
        articleType = "Unknown"

    print("You selected:", articleType)

    color = None
    print("What color is the item?")
    print("   Type 1 for Black")
    print("   Type 2 for White")
    print("   Type 3 for Gray")
    print("   Type 4 for Brown")
    print("   Type 5 for Red")
    print("   Type 6 for Orange")
    print("   Type 7 for Yellow")
    print("   Type 8 for Green")
    print("   Type 9 for Blue")
    print("   Type 10 for Purple")
    print("   Type 11 for Pink")

    color_options = {
            "1": "Black",
            "2": "White",
            "3": "Gray",
            "4": "Brown",
            "5": "Red",
            "6": "Orange",
            "7": "Yellow",
            "8": "Green",
            "9": "Blue",
            "10": "Purple",
            "11": "Pink",
        }
     
    color = color_options.get(input(), "Unknown color, please enter one of the given options")
    print("You selected:", color)

    season = None
    print("What season is the item for?")
    print("   Type 1 for Spring")
    print("   Type 2 for Summer")
    print("   Type 3 for Fall")
    print("   Type 4 for Winter")

    season_options = {
        "1": "Spring",
        "2": "Summer",
        "3": "Fall",
        "4": "Winter"
    }

    season = season_options.get(input().strip(), "Unknown season, please enter one of the given options")

    print("You selected:", season)

    print(f"\nSummary of your selections:")
    print(f"Item: {articleType}")
    print(f"Color: {color}")
    print(f"Season: {season}")

    data = {
    "assetname": local_filename,
    "data": datastr,
    "info": {
        "category": category,
        "articleType": articleType,
        "color": color,
        "season": season,
    }
}
    #
    # call the web service:
    #
    api = '/item'
    url = baseurl + api + "/" + userid

    res = web_service_post(url, data)
    #
    # let's look at what we got back:
    #
    if res.status_code == 200: #success
      pass
    elif res.status_code == 400: # no such user
      body = res.json()
      print(body)
      return
    else:
      # failed:
      print("Failed with status code:", res.status_code)
      print("url: " + url)
      if res.status_code == 500:
        # we'll have an error message
        body = res.json()
        print("Error message:", body)
      #
      return

    #
    # success, extract clothingid:
    #
    body = res.json()

    clothingid = body

    print("jpeg uploaded under the clothing id", clothingid)

    return

  except Exception as e:
    logging.error("**ERROR: upload() failed:")
    logging.error("url: " + url)
    logging.error(e)
    return
  



    
############################################################

# main 
#

try:
    print('** Welcome to Pick-a-Fit! **\n')
    print("Let's get you started.\n")
    print()

    # eliminate traceback so we just get error message:
    sys.tracebacklimit = 0

    #
    # what config file should we use for this session?
    #
    config_file = 'outfitapp-client-config.ini'

    #
    # setup base URL to web service:
    #
    configur = ConfigParser()
    configur.read(config_file)
    baseurl = configur.get('client', 'webservice')

    #
    # make sure baseurl does not end with /, if so remove:
    #
    if len(baseurl) < 16:
        print("**ERROR: baseurl '", baseurl, "' is not nearly long enough...")
        sys.exit(0)

    if baseurl.startswith("http:"):
        print("**ERROR: your URL starts with 'http', it should start with 'https'")
        sys.exit(0)

    lastchar = baseurl[len(baseurl) - 1]
    if lastchar == "/":
        baseurl = baseurl[:-1]

    #get user's username or create a new user based on username
    userid = get_or_create_user(baseurl)    


    # couldn't access username/couldn't insert user
    if not userid:
       print('Error with user, please try again')
       sys.exit(1)


    cmd = prompt()

    while cmd != 0:
      if cmd == 1:
        upload(baseurl, userid)
      elif cmd == 2:
         # download function place holder
         pass
      else:
         print("** Unknown command, try again....")
      
      cmd = prompt()
    #
    # done
    #
    print()
    print('** done **')
    sys.exit(0)

except Exception as e:
    logging.error("**ERROR: main() failed:")
    logging.error(e)
    sys.exit(0)
