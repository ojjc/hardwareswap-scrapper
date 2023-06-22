import praw
import pandas as pd
from collections import defaultdict
from datetime import datetime
import yagmail
import re
import html
import schedule
import time

sent_emails = defaultdict(int)

# extract price from description based on matching criteria
def extract_price(desc):
    patterns = [r'\$([\d,.]+)',
                r'Asking \$([\d,.]+)',
                r'Asking for\s*([\d,.]+)',
                r'([\d,.]+)\s*USD',
                r'([\d,.]+)\$'
    ]
    for pattern in patterns:
        match = re.search(pattern, desc, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


# extract key information between [H] and [W]
def extract_title(tit):
    pattern = r'\[H\](.*?)\[W\]'
    match = re.search(pattern, tit, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


# extract the timestamp url for quick access
def extract_url(description):
    pattern = r'(https?://\S+)'
    match = re.findall(pattern, description)
    if match:
        urls = [html.unescape(url) for url in match]
        return urls
    return None


# dictionary simplification
def simplify(variations_dict):
    simplified_dict = {}
    for variations, simplified in variations_dict.items():
        if isinstance(variations, str):
            variations = (variations,)
        for variation in variations:
            simplified_dict[variation] = simplified
    return simplified_dict


# load previously sent email info from CSV file into sent_emails.csv
def load_sent_emails():
    try:
        df = pd.read_csv('sent_emails.csv', index_col=0)
        sent_emails.update(df['Count'].to_dict())
    except FileNotFoundError:
        pass


# called after sending emails in order to save updated count
def save_sent_emails():
    df = pd.DataFrame(sent_emails.items(), columns=['Title', 'Count'])
    df.to_csv('sent_emails.csv', index=False)


# processing
def process_posts():
    reddit_read_only = praw.Reddit(client_id="----",
                               client_secret="----",
                               user_agent="----")

    subreddit = reddit_read_only.subreddit("hardwareswap")
    new_posts = subreddit.new(limit=40)
    posts_dict = defaultdict(list)
  
    for post in new_posts:
      title = post.title
  
      description = post.selftext
  
      flair = post.link_flair_text
      
      if flair and flair.lower() != "selling":
          continue
  
      price = extract_price(description)
      tit = extract_title(title)
      url = extract_url(description)
  
      posts_dict["Title"].append(tit)
      posts_dict["Cost"].append(price)
      posts_dict["URL"].append(post.url)
      posts_dict["Timestamps"].append(url)
      
  
    new_posts = pd.DataFrame(posts_dict)
    new_posts.to_csv("hsw.csv", index=False)
    df = pd.read_csv("hsw.csv", index_col=0)
    print(df)
  

    # CAN BE ANY ITEM OR THING YOU WANT, USER INPUTTED THOUGH SINCE THERE'S SO MUCH VARIATION BASED ON
    # THE POSTS SEEN ON R/HARDWARESWAP
    search_phrase = simplify({
      ("b550i", "B550i", "b550 itx", "B550 itx", "B550 ITX", "B550I", "b550I"): "b550i",
      ("5800x3d", "5800x 3d", "5800X 3d", "5800X 3D", "5800X3D", "5800X(3d)", "5800X(3D)"): "5800x3d",
      ("x570i", "X570i", "x570I", "X570I", "X570 ITX", "x570 ITX", "x570 itx", "X570 itx"): "x570i"
    })
  
    user = '----'
    app_password = '----'
    to = '----'
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
  
    for i in range(len(posts_dict["Title"])):
        title = posts_dict["Title"][i]

        if title is None:
            continue

        if sent_emails[title] >= 3:
            continue

        for phrase, output in search_phrase.items():
            if phrase in title:
                email_count = sent_emails[title] + 1

                # warning email
                if sent_emails[title] == 2:
                    subject = f"'{phrase}' - last email ^-^"
                    content = [f"'{phrase}' found in '{title}': {output}", posts_dict["URL"][i],
                                "this is the last email before stopping :3", 'sent at ' + current_time]
                    with yagmail.SMTP(user, app_password) as yag:
                        yag.send(to, subject, content)
                        print('sent last email before updates stop')

                # normal email
                if sent_emails[title] < 3:
                    subject = f"'{phrase}' is HERE!!!"
                    content = [f"'{phrase}' found in '{title}': {output}", posts_dict["URL"][i],
                                f"this is email number #{email_count} sent for this post", 'sent at ' + current_time]
                    with yagmail.SMTP(user, app_password) as yag:
                        yag.send(to, subject, content)
                        print(f'sent email {email_count} for post "{title}"')

                    sent_emails[title] += 1

                break

    save_sent_emails()

load_sent_emails()

def job():
    process_posts()

schedule.every(1).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)